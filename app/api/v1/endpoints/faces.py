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
                1 - (embedding <-> :query_embedding) as similarity
            FROM face_embeddings
            WHERE event_id = :event_id
                AND (1 - (embedding <-> :query_embedding)) >= :threshold
            ORDER BY embedding <-> :query_embedding
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
