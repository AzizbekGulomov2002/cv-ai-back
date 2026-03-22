"""
Embedding service for generating and managing text embeddings using OpenAI API.
Includes fallback to dummy embeddings when API key is not available.
"""
import hashlib
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from django.conf import settings

try:
    import openai
    from openai import OpenAI
except ImportError:
    openai = None
    OpenAI = None

from apps.ai.models import EmbeddingCache

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service class for generating and managing text embeddings.
    """
    
    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_DIMENSIONS = 1536
    
    def __init__(self):
        """Initialize the embedding service."""
        self.client = None
        self.api_key = settings.OPENAI_API_KEY
        self.use_openai = self._initialize_openai()
        
        if not self.use_openai:
            logger.warning(
                "OpenAI API not available. Using dummy embeddings. "
                "Set OPENAI_API_KEY in .env file to use real embeddings."
            )
    
    def _initialize_openai(self) -> bool:
        """
        Initialize OpenAI client if API key is available.
        
        Returns:
            bool: True if OpenAI is available and configured
        """
        if not self.api_key:
            return False
        
        if OpenAI is None:
            logger.error("OpenAI package not installed. Install with: pip install openai")
            return False
        
        try:
            self.client = OpenAI(api_key=self.api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return False
    
    def _generate_content_hash(self, text: str) -> str:
        """
        Generate SHA-256 hash for content caching.
        
        Args:
            text: Text content to hash
            
        Returns:
            str: SHA-256 hash of the content
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _get_cached_embedding(self, content_hash: str, content_type: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding if available.
        
        Args:
            content_hash: Hash of the content
            content_type: Type of content ('cv_text' or 'job_description')
            
        Returns:
            List[float] or None: Cached embedding vector if found
        """
        try:
            cache_entry = EmbeddingCache.objects.get(
                content_hash=content_hash,
                content_type=content_type
            )
            cache_entry.increment_usage()
            logger.info(f"Using cached embedding for {content_type}: {content_hash[:8]}...")
            return cache_entry.embedding_vector
        except EmbeddingCache.DoesNotExist:
            return None
    
    def _cache_embedding(self, content_hash: str, content_type: str, 
                        embedding: List[float], model_used: str):
        """
        Cache embedding for future use.
        
        Args:
            content_hash: Hash of the content
            content_type: Type of content
            embedding: Embedding vector to cache
            model_used: OpenAI model used for embedding
        """
        try:
            EmbeddingCache.objects.create(
                content_hash=content_hash,
                content_type=content_type,
                embedding_vector=embedding,
                model_used=model_used
            )
            logger.info(f"Cached embedding for {content_type}: {content_hash[:8]}...")
        except Exception as e:
            logger.error(f"Failed to cache embedding: {str(e)}")
    
    def _generate_dummy_embedding(self, text: str, dimensions: int = DEFAULT_DIMENSIONS) -> List[float]:
        """
        Generate dummy embedding based on text hash for fallback.
        
        Args:
            text: Input text
            dimensions: Embedding dimensions
            
        Returns:
            List[float]: Dummy embedding vector
        """
        # Use text hash to generate reproducible dummy embedding
        hash_int = int(self._generate_content_hash(text)[:16], 16)
        np.random.seed(hash_int % (2**32))
        
        # Generate random vector and normalize
        embedding = np.random.randn(dimensions).astype(float)
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.tolist()
    
    def generate_embedding(self, text: str, content_type: str = "text", 
                          model: str = DEFAULT_MODEL) -> Tuple[List[float], bool]:
        """
        Generate embedding for given text.
        
        Args:
            text: Text to embed
            content_type: Type of content for caching
            model: OpenAI model to use
            
        Returns:
            tuple: (embedding_vector, used_openai)
        """
        if not text.strip():
            raise ValueError("Input text cannot be empty")
        
        # Clean and prepare text
        text = text.strip()
        content_hash = self._generate_content_hash(text)
        
        # Try to get cached embedding first
        cached_embedding = self._get_cached_embedding(content_hash, content_type)
        if cached_embedding is not None:
            return cached_embedding, self.use_openai
        
        if self.use_openai:
            try:
                # Generate embedding using OpenAI
                response = self.client.embeddings.create(
                    input=text,
                    model=model
                )
                
                embedding = response.data[0].embedding
                
                # Cache the embedding
                self._cache_embedding(content_hash, content_type, embedding, model)
                
                logger.info(f"Generated OpenAI embedding for {content_type}")
                return embedding, True
                
            except Exception as e:
                logger.error(f"OpenAI embedding generation failed: {str(e)}")
                logger.warning("Falling back to dummy embedding")
                # Fall through to dummy embedding
        
        # Generate dummy embedding as fallback
        embedding = self._generate_dummy_embedding(text)
        
        # Cache dummy embedding too
        self._cache_embedding(content_hash, content_type, embedding, "dummy")
        
        logger.info(f"Generated dummy embedding for {content_type}")
        return embedding, False
    
    def generate_cv_embedding(self, cv_text: str) -> Tuple[List[float], bool]:
        """
        Generate embedding specifically for CV text.
        
        Args:
            cv_text: CV text content
            
        Returns:
            tuple: (embedding_vector, used_openai)
        """
        return self.generate_embedding(cv_text, content_type="cv_text")
    
    def generate_job_embedding(self, job_description: str) -> Tuple[List[float], bool]:
        """
        Generate embedding specifically for job description.
        
        Args:
            job_description: Job description text
            
        Returns:
            tuple: (embedding_vector, used_openai)
        """
        return self.generate_embedding(job_description, content_type="job_description")
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score between -1 and 1
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimensions")
        
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    
    def calculate_similarity_score(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate similarity score normalized to 0-100 range.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Similarity score between 0 and 100
        """
        similarity = self.calculate_similarity(embedding1, embedding2)
        # Convert from [-1, 1] to [0, 100]
        return ((similarity + 1) / 2) * 100
    
    def batch_generate_embeddings(self, texts: List[str], content_type: str = "text") -> List[Tuple[List[float], bool]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            content_type: Type of content for caching
            
        Returns:
            List[tuple]: List of (embedding_vector, used_openai) tuples
        """
        results = []
        
        for text in texts:
            try:
                embedding, used_openai = self.generate_embedding(text, content_type)
                results.append((embedding, used_openai))
            except Exception as e:
                logger.error(f"Failed to generate embedding for text: {str(e)}")
                # Add dummy embedding for failed case
                dummy_embedding = self._generate_dummy_embedding(text)
                results.append((dummy_embedding, False))
        
        return results
    
    def get_embedding_stats(self) -> Dict:
        """
        Get statistics about embedding usage.
        
        Returns:
            dict: Embedding usage statistics
        """
        try:
            from django.db.models import Count, Sum
            
            stats = EmbeddingCache.objects.aggregate(
                total_embeddings=Count('id'),
                total_usage=Sum('usage_count')
            )
            
            by_type = EmbeddingCache.objects.values('content_type').annotate(
                count=Count('id'),
                usage=Sum('usage_count')
            )
            
            by_model = EmbeddingCache.objects.values('model_used').annotate(
                count=Count('id'),
                usage=Sum('usage_count')
            )
            
            return {
                'total_embeddings': stats['total_embeddings'] or 0,
                'total_usage': stats['total_usage'] or 0,
                'by_content_type': list(by_type),
                'by_model': list(by_model),
                'openai_available': self.use_openai
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {str(e)}")
            return {
                'total_embeddings': 0,
                'total_usage': 0,
                'by_content_type': [],
                'by_model': [],
                'openai_available': self.use_openai
            }
    
    def clear_cache(self, content_type: Optional[str] = None) -> int:
        """
        Clear embedding cache.
        
        Args:
            content_type: Optional content type to clear specific cache
            
        Returns:
            int: Number of cache entries deleted
        """
        try:
            queryset = EmbeddingCache.objects.all()
            
            if content_type:
                queryset = queryset.filter(content_type=content_type)
            
            count = queryset.count()
            queryset.delete()
            
            logger.info(f"Cleared {count} embedding cache entries")
            return count
            
        except Exception as e:
            logger.error(f"Failed to clear embedding cache: {str(e)}")
            return 0