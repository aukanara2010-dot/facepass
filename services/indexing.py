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
        db: Session,
        s3_prefix: Optional[str] = None
    ) -> Tuple[int, int, List[str]]:
        """
        Index multiple photos in batch.
        
        Args:
            session_id: Photo session UUID
            photos: List of (photo_id, s3_key) tuples
            db: Database session
            s3_prefix: S3 environment prefix
            
        Returns:
            Tuple of (indexed_count, failed_count, error_messages)
        """
        from core.config import get_settings
        settings = get_settings()
        env_prefix = s3_prefix or settings.S3_ENV_PREFIX
        
        indexed = 0
        failed = 0
        errors = []
        
        for photo_id, s3_key in photos:
            # Ensure s3_key starts with the correct prefix
            if not s3_key.startswith(f"{env_prefix}/"):
                # If it already has a prefix but it's different, we might need to replace it
                # or just prepend if it's missing. Pixora usually sends keys like 'sessions/...'
                # but we want 'staging/sessions/...'
                if not any(s3_key.startswith(p) for p in ["staging/", "production/"]):
                    full_s3_key = f"{env_prefix}/{s3_key}"
                else:
                    # Replace existing prefix if it doesn't match
                    parts = s3_key.split('/', 1)
                    if len(parts) > 1:
                        full_s3_key = f"{env_prefix}/{parts[1]}"
                    else:
                        full_s3_key = f"{env_prefix}/{s3_key}"
            else:
                full_s3_key = s3_key

            success, confidence, faces, error = self.index_photo_from_s3(
                photo_id, session_id, full_s3_key, db
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
        db: Session,
        s3_prefix: Optional[str] = None
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Load embeddings from S3 for a session.
        
        This function downloads photos from S3 originals folder for a given session,
        compares them with existing database records, and only indexes files that
        aren't already in the database.
        
        Args:
            session_id: Photo session UUID
            db: Database session
            s3_prefix: S3 environment prefix
            
        Returns:
            Tuple of (success, indexed_count, error_message)
        """
        try:
            from core.s3 import list_s3_objects, download_image
            from core.config import get_settings
            import os
            from models.face import FaceEmbedding
            from PIL import Image, UnidentifiedImageError
            
            settings = get_settings()
            env_prefix = s3_prefix or settings.S3_ENV_PREFIX
            
            # Construct S3 path dynamically using environment prefix
            prefix = f"{env_prefix}/photos/{session_id}/originals/"
            logger.info(f"Searching S3 for photos with prefix: {prefix}")
            print(f'Scanning S3 path: {prefix}')
            
            s3_keys = list_s3_objects(prefix)
            
            if not s3_keys:
                logger.warning(f"No photos found in S3 for session {session_id}")
                print(f'No photos found in S3 for path: {prefix}')
                return False, 0, f"No photos found in S3 for path: {prefix}"
            
            logger.info(f"Found {len(s3_keys)} photos in S3 for session {session_id}")
            print(f'Found {len(s3_keys)} photos in S3 for session {session_id}')
            
            from core.config import SUPPORTED_EXTENSIONS
            
            # Filter only image files
            image_keys = [key for key in s3_keys if key.lower().endswith(SUPPORTED_EXTENSIONS)]
            
            if not image_keys:
                logger.warning(f"No image files found in S3 for session {session_id}")
                print(f'No image files found in S3 for path: {prefix}')
                return False, 0, f"No image files found in S3 for path: {prefix}"
            
            # Get existing photo_ids from the database for this session
            existing_photo_ids = set()
            existing_records = db.query(FaceEmbedding.photo_id).filter(
                FaceEmbedding.session_id == session_id
            ).all()
            
            for record in existing_records:
                existing_photo_ids.add(record[0].lower())  # Store lowercase for case-insensitive comparison
            
            logger.info(f"Found {len(existing_photo_ids)} existing photo records in database for session {session_id}")
            print(f'Found {len(existing_photo_ids)} existing photo records in database')
            
            # Prepare list of photos to process (only those not in the database)
            photos_to_process = []
            for s3_key in image_keys:
                filename = os.path.basename(s3_key)
                # Get photo_id without extension and convert to lowercase for case-insensitive comparison
                photo_id = os.path.splitext(filename)[0].lower()
                
                if photo_id not in existing_photo_ids:
                    # Store original photo_id (not lowercase) for indexing
                    original_photo_id = os.path.splitext(filename)[0]
                    photos_to_process.append((s3_key, original_photo_id))
            
            logger.info(f"Found {len(photos_to_process)} new photos to process out of {len(image_keys)} total")
            print(f'Processing {len(photos_to_process)} new photos out of {len(image_keys)} total from S3...')
            
            if not photos_to_process:
                logger.info(f"All photos for session {session_id} are already indexed")
                print(f'All photos for session {session_id} are already indexed')
                return True, len(existing_photo_ids), None
            
            # Index each new photo from S3
            indexed = 0
            failed = 0
            
            for s3_key, photo_id in photos_to_process:
                try:
                    print(f'Processing file from S3: {s3_key}')
                    logger.info(f"Processing {os.path.basename(s3_key)} (photo_id: {photo_id})")
                    
                    # Download image from S3
                    image_data = download_image(s3_key)
                    
                    if not image_data:
                        logger.warning(f"Failed to download {s3_key} - file may be empty (0 bytes)")
                        failed += 1
                        continue
                    
                    # Check for zero-byte files or truncated images
                    try:
                        if len(image_data) == 0:
                            logger.warning(f"Zero-byte file detected: {s3_key}")
                            failed += 1
                            continue
                            
                        # Try to open the image to check if it's valid
                        import io
                        Image.open(io.BytesIO(image_data)).verify()
                    except UnidentifiedImageError:
                        logger.warning(f"Truncated or corrupt image detected: {s3_key}")
                        failed += 1
                        continue
                    except Exception as img_err:
                        if "truncated" in str(img_err).lower():
                            logger.warning(f"Truncated image detected: {s3_key} - {str(img_err)}")
                            failed += 1
                            continue
                    
                    # Extract face embedding and index
                    success, confidence, faces, error = self.index_photo(
                        photo_id, session_id, image_data, db
                    )
                    
                    if success:
                        indexed += 1
                        print(f'✓ Indexed {os.path.basename(s3_key)} (confidence: {confidence:.2f})')
                        logger.info(f"Successfully indexed {os.path.basename(s3_key)}")
                    else:
                        failed += 1
                        print(f'✗ Failed to index {os.path.basename(s3_key)}: {error}')
                        logger.warning(f"Failed to index {os.path.basename(s3_key)}: {error}")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing {s3_key}: {str(e)}")
                    print(f'✗ Error processing {s3_key}: {str(e)}')
            
            # Get total indexed count (including previously indexed)
            total_indexed = len(existing_photo_ids) + indexed
            
            logger.info(f"S3 sync completed: {indexed} newly indexed, {failed} failed, {total_indexed} total indexed")
            print(f'S3 sync completed: {indexed} newly indexed, {failed} failed, {total_indexed} total indexed')
            
            # Return success even if no new photos were indexed but existing ones were found
            if indexed == 0 and len(existing_photo_ids) == 0:
                return False, 0, f"Failed to index any photos from S3 ({failed} failed)"
            
            return True, total_indexed, None
            
        except Exception as e:
            logger.error(f"Error loading embeddings from S3 for session {session_id}: {str(e)}")
            print(f'Error loading from S3: {str(e)}')
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
