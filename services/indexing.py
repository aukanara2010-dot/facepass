"""
Photo indexing service for FacePass microservice.

This service handles indexing of photos by extracting face embeddings
and storing them in the vector database.
"""

import logging
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import numpy as np

from models.face import FaceEmbedding
from services.face_recognition import get_face_recognition_service
from core.s3 import download_image

logger = logging.getLogger(__name__)


class IndexingService:
    """Service for indexing photos and managing face embeddings."""
    
    def __init__(self):
        """Initialize indexing service."""
        self.face_service = get_face_recognition_service()
    
    def index_photo(
        self,
        photo_id: str,
        session_id: str,
        image_data: bytes,
        db: Session
    ) -> Tuple[bool, Optional[float], int, Optional[str]]:
        """
        Index a single photo by extracting face embedding.
        
        Args:
            photo_id: Unique photo identifier
            session_id: Photo session UUID
            image_data: Raw image bytes
            db: Database session
            
        Returns:
            Tuple of (success, confidence, faces_detected, error_message)
        """
        try:
            # Extract face embedding
            embedding, confidence = self.face_service.extract_single_embedding(image_data)
            
            if embedding is None:
                logger.warning(f"No face detected in photo {photo_id}")
                return False, None, 0, "No face detected"
            
            # Normalize embedding
            embedding_norm = np.linalg.norm(embedding)
            if embedding_norm > 0:
                embedding = embedding / embedding_norm
            
            # Check if embedding already exists (idempotent indexing)
            existing = db.query(FaceEmbedding).filter(
                FaceEmbedding.photo_id == photo_id,
                FaceEmbedding.session_id == session_id
            ).first()
            
            if existing:
                # Update existing embedding
                existing.embedding = embedding.tolist()
                existing.confidence = float(confidence)
                logger.info(f"Updated existing embedding for photo {photo_id}")
            else:
                # Create new embedding
                face_embedding = FaceEmbedding(
                    photo_id=photo_id,
                    session_id=session_id,
                    embedding=embedding.tolist(),
                    confidence=float(confidence)
                )
                db.add(face_embedding)
                logger.info(f"Created new embedding for photo {photo_id}")
            
            db.commit()
            
            return True, float(confidence), 1, None
            
        except Exception as e:
            logger.error(f"Error indexing photo {photo_id}: {str(e)}")
            db.rollback()
            return False, None, 0, str(e)
    
    def index_photo_from_s3(
        self,
        photo_id: str,
        session_id: str,
        s3_key: str,
        db: Session
    ) -> Tuple[bool, Optional[float], int, Optional[str]]:
        """
        Index a photo from S3 storage.
        
        Args:
            photo_id: Unique photo identifier
            session_id: Photo session UUID
            s3_key: S3 key for the photo
            db: Database session
            
        Returns:
            Tuple of (success, confidence, faces_detected, error_message)
        """
        try:
            # Download image from S3
            image_data = download_image(s3_key)
            
            if not image_data:
                return False, None, 0, "Failed to download from S3"
            
            # Index the photo
            return self.index_photo(photo_id, session_id, image_data, db)
            
        except Exception as e:
            logger.error(f"Error downloading photo {photo_id} from S3: {str(e)}")
            return False, None, 0, f"S3 download error: {str(e)}"
    
    def index_batch(
        self,
        session_id: str,
        photos: List[Tuple[str, str]],
        db: Session
    ) -> Tuple[int, int, List[str]]:
        """
        Index multiple photos in batch.
        
        Args:
            session_id: Photo session UUID
            photos: List of (photo_id, s3_key) tuples
            db: Database session
            
        Returns:
            Tuple of (indexed_count, failed_count, error_messages)
        """
        indexed = 0
        failed = 0
        errors = []
        
        for photo_id, s3_key in photos:
            success, confidence, faces, error = self.index_photo_from_s3(
                photo_id, session_id, s3_key, db
            )
            
            if success:
                indexed += 1
            else:
                failed += 1
                errors.append(f"{photo_id}: {error}")
        
        logger.info(f"Batch indexing completed: {indexed} indexed, {failed} failed")
        
        return indexed, failed, errors
    
    def delete_session(
        self,
        session_id: str,
        db: Session
    ) -> int:
        """
        Delete all embeddings for a session.
        
        Args:
            session_id: Photo session UUID
            db: Database session
            
        Returns:
            Number of embeddings deleted
        """
        try:
            count = db.query(FaceEmbedding).filter(
                FaceEmbedding.session_id == session_id
            ).delete()
            
            db.commit()
            
            logger.info(f"Deleted {count} embeddings for session {session_id}")
            
            return count
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            db.rollback()
            raise
    
    def get_session_status(
        self,
        session_id: str,
        db: Session
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Get indexing status for a session.
        
        Args:
            session_id: Photo session UUID
            db: Database session
            
        Returns:
            Tuple of (indexed, photo_count, last_indexed_timestamp)
        """
        try:
            # Count embeddings
            count = db.query(FaceEmbedding).filter(
                FaceEmbedding.session_id == session_id
            ).count()
            
            # Get last indexed timestamp
            last_indexed = None
            if count > 0:
                result = db.query(func.max(FaceEmbedding.created_at)).filter(
                    FaceEmbedding.session_id == session_id
                ).scalar()
                
                if result:
                    last_indexed = result.isoformat()
            
            indexed = count > 0
            
            return indexed, count, last_indexed
            
        except Exception as e:
            logger.error(f"Error getting session status {session_id}: {str(e)}")
            raise
    
    def load_embeddings_from_s3(
        self,
        session_id: str,
        db: Session
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Load embeddings from S3 for a session.
        
        This function downloads all photos from S3 for a given session
        and indexes them in the local vector database.
        
        Args:
            session_id: Photo session UUID
            db: Database session
            
        Returns:
            Tuple of (success, indexed_count, error_message)
        """
        try:
            from core.s3 import list_s3_objects
            
            # List all objects in S3 for this session
            prefix = f"embeddings/{session_id}/"
            logger.info(f"Searching S3 for embeddings with prefix: {prefix}")
            
            s3_keys = list_s3_objects(prefix)
            
            if not s3_keys:
                logger.warning(f"No embeddings found in S3 for session {session_id}")
                return False, 0, "No embeddings found in S3"
            
            logger.info(f"Found {len(s3_keys)} objects in S3 for session {session_id}")
            
            # Index each photo from S3
            indexed = 0
            failed = 0
            
            for s3_key in s3_keys:
                # Extract photo_id from s3_key (e.g., "embeddings/session-id/photo123.jpg" -> "photo123")
                photo_id = s3_key.split('/')[-1].split('.')[0]
                
                success, confidence, faces, error = self.index_photo_from_s3(
                    photo_id, session_id, s3_key, db
                )
                
                if success:
                    indexed += 1
                else:
                    failed += 1
                    logger.warning(f"Failed to index {photo_id} from S3: {error}")
            
            logger.info(f"S3 sync completed: {indexed} indexed, {failed} failed")
            
            if indexed == 0:
                return False, 0, f"Failed to index any photos from S3 ({failed} failed)"
            
            return True, indexed, None
            
        except Exception as e:
            logger.error(f"Error loading embeddings from S3 for session {session_id}: {str(e)}")
            return False, 0, str(e)


# Singleton instance
_indexing_service: Optional[IndexingService] = None


def get_indexing_service() -> IndexingService:
    """
    Get singleton IndexingService instance.
    
    Returns:
        IndexingService: Singleton instance
    """
    global _indexing_service
    
    if _indexing_service is None:
        _indexing_service = IndexingService()
    
    return _indexing_service
