from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.api.deps import get_db, get_vector_db_session
from app.schemas.face import (
    FaceUploadResponse, 
    FaceSearchResponse, 
    FaceSearchResult,
    S3SyncRequest,
    S3SyncResponse
)
from models.face import Face, FaceEmbedding
from models.event import Event
from core.s3 import upload_image
from workers.tasks import process_face_embedding, search_similar_faces_task, sync_event_photos

router = APIRouter()


@router.post("/upload", response_model=FaceUploadResponse)
async def upload_face(
    event_id: int = Form(..., description="Event ID where this photo was taken"),
    file: UploadFile = File(..., description="Photo file uploaded by photographer"),
    db: Session = Depends(get_db)
):
    """
    Upload face image for an event (photographer uploads)
    
    This endpoint is used by photographers to upload photos from an event.
    
    Workflow:
    1. Validates the event exists
    2. Uploads image to S3
    3. Creates Face record in database
    4. Triggers async Celery task to extract embedding
    """
    # Validate event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file data
    file_data = await file.read()
    
    # Generate unique S3 key
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    s3_key = f"events/{event_id}/{uuid.uuid4()}.{file_extension}"
    
    # Upload to S3
    try:
        image_url = upload_image(file_data, s3_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
    
    # Create Face record
    face = Face(
        event_id=event_id,
        image_url=image_url,
        s3_key=s3_key,
        confidence=0.0  # Will be updated by Celery task
    )
    db.add(face)
    db.commit()
    db.refresh(face)
    
    # Trigger async task to process embedding
    task = process_face_embedding.delay(face.id, s3_key, event_id)
    
    return FaceUploadResponse(
        face_id=face.id,
        image_url=image_url,
        confidence=face.confidence,
        task_id=task.id
    )


@router.get("/event/{event_id}", response_model=List[FaceUploadResponse])
async def get_event_faces(event_id: int, db: Session = Depends(get_db)):
    """
    Get all faces for a specific event
    
    Used by photographers to see all uploaded photos for an event.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    faces = db.query(Face).filter(Face.event_id == event_id).all()
    
    return [
        FaceUploadResponse(
            face_id=face.id,
            image_url=face.image_url,
            confidence=face.confidence,
            task_id=""  # Historical records don't have task_id
        )
        for face in faces
    ]


@router.get("/{face_id}")
async def get_face(face_id: int, db: Session = Depends(get_db)):
    """
    Get face details by ID
    """
    face = db.query(Face).filter(Face.id == face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Face not found")
    
    return {
        "id": face.id,
        "event_id": face.event_id,
        "image_url": face.image_url,
        "s3_key": face.s3_key,
        "confidence": face.confidence,
        "created_at": face.created_at
    }


@router.delete("/{face_id}", status_code=204)
async def delete_face(face_id: int, db: Session = Depends(get_db)):
    """
    Delete face by ID
    """
    face = db.query(Face).filter(Face.id == face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Face not found")
    
    db.delete(face)
    db.commit()
    return None


@router.post("/search", response_model=FaceSearchResponse)
async def search_faces(
    event_id: int = Form(..., description="Event ID to search within"),
    file: UploadFile = File(..., description="Selfie photo from attendee"),
    threshold: float = Form(0.7, description="Similarity threshold (0.0-1.0)"),
    limit: int = Form(10, description="Maximum number of results"),
    db: Session = Depends(get_db),
    vector_db: Session = Depends(get_vector_db_session)
):
    """
    Search for similar faces within an event (attendee searches their photos)
    
    **MAIN ENDPOINT FOR ATTENDEES**
    
    This is the core functionality: an attendee uploads their selfie
    and the system finds all photos of them from the event.
    
    Workflow:
    1. Validates event exists
    2. Extracts embedding from uploaded selfie using InsightFace
    3. Searches for similar faces ONLY within this event using pgvector
    4. Returns matching photos above threshold
    
    Args:
        event_id: The event to search within
        file: Selfie image from attendee
        threshold: Minimum similarity score (0.7 = 70% similar)
        limit: Maximum number of photos to return
    
    Returns:
        List of matching photos with similarity scores
    """
    import time
    from sqlalchemy import text
    from services.face_recognition import get_face_recognition_service
    
    start_time = time.time()
    
    # Validate event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file data
    file_data = await file.read()
    
    # Extract embedding from uploaded selfie using InsightFace
    try:
        face_service = get_face_recognition_service()
        query_embedding, confidence = face_service.extract_single_embedding(file_data)
        
        if query_embedding is None:
            # No face detected in selfie
            return FaceSearchResponse(
                results=[],
                query_time_ms=0.0,
                task_id=None
            )
        
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Face recognition service error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")
    
    # Convert embedding to list for SQL query
    query_embedding_list = query_embedding.tolist()
    query_embedding_str = '[' + ','.join(map(str, query_embedding_list)) + ']'
    
    # Perform vector similarity search with event_id filter
    # Using <-> operator for cosine distance (lower = more similar)
    # Formula: similarity = 1 - distance
    try:
        query = text("""
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
        
        # Fetch matching faces from main database
        results = []
        for row in result:
            face_id = row[0]
            similarity = float(row[2])
            
            # Get Face details from main database
            face = db.query(Face).filter(Face.id == face_id).first()
            if face:
                results.append(
                    FaceSearchResult(
                        face_id=face.id,
                        event_id=face.event_id,
                        similarity=similarity,
                        image_url=face.image_url
                    )
                )
        
        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000
        
        return FaceSearchResponse(
            results=results,
            query_time_ms=query_time_ms,
            task_id=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search-session", response_model=dict)
async def search_faces_in_session(
    session_id: str = Form(..., description="Photo session UUID to search within"),
    file: UploadFile = File(..., description="Selfie photo from client"),
    threshold: float = Form(0.7, description="Similarity threshold (0.0-1.0)"),
    limit: int = Form(50, description="Maximum number of results"),
    db: Session = Depends(get_db),
    vector_db: Session = Depends(get_vector_db_session)
):
    """
    Search for similar faces within a photo session (FacePass functionality)
    
    **NEW ENDPOINT FOR FACEPASS SESSIONS**
    
    This endpoint allows clients to find their photos from a specific photo session
    by uploading a selfie. It integrates with the external Pixora database to
    fetch photo metadata and URLs.
    
    Workflow:
    1. Validates session exists and FacePass is enabled
    2. Extracts embedding from uploaded selfie using InsightFace
    3. Searches for similar faces in vector database filtered by session
    4. Fetches photo details from external Pixora database
    5. Returns matching photos with preview URLs and similarity scores
    
    Args:
        session_id: The photo session UUID to search within
        file: Selfie image from client
        threshold: Minimum similarity score (0.7 = 70% similar)
        limit: Maximum number of photos to return
    
    Returns:
        Dictionary with matches array containing photo details and similarity scores
    """
    import time
    import logging
    from sqlalchemy import text
    from services.face_recognition import get_face_recognition_service
    from core.database import get_pixora_db
    from models.photo_session import PhotoSession
    
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    logger.info(f"Starting face search for session {session_id}")
    
    # Validate session exists and FacePass is enabled
    pixora_db = None
    try:
        pixora_db = next(get_pixora_db())
        session = pixora_db.query(PhotoSession).filter(PhotoSession.id == session_id).first()
        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.is_facepass_active():
            logger.warning(f"FacePass not enabled for session: {session_id}")
            raise HTTPException(status_code=403, detail="FacePass is not enabled for this session")
            
        logger.info(f"Session validated: {session.name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session validation error: {str(e)}")
    finally:
        if pixora_db:
            pixora_db.close()
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        logger.warning(f"Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file data
    try:
        file_data = await file.read()
        logger.info(f"Read file data: {len(file_data)} bytes")
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Extract embedding from uploaded selfie using InsightFace
    try:
        logger.info("Extracting face embedding...")
        face_service = get_face_recognition_service()
        query_embedding, confidence = face_service.extract_single_embedding(file_data)
        
        if query_embedding is None:
            logger.info("No face detected in uploaded image")
            return {
                "matches": [],
                "query_time_ms": (time.time() - start_time) * 1000,
                "message": "No face detected in uploaded image"
            }
        
        logger.info(f"Face embedding extracted with confidence: {confidence}")
        
        # Normalize the embedding for consistent similarity calculation
        import numpy as np
        embedding_norm = np.linalg.norm(query_embedding)
        if embedding_norm > 0:
            query_embedding = query_embedding / embedding_norm
            logger.info(f"Embedding normalized (original norm: {embedding_norm:.6f})")
        else:
            logger.warning("Zero embedding detected, cannot normalize")
        
        # Normalize the embedding for consistent similarity calculation
        import numpy as np
        embedding_norm = np.linalg.norm(query_embedding)
        if embedding_norm > 0:
            query_embedding = query_embedding / embedding_norm
            logger.info(f"Embedding normalized (original norm: {embedding_norm:.6f})")
        else:
            logger.warning("Zero embedding detected, cannot normalize")
        
    except RuntimeError as e:
        logger.error(f"Face recognition service error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Face recognition service error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid image: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to process image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")
    
    # Convert embedding to list for SQL query
    try:
        query_embedding_list = query_embedding.tolist()
        query_embedding_str = '[' + ','.join(map(str, query_embedding_list)) + ']'
        logger.info(f"Embedding converted to string format (length: {len(query_embedding_str)})")
    except Exception as e:
        logger.error(f"Error converting embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing embedding: {str(e)}")
    
    # Check if session is already indexed, if not - index it automatically
    indexing_start_time = time.time()
    indexing_status = "not_needed"
    indexing_progress = {}
    
    try:
        from services.photo_indexing import get_photo_indexing_service
        
        logger.info(f"Checking if session {session_id} is indexed...")
        indexing_service = get_photo_indexing_service()
        is_indexed, embedding_count = indexing_service.check_session_indexed(session_id, vector_db)
        
        if not is_indexed:
            logger.info(f"Session {session_id} not indexed. Starting automatic indexing...")
            indexing_status = "indexing"
            
            # First, scan to get total photo count for progress tracking
            try:
                photo_keys = indexing_service.scan_session_photos(session_id, "auto")
                total_photos = len(photo_keys)
                logger.info(f"Found {total_photos} photos to index")
                
                indexing_progress = {
                    "status": "scanning_complete",
                    "total_photos": total_photos,
                    "processed_photos": 0,
                    "successful_photos": 0,
                    "estimated_time_remaining": total_photos * 2  # Rough estimate: 2 seconds per photo
                }
                
                if total_photos == 0:
                    logger.warning(f"No photos found for session {session_id}")
                    return {
                        "matches": [],
                        "query_time_ms": (time.time() - start_time) * 1000,
                        "message": "No photos found in this session",
                        "indexing_status": "no_photos",
                        "indexing_progress": indexing_progress
                    }
                
                # Limit photos for reasonable processing time (max 10 minutes at 2 sec/photo = 300 photos)
                max_photos_for_realtime = min(total_photos, 300)
                if total_photos > max_photos_for_realtime:
                    logger.warning(f"Session has {total_photos} photos, limiting to {max_photos_for_realtime} for real-time processing")
                
            except Exception as e:
                logger.error(f"Error scanning photos: {str(e)}")
                return {
                    "matches": [],
                    "query_time_ms": (time.time() - start_time) * 1000,
                    "message": f"Error scanning photos: {str(e)}",
                    "indexing_status": "scan_error",
                    "indexing_progress": {"error": str(e)}
                }
            
            # Perform automatic indexing with progress tracking
            try:
                processed_count, success_count, error_messages = indexing_service.index_session_photos(
                    session_id, vector_db, max_photos=max_photos_for_realtime
                )
                
                indexing_time = time.time() - indexing_start_time
                logger.info(f"Indexing completed: {success_count}/{processed_count} photos in {indexing_time:.2f}s")
                
                indexing_progress.update({
                    "status": "completed",
                    "processed_photos": processed_count,
                    "successful_photos": success_count,
                    "failed_photos": processed_count - success_count,
                    "indexing_time_seconds": indexing_time,
                    "photos_per_second": processed_count / indexing_time if indexing_time > 0 else 0
                })
                
                if error_messages:
                    logger.warning(f"Indexing errors: {error_messages[:5]}")
                    indexing_progress["sample_errors"] = error_messages[:5]
                
                if success_count == 0:
                    logger.warning(f"No photos were successfully indexed for session {session_id}")
                    return {
                        "matches": [],
                        "query_time_ms": (time.time() - start_time) * 1000,
                        "message": f"No photos could be indexed for this session. Processed {processed_count} photos.",
                        "indexing_status": "indexing_failed",
                        "indexing_progress": indexing_progress,
                        "indexing_errors": error_messages[:10]
                    }
                
                indexing_status = "completed"
                logger.info(f"Session {session_id} indexed successfully with {success_count} photos")
                
            except Exception as e:
                logger.error(f"Error during indexing: {str(e)}")
                indexing_status = "error"
                indexing_progress["error"] = str(e)
                
                return {
                    "matches": [],
                    "query_time_ms": (time.time() - start_time) * 1000,
                    "message": f"Indexing failed: {str(e)}",
                    "indexing_status": "indexing_error",
                    "indexing_progress": indexing_progress
                }
        else:
            indexing_status = "already_indexed"
            indexing_progress = {
                "status": "already_indexed",
                "existing_embeddings": embedding_count
            }
            logger.info(f"Session {session_id} already indexed with {embedding_count} embeddings")
            
    except Exception as e:
        logger.error(f"Error during session indexing check: {str(e)}")
        indexing_status = "check_error"
        indexing_progress = {"error": str(e)}
        # Continue with search despite indexing error
        logger.warning("Continuing with search despite indexing check error")
    
    # Perform vector similarity search with session_id filter
    try:
        logger.info(f"Searching for similar faces in session {session_id} with threshold {threshold}")
        
        # First, get ALL similarities to find the maximum (for debugging)
        max_similarity_query = text("""
            SELECT 
                fe.photo_id,
                1 - (fe.embedding <=> :query_embedding) as similarity
            FROM face_embeddings fe
            WHERE fe.session_id = :session_id
            ORDER BY fe.embedding <=> :query_embedding ASC
            LIMIT 10
        """)
        
        max_result = vector_db.execute(
            max_similarity_query,
            {
                "query_embedding": query_embedding_str,
                "session_id": session_id
            }
        )
        
        # Log maximum similarities found (for debugging)
        max_similarities = []
        for row in max_result:
            similarity = float(row[1])
            max_similarities.append(similarity)
        
        if max_similarities:
            max_similarity = max(max_similarities)
            logger.info(f"SIMILARITY DEBUG - Max similarity found: {max_similarity:.4f}, Top 5 similarities: {sorted(max_similarities, reverse=True)[:5]}")
            print(f"SIMILARITY DEBUG - Session {session_id}: Max similarity = {max_similarity:.4f}, Threshold = {threshold}")
        else:
            logger.info(f"SIMILARITY DEBUG - No embeddings found for session {session_id}")
            print(f"SIMILARITY DEBUG - Session {session_id}: No embeddings found")
        
        # Now get matches above threshold using cosine similarity (best for any vectors)
        query = text("""
            SELECT 
                fe.photo_id,
                1 - (fe.embedding <=> :query_embedding) as similarity
            FROM face_embeddings fe
            WHERE fe.session_id = :session_id
                AND (1 - (fe.embedding <=> :query_embedding)) >= :threshold
            ORDER BY fe.embedding <=> :query_embedding ASC
            LIMIT :limit
        """)
        
        result = vector_db.execute(
            query,
            {
                "query_embedding": query_embedding_str,
                "session_id": session_id,
                "threshold": threshold,
                "limit": limit
            }
        )
        
        # Collect photo IDs and similarities
        photo_matches = []
        for row in result:
            photo_id = row[0]  # photo_id from vector database
            similarity = float(row[1])
            
            photo_matches.append({
                "photo_id": photo_id,
                "similarity": similarity
            })
        
        logger.info(f"Found {len(photo_matches)} matches above threshold {threshold} in vector database")
        if photo_matches:
            match_similarities = [m["similarity"] for m in photo_matches]
            logger.info(f"SIMILARITY DEBUG - Matches above threshold: {sorted(match_similarities, reverse=True)}")
            print(f"SIMILARITY DEBUG - Session {session_id}: {len(photo_matches)} matches above {threshold}, similarities: {sorted(match_similarities, reverse=True)}")
        else:
            logger.info(f"SIMILARITY DEBUG - No matches above threshold {threshold}")
            print(f"SIMILARITY DEBUG - Session {session_id}: No matches above threshold {threshold}, max found was {max_similarities[0] if max_similarities else 'N/A'}")
        
        # If no matches found in vector database
        if not photo_matches:
            logger.info("No matching faces found in vector database")
            return {
                "matches": [],
                "query_time_ms": (time.time() - start_time) * 1000,
                "message": "No matching faces found in this session"
            }
        
        # Fetch photo details from external Pixora database
        photo_ids = [match["photo_id"] for match in photo_matches]
        logger.info(f"Fetching details for {len(photo_ids)} photos from Pixora database")
        
        pixora_db = None
        try:
            pixora_db = next(get_pixora_db())
            
            # Query external Pixora database for photo details
            # Note: photo_id from our vector DB corresponds to file_name in Pixora DB (without extension)
            # We search by file_name pattern since photo_id might be timestamp-hash format
            
            # Create a simpler query that searches by file_name patterns
            photo_id_conditions = []
            query_params = {"session_id": session_id}
            
            for i, photo_id in enumerate(photo_ids):
                param_name = f"photo_id_{i}"
                # Try exact match and with common extensions
                photo_id_conditions.append(f"""
                    (file_name = :{param_name} 
                     OR file_name = :{param_name} || '.jpg'
                     OR file_name = :{param_name} || '.jpeg'
                     OR file_name = :{param_name} || '.png'
                     OR file_name = :{param_name} || '.webp')
                """)
                query_params[param_name] = photo_id
            
            photos_query_str = f"""
                SELECT id, file_name, preview_path, file_path, created_at
                FROM public.photos 
                WHERE photo_session_id = :session_id
                    AND ({' OR '.join(photo_id_conditions)})
                ORDER BY created_at DESC
            """
            
            photos_query = text(photos_query_str)
            photos_result = pixora_db.execute(photos_query, query_params)
            
            # Create lookup dictionary for photo details
            photo_details = {}
            for photo_row in photos_result:
                file_name = photo_row[1]
                # Extract photo_id from file_name (remove extension)
                photo_id_from_filename = file_name.split('.')[0] if '.' in file_name else file_name
                
                photo_details[photo_id_from_filename] = {
                    "id": photo_row[0],
                    "file_name": file_name,
                    "preview_path": photo_row[2],
                    "file_path": photo_row[3],
                    "created_at": photo_row[4].isoformat() if photo_row[4] else None
                }
            
            logger.info(f"Retrieved details for {len(photo_details)} photos from Pixora database")
        
        finally:
            if pixora_db:
                pixora_db.close()
        
        # Combine similarity data with photo details
        final_matches = []
        for match in photo_matches:
            photo_id = match["photo_id"]
            if photo_id in photo_details:
                photo_info = photo_details[photo_id]
                final_matches.append({
                    "id": photo_info["id"],
                    "file_name": photo_info["file_name"],
                    "preview_path": photo_info["preview_path"],
                    "file_path": photo_info["file_path"],
                    "similarity": match["similarity"],
                    "created_at": photo_info["created_at"]
                })
        
        # Sort by similarity (highest first)
        final_matches.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Search completed successfully: {len(final_matches)} matches in {query_time_ms:.2f}ms")
        
        # Get final embedding count for response
        final_embedding_count = vector_db.query(FaceEmbedding).filter(
            FaceEmbedding.session_id == session_id
        ).count()
        
        return {
            "matches": final_matches,
            "query_time_ms": query_time_ms,
            "session_id": session_id,
            "session_name": session.name,
            "total_matches": len(final_matches),
            "indexed_photos": final_embedding_count,
            "search_threshold": threshold,
            "indexing_status": indexing_status,
            "indexing_progress": indexing_progress
        }
        
    except Exception as e:
        logger.error(f"Search failed for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/index-session/{session_id}", response_model=dict)
async def index_session_photos(
    session_id: str,
    force_reindex: bool = False,
    max_photos: int = 1000,
    vector_db: Session = Depends(get_vector_db_session)
):
    """
    Manually index photos for a session (Admin endpoint).
    
    This endpoint allows administrators to manually trigger photo indexing
    for a specific session. Useful for:
    - Pre-indexing popular sessions
    - Re-indexing after adding new photos
    - Troubleshooting indexing issues
    
    Args:
        session_id: The photo session UUID to index
        force_reindex: Whether to reindex even if already indexed
        max_photos: Maximum number of photos to process (safety limit)
        vector_db: Database session for vector database
        
    Returns:
        Dictionary with indexing results and statistics
    """
    import time
    import logging
    from services.photo_indexing import get_photo_indexing_service
    from core.database import get_pixora_db
    from models.photo_session import PhotoSession
    
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    logger.info(f"Manual indexing requested for session {session_id}")
    
    # Validate session exists and FacePass is enabled
    pixora_db = None
    try:
        pixora_db = next(get_pixora_db())
        session = pixora_db.query(PhotoSession).filter(PhotoSession.id == session_id).first()
        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.is_facepass_active():
            logger.warning(f"FacePass not enabled for session: {session_id}")
            raise HTTPException(status_code=403, detail="FacePass is not enabled for this session")
            
        logger.info(f"Session validated: {session.name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session validation error: {str(e)}")
    finally:
        if pixora_db:
            pixora_db.close()
    
    # Check current indexing status
    try:
        indexing_service = get_photo_indexing_service()
        is_indexed, current_count = indexing_service.check_session_indexed(session_id, vector_db)
        
        if is_indexed and not force_reindex:
            logger.info(f"Session {session_id} already indexed with {current_count} embeddings")
            return {
                "success": True,
                "message": f"Session already indexed with {current_count} embeddings",
                "session_id": session_id,
                "session_name": session.name,
                "already_indexed": True,
                "embedding_count": current_count,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        # Clear existing embeddings if force reindex
        if force_reindex and current_count > 0:
            logger.info(f"Force reindex: clearing {current_count} existing embeddings")
            vector_db.query(FaceEmbedding).filter(
                FaceEmbedding.session_id == session_id
            ).delete()
            vector_db.commit()
        
        # Perform indexing
        logger.info(f"Starting indexing for session {session_id} (max_photos: {max_photos})")
        processed_count, success_count, error_messages = indexing_service.index_session_photos(
            session_id, vector_db, max_photos=max_photos
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Indexing completed: {success_count}/{processed_count} photos in {processing_time_ms:.2f}ms")
        
        return {
            "success": True,
            "message": f"Successfully indexed {success_count} out of {processed_count} photos",
            "session_id": session_id,
            "session_name": session.name,
            "processed_photos": processed_count,
            "successful_photos": success_count,
            "failed_photos": processed_count - success_count,
            "embedding_count": success_count,
            "processing_time_ms": processing_time_ms,
            "errors": error_messages[:10] if error_messages else [],  # First 10 errors
            "force_reindex": force_reindex
        }
        
    except Exception as e:
        logger.error(f"Indexing failed for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get("/session-index-status/{session_id}", response_model=dict)
async def get_session_index_status(
    session_id: str,
    vector_db: Session = Depends(get_vector_db_session)
):
    """
    Get indexing status for a session.
    
    Args:
        session_id: The photo session UUID to check
        vector_db: Database session for vector database
        
    Returns:
        Dictionary with indexing status and statistics
    """
    import logging
    from services.photo_indexing import get_photo_indexing_service
    from core.database import get_pixora_db
    from models.photo_session import PhotoSession
    from sqlalchemy import text
    
    logger = logging.getLogger(__name__)
    
    # Validate session exists
    pixora_db = None
    try:
        pixora_db = next(get_pixora_db())
        session = pixora_db.query(PhotoSession).filter(PhotoSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session validation error: {str(e)}")
    finally:
        if pixora_db:
            pixora_db.close()
    
    try:
        # Get indexing status
        indexing_service = get_photo_indexing_service()
        is_indexed, embedding_count = indexing_service.check_session_indexed(session_id, vector_db)
        
        # Get additional statistics
        stats = {}
        if is_indexed:
            # Get embedding statistics
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_embeddings,
                    COUNT(DISTINCT photo_id) as unique_photos,
                    AVG(confidence) as avg_confidence,
                    MIN(confidence) as min_confidence,
                    MAX(confidence) as max_confidence,
                    MIN(created_at) as first_indexed,
                    MAX(created_at) as last_indexed
                FROM face_embeddings 
                WHERE session_id = :session_id
            """)
            
            result = vector_db.execute(stats_query, {"session_id": session_id}).fetchone()
            
            if result:
                stats = {
                    "total_embeddings": result[0],
                    "unique_photos": result[1],
                    "avg_confidence": float(result[2]) if result[2] else 0.0,
                    "min_confidence": float(result[3]) if result[3] else 0.0,
                    "max_confidence": float(result[4]) if result[4] else 0.0,
                    "first_indexed": result[5].isoformat() if result[5] else None,
                    "last_indexed": result[6].isoformat() if result[6] else None
                }
        
        return {
            "session_id": session_id,
            "session_name": session.name,
            "is_indexed": is_indexed,
            "embedding_count": embedding_count,
            "facepass_enabled": session.is_facepass_active(),
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting index status for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get index status: {str(e)}")


@router.post("/sync-s3", response_model=S3SyncResponse)
async def sync_s3_photos(
    sync_request: S3SyncRequest,
    db: Session = Depends(get_db)
):
    """
    Sync photos from S3 to database (bulk import)
    
    This endpoint triggers a background task to:
    1. List all files in the specified S3 prefix
    2. Check which files are already in the database
    3. Process new files with InsightFace
    4. Store embeddings in vector database
    
    **Use case:** Photographer uploads many photos to S3 and wants to bulk import them.
    
    Args:
        sync_request: Contains event_uuid and s3_prefix
        
    Returns:
        Task information for tracking progress
        
    Example:
        POST /api/v1/faces/sync-s3
        {
            "event_uuid": "550e8400-e29b-41d4-a716-446655440000",
            "s3_prefix": "events/1/previews/"
        }
    """
    import uuid as uuid_lib
    
    # Validate event exists
    try:
        event_uuid = uuid_lib.UUID(sync_request.event_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    event = db.query(Event).filter(Event.event_uuid == event_uuid).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Trigger background sync task
    task = sync_event_photos.delay(event.id, sync_request.s3_prefix)
    
    return S3SyncResponse(
        task_id=task.id,
        event_id=event.id,
        s3_prefix=sync_request.s3_prefix,
        message=f"Sync task started for event {event.name}"
    )
