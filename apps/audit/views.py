"""
Views for audit log access and compliance reporting.
"""
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import AuditLog, ComplianceReport
from .serializers import AuditLogSerializer, ComplianceReportSerializer


class AuditLogListView(generics.ListAPIView):
    """
    List audit logs with filtering capabilities.
    """
    serializer_class = AuditLogSerializer
    
    def get_queryset(self):
        queryset = AuditLog.objects.all()
        
        # Filter by action type
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Filter by risk level
        risk_level = self.request.query_params.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by date range
        days = self.request.query_params.get('days', 30)
        try:
            days = int(days)
            start_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=start_date)
        except ValueError:
            pass
        
        # Search in descriptions
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(action_description__icontains=search) |
                Q(ai_explanation__icontains=search)
            )
        
        return queryset.order_by('-timestamp')


@api_view(['GET'])
def audit_statistics(request):
    """
    Get audit log statistics.
    """
    try:
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Basic counts
        from django.db.models import Count
        
        stats = AuditLog.objects.filter(timestamp__gte=start_date).aggregate(
            total_logs=Count('id'),
            high_risk_actions=Count('id', filter=Q(risk_level='high')),
            failed_actions=Count('id', filter=Q(success=False))
        )
        
        # Action type distribution
        action_types = AuditLog.objects.filter(
            timestamp__gte=start_date
        ).values('action_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Risk level distribution
        risk_levels = AuditLog.objects.filter(
            timestamp__gte=start_date
        ).values('risk_level').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'period_days': days,
            'total_logs': stats['total_logs'] or 0,
            'high_risk_actions': stats['high_risk_actions'] or 0,
            'failed_actions': stats['failed_actions'] or 0,
            'success_rate': (
                ((stats['total_logs'] or 0) - (stats['failed_actions'] or 0)) / 
                (stats['total_logs'] or 1) * 100
            ),
            'action_types': list(action_types),
            'risk_levels': list(risk_levels),
            'generated_at': timezone.now().isoformat()
        })
        
    except ValueError:
        return Response({'error': 'Invalid days parameter'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)