"""
Views for candidate management and CV processing.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging

from apps.audit.models import AuditLog
from services.api_actor import get_api_actor
from services.parser_service import CVParserService
from services.embedding_service import EmbeddingService
from .models import Candidate
from .serializers import (
    CandidateUploadSerializer, CandidateSerializer, 
    CandidateDetailSerializer, CandidateUpdateSerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
def upload_cv(request):
    """
    Upload and process a candidate's CV.
    """
    serializer = CandidateUploadSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            # Save the candidate with uploaded file
            actor = get_api_actor(request)
            candidate = serializer.save(uploaded_by=actor)
            
            # Log the upload action
            AuditLog.log_cv_upload(
                user=actor,
                candidate=candidate,
                metadata={
                    'file_name': candidate.cv_file.name,
                    'file_size': candidate.cv_file.size
                },
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Process the CV file
            try:
                parser_service = CVParserService()
                parsing_result = parser_service.parse_cv(candidate.cv_file.path)
                
                if parsing_result['parsing_success']:
                    # Update candidate with parsed information
                    candidate.extracted_text = parsing_result['extracted_text']
                    candidate.skills = parsing_result['skills']
                    candidate.experience_years = parsing_result['experience_years']
                    candidate.education = parsing_result['education']
                    
                    # Update email and phone if not provided
                    if not candidate.email and parsing_result['email']:
                        candidate.email = parsing_result['email']
                    if not candidate.phone and parsing_result['phone']:
                        candidate.phone = parsing_result['phone']
                    
                    candidate.save()
                    
                    # Generate embedding
                    try:
                        embedding_service = EmbeddingService()
                        embedding, used_openai = embedding_service.generate_cv_embedding(
                            candidate.extracted_text
                        )
                        candidate.embedding_vector = embedding
                        candidate.save()
                        
                        logger.info(f"Generated embedding for candidate {candidate.name} using {'OpenAI' if used_openai else 'dummy'}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for candidate {candidate.name}: {str(e)}")
                    
                    return Response({
                        'message': 'CV uploaded and processed successfully',
                        'candidate': CandidateSerializer(candidate).data,
                        'parsing_details': {
                            'extracted_skills_count': len(parsing_result['skills']),
                            'experience_years_found': parsing_result['experience_years'] is not None,
                            'education_found': bool(parsing_result['education']),
                            'embedding_generated': bool(candidate.embedding_vector)
                        }
                    }, status=status.HTTP_201_CREATED)
                
                else:
                    # Parsing failed but candidate was created
                    return Response({
                        'message': 'CV uploaded but processing failed',
                        'candidate': CandidateSerializer(candidate).data,
                        'error': parsing_result['error_message']
                    }, status=status.HTTP_206_PARTIAL_CONTENT)
                    
            except Exception as e:
                logger.error(f"Error processing CV for candidate {candidate.name}: {str(e)}")
                return Response({
                    'message': 'CV uploaded but processing failed',
                    'candidate': CandidateSerializer(candidate).data,
                    'error': str(e)
                }, status=status.HTTP_206_PARTIAL_CONTENT)
                
        except Exception as e:
            logger.error(f"Error uploading CV: {str(e)}")
            return Response({
                'error': 'CV upload failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'error': 'Invalid upload data',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


class CandidateListView(generics.ListAPIView):
    """
    List all active candidates.
    """
    serializer_class = CandidateSerializer
    
    def get_queryset(self):
        queryset = Candidate.objects.filter(is_active=True)
        
        # Filter by search query if provided
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                name__icontains=search
            ) | queryset.filter(
                email__icontains=search
            ) | queryset.filter(
                skills__icontains=search
            )
        
        # Filter by experience years
        min_experience = self.request.query_params.get('min_experience')
        if min_experience:
            try:
                min_exp = int(min_experience)
                queryset = queryset.filter(experience_years__gte=min_exp)
            except ValueError:
                pass
        
        # Filter by skills
        required_skills = self.request.query_params.get('skills')
        if required_skills:
            skill_list = [skill.strip() for skill in required_skills.split(',')]
            for skill in skill_list:
                queryset = queryset.filter(skills__icontains=skill)
        
        return queryset.order_by('-created_at')


class CandidateDetailView(generics.RetrieveAPIView):
    """
    Get detailed candidate information.
    """
    serializer_class = CandidateDetailSerializer
    queryset = Candidate.objects.all()


class CandidateUpdateView(generics.UpdateAPIView):
    """
    Update candidate information.
    """
    serializer_class = CandidateUpdateSerializer
    queryset = Candidate.objects.all()
    
    def perform_update(self, serializer):
        candidate = serializer.save()
        
        # Log the update action
        AuditLog.log_action(
            user=get_api_actor(self.request),
            action_type='update',
            description=f"Updated candidate {candidate.name}",
            content_object=candidate,
            risk_level='low',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class CandidateDeleteView(generics.DestroyAPIView):
    """
    Delete (deactivate) a candidate.
    """
    queryset = Candidate.objects.all()
    
    def perform_destroy(self, instance):
        # Soft delete - just mark as inactive
        instance.is_active = False
        instance.save()
        
        # Log the deletion action
        AuditLog.log_action(
            user=get_api_actor(self.request),
            action_type='delete',
            description=f"Deactivated candidate {instance.name}",
            content_object=instance,
            risk_level='medium',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )