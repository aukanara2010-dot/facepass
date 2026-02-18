"""
Photo indexing service for automatic face embedding extraction.

This service handles:
- Scanning S3 folders for photos
- Extracting face embeddings using InsightFace
- Storing embeddings in vector database
"""

import logging
import uuid
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.s3 import list_s3_objects, download_image, S3Error
from services.face_recognition import get_face_recognition_service
from models.face import FaceEmbedding
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PhotoIndexingService:
    """Service for automatic photo indexing and face embedding extraction."""
    
    def __init__(self):
        """Initialize the photo indexing service."""
        self.face_service = get_face_recognition_service()
    
    def get_session_s3_prefixes(self, session_id: str, environment: str = "auto") -> List[str]:
        """
        Generate possible S3 prefixes for session photos.
        
        Args:
            session_id: UUID of the photo session
            environment: Environment ("production", "staging", or "auto" for auto-detection)
            
        Returns:
            List of S3 prefix paths to try
        """
        if environment == "auto":
            # Try to detect environment based on current domain/config
            if hasattr(settings, 'DOMAIN') and 'staging' in settings.DOMAIN.lower():
                environment = "staging"
            else:
                environment = "production"
        
        # Multiple possible structures for each environment
        prefixes = []
        
        if environment == "production":
            prefixes = [
                f"production/photos/{session_id}/previews/",
                f"production/photos/{session_id}/",
            ]
        elif environment == "staging":
            prefixes = [
                f"staging/photos/{session_id}/previews/",
                f"staging/photos/{session_id}/",
            ]
        
        return prefixes
    
    def scan_session_photos(self, session_id: str, environment: str = "auto") -> List[str]:
        """
        Scan S3 for photos in the session folder.
        
        Args:
            session_id: UUID of the photo session
            environment: Environment ("production", "staging", or "auto" for auto-detection)
            
        Returns:
            List of S3 object keys for photos
            
        Raises:
            S3Error: If S3 scanning fails
        """
        logger.info(f"Scanning S3 for photos in session {session_id} (environment: {environment})")
        
        try:
            # Get possible prefixes for this environment
            prefixes = self.get_session_s3_prefixes(session_id, environment)
            
            all_objects = []
            found_prefix = None
            
            # Try each prefix until we find photos
            for prefix in prefixes:
                logger.info(f"Trying S3 prefix: {prefix}")
                try:
                    objects = list_s3_objects(prefix)
                    if objects:
                        all_objects = objects
                        found_prefix = prefix
                        logger.info(f"Found {len(objects)} objects in {prefix}")
                        break
                except S3Error:
                    continue
            
            # If no objects found and environment is auto, try the other environment
            if not all_objects and environment == "auto":
                other_env = "staging" if "production" in str(prefixes) else "production"
                logger.info(f"No objects found in current environment, trying {other_env}")
                
                other_prefixes = self.get_session_s3_prefixes(session_id, other_env)
                for prefix in other_prefixes:
                    logger.info(f"Trying alternative S3 prefix: {prefix}")
                    try:
                        objects = list_s3_objects(prefix)
                        if objects:
                            all_objects = objects
                            found_prefix = prefix
                            logger.info(f"Found {len(objects)} objects in {prefix}")
                            break
                    except S3Error:
                        continue
            
            # Filter for image files
            image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
            photo_objects = []
            
            for obj_key in all_objects:
                # Get file extension
                file_ext = '.' + obj_key.lower().split('.')[-1] if '.' in obj_key else ''
                
                if file_ext in image_extensions:
                    photo_objects.append(obj_key)
            
            logger.info(f"Found {len(photo_objects)} photos in session {session_id} (prefix: {found_prefix})")
            return photo_objects
            
        except S3Error as e:
            logger.error(f"S3 error scanning session {session_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error scanning session {session_id}: {str(e)}")
            raise S3Error(f"Failed to scan session photos: {str(e)}")
    
    def extract_photo_id_from_s3_key(self, s3_key: str) -> Optional[str]:
        """
        Extract photo ID from S3 object key.
        
        Expected formats:
        - production/photos/{session_id}/previews/{timestamp}-{photo_id}.jpg
        - staging/photos/{session_id}/previews/{timestamp}-{photo_id}.jpg
        - {session_id}/previews/{photo_id}.jpg (legacy format)
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Photo ID (UUID or timestamp-hash) or None if not extractable
        """
        try:
            # Split the path and get the filename
            filename = s3_key.split('/')[-1]
            
            # Remove extension to get photo ID
            photo_id = filename.split('.')[0]
            
            # Check if it's a timestamp-hash format (like 1769586652601-3880_ht29)
            if '-' in photo_id and len(photo_id) > 10:
                # This is likely a timestamp-hash format, use as is
                return photo_id
            
            # Try to validate as UUID
            try:
                uuid.UUID(photo_id)  # This will raise ValueError if not valid UUID
                return photo_id
            except ValueError:
                # Not a UUID, but might be a valid photo ID anyway
                if len(photo_id) > 5:  # Reasonable minimum length for photo ID
                    return photo_id
                else:
                    logger.warning(f"Photo ID too short: {photo_id} from {s3_key}")
                    return None
            
        except (ValueError, IndexError):
            logger.warning(f"Could not extract photo ID from S3 key: {s3_key}")
            return None
    
    def process_single_photo(
        self, 
        s3_key: str, 
        session_id: str, 
        vector_db: Session
    ) -> Tuple[bool, Optional[str]]:
        """
        Process a single photo: download, extract embeddings, save to database.
        
        Args:
            s3_key: S3 object key for the photo
            session_id: UUID of the photo session
            vector_db: Database session for vector database
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        logger.info(f"Processing photo: {s3_key}")
        
        try:
            # Extract photo ID from S3 key
            photo_id = self.extract_photo_id_from_s3_key(s3_key)
            if not photo_id:
                return False, f"Could not extract photo ID from {s3_key}"
            
            # Check if this photo is already processed
            existing = vector_db.query(FaceEmbedding).filter(
                FaceEmbedding.photo_id == photo_id,
                FaceEmbedding.session_id == session_id
            ).first()
            
            if existing:
                logger.info(f"Photo {photo_id} already processed, skipping")
                return True, None
            
            # Download photo from S3
            try:
                photo_data = download_image(s3_key)
                logger.info(f"Downloaded photo {s3_key}: {len(photo_data)} bytes")
            except S3Error as e:
                return False, f"Failed to download {s3_key}: {str(e)}"
            
            # Extract face embeddings
            try:
                embeddings = self.face_service.get_embeddings(photo_data)
                logger.info(f"Extracted {len(embeddings)} face embeddings from {s3_key}")
                
                if not embeddings:
                    logger.info(f"No faces found in {s3_key}")
                    return True, None  # Not an error, just no faces
                
            except Exception as e:
                return False, f"Face extraction failed for {s3_key}: {str(e)}"
            
            # Save embeddings to database
            saved_count = 0
            for embedding_vector, confidence in embeddings:
                try:
                    # Normalize the embedding for consistent similarity calculation
                    import numpy as np
                    embedding_norm = np.linalg.norm(embedding_vector)
                    if embedding_norm > 0:
                        normalized_embedding = embedding_vector / embedding_norm
                        logger.debug(f"Embedding normalized for {s3_key} (original norm: {embedding_norm:.6f})")
                    else:
                        normalized_embedding = embedding_vector
                        logger.warning(f"Zero embedding detected for {s3_key}, cannot normalize")
                    
                    face_embedding = FaceEmbedding(
                        photo_id=photo_id,
                        session_id=session_id,
                        embedding=normalized_embedding.tolist(),  # Convert normalized numpy array to list
                        confidence=confidence
                    )
                    
                    vector_db.add(face_embedding)
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to save embedding for {s3_key}: {str(e)}")
                    return False, f"Database save failed: {str(e)}"
            
            # Commit the transaction
            vector_db.commit()
            logger.info(f"Saved {saved_count} embeddings for photo {photo_id}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"Unexpected error processing {s3_key}: {str(e)}")
            vector_db.rollback()
            return False, f"Unexpected error: {str(e)}"
    
    def index_session_photos(
        self, 
        session_id: str, 
        vector_db: Session,
        max_photos: int = 1000,
        environment: str = "auto"
    ) -> Tuple[int, int, List[str]]:
        """
        Index all photos in a session by extracting and storing face embeddings.
        
        Args:
            session_id: UUID of the photo session
            vector_db: Database session for vector database
            max_photos: Maximum number of photos to process (safety limit)
            environment: Environment ("production", "staging", or "auto" for auto-detection)
            
        Returns:
            Tuple of (processed_count, success_count, error_messages)
        """
        logger.info(f"Starting photo indexing for session {session_id}")
        
        try:
            # Check if face recognition service is available
            if not self.face_service.initialized:
                error_msg = "Face recognition service not initialized"
                logger.error(error_msg)
                return 0, 0, [error_msg]
            
            # Scan for photos in S3
            try:
                photo_keys = self.scan_session_photos(session_id, environment)
            except S3Error as e:
                error_msg = f"Failed to scan S3 photos: {str(e)}"
                logger.error(error_msg)
                return 0, 0, [error_msg]
            
            if not photo_keys:
                logger.info(f"No photos found for session {session_id}")
                return 0, 0, []
            
            # Limit the number of photos to process
            if len(photo_keys) > max_photos:
                logger.warning(f"Found {len(photo_keys)} photos, limiting to {max_photos}")
                photo_keys = photo_keys[:max_photos]
            
            # Process each photo
            processed_count = 0
            success_count = 0
            error_messages = []
            
            for photo_key in photo_keys:
                processed_count += 1
                
                try:
                    success, error_msg = self.process_single_photo(
                        photo_key, session_id, vector_db
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        error_messages.append(f"{photo_key}: {error_msg}")
                        
                    # Log progress every 10 photos
                    if processed_count % 10 == 0:
                        logger.info(f"Progress: {processed_count}/{len(photo_keys)} photos processed")
                        
                except Exception as e:
                    error_msg = f"Failed to process {photo_key}: {str(e)}"
                    logger.error(error_msg)
                    error_messages.append(error_msg)
            
            logger.info(f"Indexing completed for session {session_id}: "
                       f"{success_count}/{processed_count} photos successful")
            
            return processed_count, success_count, error_messages
            
        except Exception as e:
            error_msg = f"Photo indexing failed for session {session_id}: {str(e)}"
            logger.error(error_msg)
            return 0, 0, [error_msg]
    
    def check_session_indexed(self, session_id: str, vector_db: Session) -> Tuple[bool, int]:
        """
        Check if a session has been indexed (has face embeddings).
        
        Args:
            session_id: UUID of the photo session
            vector_db: Database session for vector database
            
        Returns:
            Tuple of (is_indexed: bool, embedding_count: int)
        """
        try:
            count = vector_db.query(FaceEmbedding).filter(
                FaceEmbedding.session_id == session_id
            ).count()
            
            is_indexed = count > 0
            logger.info(f"Session {session_id} indexed status: {is_indexed} ({count} embeddings)")
            
            return is_indexed, count
            
        except Exception as e:
            logger.error(f"Error checking session index status: {str(e)}")
            return False, 0


# Global instance
_photo_indexing_service = None


def get_photo_indexing_service() -> PhotoIndexingService:
    """
    Get singleton instance of PhotoIndexingService.
    
    Returns:
        PhotoIndexingService instance
    """
    global _photo_indexing_service
    
    if _photo_indexing_service is None:
        _photo_indexing_service = PhotoIndexingService()
    
    return _photo_indexing_service