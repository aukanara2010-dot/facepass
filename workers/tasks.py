from workers.celery_app import celery_app
from celery.utils.log import get_task_logger
import numpy as np

logger = get_task_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def test_task(self, message: str = "Hello from Celery!"):
    """
    Test task to verify Celery is working
    """
    logger.info(f"Executing test task: {message}")
    return f"Task executed: {message}"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_face_embedding(self, face_id: int, s3_key: str, event_id: int):
    """
    Process face image: extract embedding and store in vector database
    
    This task:
    1. Downloads image from S3
    2. Detects face using InsightFace
    3. Extracts embedding vector (512-dimensional)
    4. Stores embedding in vector database WITH event_id for filtering
    5. Updates Face record with confidence score
    
    Args:
        face_id: ID of the Face record
        s3_key: S3 key of the uploaded image
        event_id: ID of the event (for denormalized filtering)
    
    Returns:
        dict: Processing result with face_id and confidence
        
    Raises:
        Exception: If face detection fails or no face found
    """
    try:
        logger.info(f"Processing face embedding for face_id={face_id}, event_id={event_id}, s3_key={s3_key}")
        
        # Import here to avoid circular imports
        from core.database import MainSessionLocal, VectorSessionLocal
        from core.s3 import download_image
        from models.face import Face, FaceEmbedding
        from services.face_recognition import get_face_recognition_service
        
        # Download image from S3
        logger.info(f"Downloading image from S3: {s3_key}")
        image_data = download_image(s3_key)
        
        # Extract face embedding using InsightFace
        logger.info("Extracting face embedding with InsightFace...")
        face_service = get_face_recognition_service()
        
        try:
            embeddings = face_service.get_embeddings(image_data)
            
            if len(embeddings) == 0:
                logger.warning(f"No face detected in image face_id={face_id}")
                # Update Face record with 0 confidence to indicate no face found
                main_db = MainSessionLocal()
                try:
                    face = main_db.query(Face).filter(Face.id == face_id).first()
                    if face:
                        face.confidence = 0.0
                        main_db.commit()
                finally:
                    main_db.close()
                
                return {
                    "face_id": face_id,
                    "event_id": event_id,
                    "confidence": 0.0,
                    "status": "no_face_detected",
                    "message": "No face detected in image"
                }
            
            # Use first face if multiple detected
            embedding, confidence = embeddings[0]
            
            if len(embeddings) > 1:
                logger.warning(f"Multiple faces detected ({len(embeddings)}) in face_id={face_id}, using first face")
            
            logger.info(f"Face detected with confidence: {confidence:.3f}")
            
        except RuntimeError as e:
            logger.error(f"InsightFace not initialized: {e}")
            raise
        except ValueError as e:
            logger.error(f"Failed to process image: {e}")
            raise
        
        # Convert embedding to list for storage
        embedding_list = embedding.tolist()
        
        # Store embedding in vector database WITH event_id
        vector_db = VectorSessionLocal()
        try:
            face_embedding = FaceEmbedding(
                face_id=face_id,
                event_id=event_id,  # IMPORTANT: Store event_id for fast filtering
                embedding=embedding_list
            )
            vector_db.add(face_embedding)
            vector_db.commit()
            logger.info(f"Stored embedding in vector database for face_id={face_id}, event_id={event_id}")
        finally:
            vector_db.close()
        
        # Update Face record with confidence
        main_db = MainSessionLocal()
        try:
            face = main_db.query(Face).filter(Face.id == face_id).first()
            if face:
                face.confidence = confidence
                main_db.commit()
                logger.info(f"Updated Face record with confidence={confidence:.3f}")
        finally:
            main_db.close()
        
        return {
            "face_id": face_id,
            "event_id": event_id,
            "confidence": float(confidence),
            "status": "success",
            "faces_detected": len(embeddings)
        }
        
    except Exception as exc:
        logger.error(f"Error processing face embedding: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def search_similar_faces_task(self, image_data: bytes, event_id: int, threshold: float = 0.7, limit: int = 10):
    """
    Search for similar faces using vector similarity WITHIN A SPECIFIC EVENT
    
    **CRITICAL**: This task MUST filter by event_id to only search within one event.
    This prevents attendees from seeing photos from other events.
    
    Args:
        image_data: Selfie image data from attendee
        event_id: Event ID to search within (REQUIRED)
        threshold: Similarity threshold (0.0-1.0)
        limit: Maximum number of results
    
    Returns:
        dict: Search results with matching faces from this event only
    """
    try:
        logger.info(f"Searching for similar faces in event_id={event_id}, threshold={threshold}, limit={limit}")
        
        from core.database import MainSessionLocal, VectorSessionLocal
        from models.face import Face, FaceEmbedding
        from services.face_recognition import get_face_recognition_service
        from sqlalchemy import text
        
        # Extract embedding from uploaded selfie using InsightFace
        logger.info("Extracting embedding from search image...")
        face_service = get_face_recognition_service()
        
        try:
            query_embedding, confidence = face_service.extract_single_embedding(image_data)
            
            if query_embedding is None:
                logger.warning("No face detected in search image")
                return {
                    "results": [],
                    "count": 0,
                    "event_id": event_id,
                    "status": "no_face_detected",
                    "message": "No face detected in uploaded image"
                }
            
            logger.info(f"Search face detected with confidence: {confidence:.3f}")
            
            # Normalize the embedding for consistent similarity calculation
            import numpy as np
            embedding_norm = np.linalg.norm(query_embedding)
            if embedding_norm > 0:
                query_embedding = query_embedding / embedding_norm
                logger.info(f"Search embedding normalized (original norm: {embedding_norm:.6f})")
            else:
                logger.warning("Zero search embedding detected, cannot normalize")
            
        except Exception as e:
            logger.error(f"Failed to extract embedding from search image: {e}")
            raise
        
        # Convert embedding to list for SQL query
        query_embedding_list = query_embedding.tolist()
        query_embedding_str = '[' + ','.join(map(str, query_embedding_list)) + ']'
        
        # Search in vector database WITH event_id filter
        vector_db = VectorSessionLocal()
        main_db = MainSessionLocal()
        
        try:
            # CRITICAL: Filter by event_id to only search within this event
            # Using pgvector's <-> operator for cosine distance
            # Lower distance = more similar
            
            logger.info(f"Filtering search to event_id={event_id}")
            
            # Vector similarity search with event_id filter
            # Using cosine similarity <=> for robust vector comparison
            query = text(f"""
                SELECT 
                    face_id,
                    event_id,
                    1 - (embedding <=> :query_embedding) as similarity
                FROM face_embeddings
                WHERE event_id = :event_id
                    AND (1 - (embedding <=> :query_embedding)) >= :threshold
                ORDER BY embedding <=> :query_embedding ASC
                LIMIT :limit
            """)
            
            result = vector_db.execute(
                query,
                {
                    "query_embedding": query_embedding_str,
                    "event_id": event_id,
                    "threshold": threshold,
                    "limit": limit
                }
            )
            
            results = []
            for row in result:
                face_id = row[0]
                similarity = float(row[2])
                
                # Get Face details from main database
                face = main_db.query(Face).filter(Face.id == face_id).first()
                if face:
                    results.append({
                        "face_id": face.id,
                        "event_id": face.event_id,
                        "similarity": similarity,
                        "image_url": face.image_url
                    })
            
            logger.info(f"Found {len(results)} matching faces in event_id={event_id} above threshold {threshold}")
            
            return {
                "results": results,
                "count": len(results),
                "event_id": event_id,
                "status": "success",
                "query_confidence": float(confidence)
            }
            
        finally:
            vector_db.close()
            main_db.close()
            
    except Exception as exc:
        logger.error(f"Error searching similar faces: {exc}")
        raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def sync_event_photos(self, event_id: int, s3_prefix: str):
    """
    Sync photos from S3 to database (bulk import)
    
    This task:
    1. Lists all files in S3 with given prefix
    2. Checks which files are already in database
    3. For new files:
       - Creates Face record with original URL
       - Triggers process_face_embedding task
    
    **Important:** 
    - Searches in previews/ folder
    - Saves originals/ URL in database
    
    Args:
        event_id: Event ID to sync photos for
        s3_prefix: S3 prefix to search (e.g., "events/1/previews/")
    
    Returns:
        dict: Sync statistics
    """
    try:
        logger.info(f"Starting S3 sync for event_id={event_id}, prefix={s3_prefix}")
        
        from core.database import MainSessionLocal
        from core.s3 import list_s3_objects
        from models.face import Face
        from models.event import Event
        from core.config import get_settings
        
        settings = get_settings()
        
        # Validate event exists
        main_db = MainSessionLocal()
        try:
            event = main_db.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise ValueError(f"Event {event_id} not found")
            
            logger.info(f"Syncing photos for event: {event.name}")
            
            # List all objects in S3 with prefix
            logger.info(f"Listing S3 objects with prefix: {s3_prefix}")
            s3_objects = list_s3_objects(s3_prefix)
            
            if len(s3_objects) == 0:
                logger.warning(f"No objects found with prefix: {s3_prefix}")
                return {
                    "event_id": event_id,
                    "s3_prefix": s3_prefix,
                    "total_found": 0,
                    "new_photos": 0,
                    "skipped": 0,
                    "status": "completed",
                    "message": "No photos found in S3"
                }
            
            logger.info(f"Found {len(s3_objects)} objects in S3")
            
            # Get existing s3_keys from database
            existing_faces = main_db.query(Face.s3_key).filter(Face.event_id == event_id).all()
            existing_keys = {face.s3_key for face in existing_faces}
            
            logger.info(f"Found {len(existing_keys)} existing photos in database")
            
            # Process new photos
            new_photos = 0
            skipped = 0
            
            for s3_key in s3_objects:
                # Skip if already in database
                if s3_key in existing_keys:
                    skipped += 1
                    continue
                
                # Convert preview path to original path
                # Example: "events/1/previews/photo.jpg" -> "events/1/originals/photo.jpg"
                if "/previews/" in s3_key:
                    original_key = s3_key.replace("/previews/", "/originals/")
                else:
                    # If not in previews folder, use as-is
                    original_key = s3_key
                
                # Construct image URL for original
                image_url = f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{original_key}"
                
                # Create Face record
                face = Face(
                    event_id=event_id,
                    image_url=image_url,
                    s3_key=s3_key,  # Store preview key for processing
                    confidence=0.0  # Will be updated by Celery task
                )
                main_db.add(face)
                main_db.flush()  # Get face.id without committing
                
                # Trigger async task to process embedding
                # Process from preview but store original URL
                process_face_embedding.delay(face.id, s3_key, event_id)
                
                new_photos += 1
                
                if new_photos % 10 == 0:
                    logger.info(f"Processed {new_photos} new photos...")
            
            # Commit all new faces
            main_db.commit()
            
            logger.info(f"S3 sync completed: {new_photos} new photos, {skipped} skipped")
            
            return {
                "event_id": event_id,
                "s3_prefix": s3_prefix,
                "total_found": len(s3_objects),
                "new_photos": new_photos,
                "skipped": skipped,
                "status": "completed",
                "message": f"Successfully synced {new_photos} new photos"
            }
            
        finally:
            main_db.close()
            
    except Exception as exc:
        logger.error(f"Error syncing S3 photos: {exc}")
        raise self.retry(exc=exc)
