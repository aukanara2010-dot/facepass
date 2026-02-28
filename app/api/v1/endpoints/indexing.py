"""
Photo indexing endpoints for FacePass microservice.

This module provides API endpoints for indexing photos, managing embeddings,
checking indexing status, health checks, and metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from sqlalchemy.orm import Session
import logging
import time
from typing import Optional

from core.database import get_db
from services.indexing import get_indexing_service
from app.middleware.auth import require_api_key
from app.schemas.indexing import (
    IndexPhotoResponse,
    BatchIndexRequest,
    BatchIndexResponse,
    DeleteSessionResponse,
    SessionStatusResponse
)
from app.utils.validation import (
    validate_image_upload,
    validate_session_id,
    validate_photo_id,
    validate_threshold,
    validate_limit
)
from app.middleware.rate_limit import limiter, INDEXING_RATE_LIMIT, SEARCH_RATE_LIMIT

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/index",
    response_model=IndexPhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index single photo",
    description="Index a single photo by extracting face embedding and storing it in the database",
    dependencies=[Depends(require_api_key)]
)
@limiter.limit(INDEXING_RATE_LIMIT)
async def index_photo(
    request: Request,
    photo_id: str = Form(..., description="Unique photo identifier (UUID or filename)"),
    session_id: str = Form(..., description="Photo session UUID"),
    s3_key: Optional[str] = Form(None, description="S3 key for the photo (if already uploaded)"),
    file: Optional[UploadFile] = File(None, description="Photo file (if not using s3_key)"),
    db: Session = Depends(get_db)
) -> IndexPhotoResponse:
    """
    Index a single photo for face recognition search.
    
    This endpoint accepts either:
    1. A file upload (multipart/form-data)
    2. An S3 key for an already uploaded photo
    
    The service will:
    1. Extract face embedding using InsightFace
    2. Store embedding in vector database
    3. Return indexing result
    
    **Note**: If a photo is indexed multiple times, the embedding will be updated (idempotent).
    
    Args:
        photo_id: Unique identifier for the photo
        session_id: Session UUID this photo belongs to
        s3_key: S3 key if photo is already in storage
        file: Photo file if uploading directly
        db: Database session
        
    Returns:
        IndexPhotoResponse: Indexing result with confidence and faces detected
        
    Raises:
        HTTPException 400: If neither file nor s3_key provided, or invalid file type
        HTTPException 500: If indexing fails
    """
    # Validate inputs
    validate_photo_id(photo_id)
    validate_session_id(session_id)
    
    indexing_service = get_indexing_service()
    
    # Validate input: must provide either file or s3_key
    if not file and not s3_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'file' or 's3_key'"
        )
    
    try:
        if file:
            # Validate and read file
            image_data = await validate_image_upload(file)
            
            # Index from uploaded file
            success, confidence, faces_detected, error = indexing_service.index_photo(
                photo_id, session_id, image_data, db
            )
        else:
            # Index from S3
            success, confidence, faces_detected, error = indexing_service.index_photo_from_s3(
                photo_id, session_id, s3_key, db
            )
        
        if not success:
            return IndexPhotoResponse(
                indexed=False,
                photo_id=photo_id,
                confidence=confidence,
                faces_detected=faces_detected,
                error=error
            )
        
        return IndexPhotoResponse(
            indexed=True,
            photo_id=photo_id,
            confidence=confidence,
            faces_detected=faces_detected,
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing photo {photo_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}"
        )


@router.post(
    "/index/batch",
    response_model=BatchIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index multiple photos in batch",
    description="Index multiple photos at once for better performance",
    dependencies=[Depends(require_api_key)]
)
@limiter.limit(INDEXING_RATE_LIMIT)
async def index_batch(
    request: Request,
    batch_request: BatchIndexRequest,
    db: Session = Depends(get_db)
) -> BatchIndexResponse:
    """
    Index multiple photos in batch.
    
    This endpoint is optimized for indexing many photos at once.
    It processes all photos and returns a summary of successes and failures.
    
    **Note**: This operation is idempotent - photos that are already indexed
    will have their embeddings updated.
    
    Args:
        request: Batch indexing request with session_id and list of photos
        db: Database session
        
    Returns:
        BatchIndexResponse: Summary of indexing results
        
    Raises:
        HTTPException 400: If request is invalid
        HTTPException 500: If batch indexing fails
    """
    indexing_service = get_indexing_service()
    
    if not batch_request.photos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photos list cannot be empty"
        )
    
    try:
        # Convert to list of tuples
        photos = [(item.photo_id, item.s3_key) for item in batch_request.photos]
        
        # Index batch
        indexed, failed, errors = indexing_service.index_batch(
            batch_request.session_id, photos, db
        )
        
        return BatchIndexResponse(
            indexed=indexed,
            failed=failed,
            total=len(photos),
            errors=errors[:10]  # Limit to first 10 errors
        )
        
    except Exception as e:
        logger.error(f"Error in batch indexing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch indexing failed: {str(e)}"
        )


@router.delete(
    "/index/{session_id}",
    response_model=DeleteSessionResponse,
    summary="Delete session embeddings",
    description="Delete all face embeddings for a specific session",
    dependencies=[Depends(require_api_key)]
)
@limiter.limit(INDEXING_RATE_LIMIT)
async def delete_session(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db)
) -> DeleteSessionResponse:
    """
    Delete all face embeddings for a session.
    
    This endpoint removes all indexed photos for a session from the database.
    Use this when a session is deleted or needs to be re-indexed from scratch.
    
    Args:
        session_id: Session UUID to delete
        db: Database session
        
    Returns:
        DeleteSessionResponse: Deletion result with count of removed embeddings
        
    Raises:
        HTTPException 500: If deletion fails
    """
    indexing_service = get_indexing_service()
    
    try:
        embeddings_removed = indexing_service.delete_session(session_id, db)
        
        return DeleteSessionResponse(
            deleted=True,
            session_id=session_id,
            embeddings_removed=embeddings_removed
        )
        
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )


@router.get(
    "/search/status/{session_id}",
    response_model=SessionStatusResponse,
    summary="Get session indexing status",
    description="Check if a session has indexed photos and get statistics"
)
async def get_session_status(
    session_id: str,
    db: Session = Depends(get_db)
) -> SessionStatusResponse:
    """
    Get indexing status for a session.
    
    This endpoint returns information about indexed photos for a session:
    - Whether any photos are indexed
    - Number of indexed photos
    - Timestamp of last indexing
    
    Args:
        session_id: Session UUID to check
        db: Database session
        
    Returns:
        SessionStatusResponse: Session indexing status
        
    Raises:
        HTTPException 500: If status check fails
    """
    indexing_service = get_indexing_service()
    
    try:
        indexed, photo_count, last_indexed = indexing_service.get_session_status(
            session_id, db
        )
        
        return SessionStatusResponse(
            indexed=indexed,
            session_id=session_id,
            photo_count=photo_count,
            last_indexed=last_indexed
        )
        
    except Exception as e:
        logger.error(f"Error getting session status {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )



@router.post(
    "/search",
    response_model=dict,
    summary="Search for similar faces",
    description="Search for similar faces in a session by uploading a selfie"
)
@limiter.limit(SEARCH_RATE_LIMIT)
async def search_faces(
    request: Request,
    session_id: str = Form(..., alias="sessionId", description="Photo session UUID to search within"),
    file: UploadFile = File(..., description="Selfie photo to search for"),
    threshold: Optional[float] = Form(None, description="Similarity threshold (0.0-1.0)"),
    limit: int = Form(1000, description="Maximum number of results"),
    db: Session = Depends(get_db)
) -> dict:
    """
    Search for similar faces in a session.
    
    This endpoint allows clients to find photos by uploading a selfie.
    It extracts the face embedding from the selfie and searches for similar
    faces in the specified session.
    
    **Requirements**:
    - Session must have indexed photos (use GET /api/v1/search/status to check)
    - Selfie must contain a detectable face
    
    **Process**:
    1. Extract face embedding from selfie
    2. Normalize embedding for consistent similarity
    3. Search vector database for similar faces
    4. Return matches with similarity scores
    
    Args:
        session_id: Session UUID to search within
        file: Selfie image file
        threshold: Minimum similarity score (uses config default if not provided)
        limit: Maximum number of results to return
        db: Database session
        
    Returns:
        Dictionary with matches, query time, and statistics
        
    Raises:
        HTTPException 400: If file is invalid or no face detected
        HTTPException 404: If session has no indexed photos
        HTTPException 500: If search fails
    """
    import numpy as np
    from sqlalchemy import text
    from services.face_recognition import get_face_recognition_service
    from core.config import get_settings
    from models.face import FaceEmbedding
    
    # Log for PM2 monitoring
    print(f'=== SEARCH REQUEST START ===')
    print(f'Session ID: {session_id}')
    print(f'File: {file.filename if file else "None"}')
    print(f'Threshold: {threshold}')
    print(f'Limit: {limit}')
    print(f'===========================')
    
    # Validate inputs
    validate_session_id(session_id)
    validate_limit(limit)
    
    start_time = time.time()
    settings = get_settings()
    
    # Use config default if threshold not provided
    if threshold is None:
        threshold = settings.FACE_SIMILARITY_THRESHOLD
    else:
        validate_threshold(threshold)
    
    logger.info(f"Starting face search for session {session_id} with threshold {threshold}")
    
    # Validate and read file
    file_data = await validate_image_upload(file)
    
    # Extract embedding from uploaded selfie
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
        
        # Normalize the embedding
        embedding_norm = np.linalg.norm(query_embedding)
        if embedding_norm > 0:
            query_embedding = query_embedding / embedding_norm
            logger.info(f"Embedding normalized (original norm: {embedding_norm:.6f})")
        else:
            logger.warning("Zero embedding detected, cannot normalize")
        
    except RuntimeError as e:
        logger.error(f"Face recognition service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face recognition service error: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Invalid image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to process image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image: {str(e)}"
        )
    
    # Convert embedding to list for SQL query
    try:
        query_embedding_list = query_embedding.tolist()
        query_embedding_str = '[' + ','.join(map(str, query_embedding_list)) + ']'
        logger.info(f"Embedding converted to string format (length: {len(query_embedding_str)})")
    except Exception as e:
        logger.error(f"Error converting embedding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing embedding: {str(e)}"
        )
    
    # Check if session has any indexed photos
    try:
        embedding_count = db.query(FaceEmbedding).filter(
            FaceEmbedding.session_id == session_id
        ).count()
        
        if embedding_count == 0:
            logger.info(f"No indexed photos found for session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No indexed photos found for this session. Please index photos first."
            )
        
        logger.info(f"Session {session_id} has {embedding_count} indexed photos")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking indexed photos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    # Perform vector similarity search
    try:
        logger.info(f"Searching for similar faces in session {session_id} with threshold {threshold}")
        
        # Get matches above threshold using cosine similarity
        query = text("""
            SELECT 
                fe.photo_id,
                1 - (fe.embedding <=> :query_embedding) as similarity,
                fe.confidence
            FROM face_embeddings fe
            WHERE fe.session_id = :session_id
                AND (1 - (fe.embedding <=> :query_embedding)) >= :threshold
            ORDER BY similarity DESC
            LIMIT :limit
        """)
        
        result = db.execute(
            query,
            {
                "query_embedding": query_embedding_str,
                "session_id": session_id,
                "threshold": threshold,
                "limit": limit
            }
        )
        
        # Collect matches
        matches = []
        for row in result:
            photo_id = row[0]
            similarity = float(row[1])
            face_confidence = float(row[2])
            
            matches.append({
                "photo_id": photo_id,
                "similarity": similarity,
                "confidence": face_confidence
            })
        
        logger.info(f"Found {len(matches)} matches above threshold {threshold}")
        
        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Search completed: {len(matches)} matches in {query_time_ms:.2f}ms")
        
        return {
            "matches": matches,
            "query_time_ms": query_time_ms,
            "session_id": session_id,
            "total_matches": len(matches),
            "indexed_photos": embedding_count,
            "search_threshold": threshold
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Search failed for session {session_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check endpoint",
    description="Check service health including database and face recognition model"
)
async def health_check(
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    Health check endpoint for monitoring and load balancers.
    
    Checks:
    1. Database connectivity
    2. Face recognition model loaded
    3. Service uptime
    
    Returns:
        Dictionary with health status and component details
        
    Status codes:
        200: All components healthy
        503: One or more components unhealthy
    """
    from services.face_recognition import get_face_recognition_service
    from core.config import get_settings
    
    settings = get_settings()
    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "components": {}
    }
    
    # Calculate uptime
    if hasattr(request.app.state, 'startup_time'):
        uptime_seconds = int(time.time() - request.app.state.startup_time)
        health_status["uptime_seconds"] = uptime_seconds
    
    # Check database
    try:
        db.execute("SELECT 1")
        health_status["components"]["database"] = {
            "status": "healthy",
            "type": "postgresql+pgvector"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check face recognition model
    try:
        face_service = get_face_recognition_service()
        if face_service.initialized:
            health_status["components"]["face_recognition_model"] = {
                "status": "healthy",
                "model": "InsightFace"
            }
        else:
            health_status["status"] = "unhealthy"
            health_status["components"]["face_recognition_model"] = {
                "status": "unhealthy",
                "error": "Model not initialized"
            }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["face_recognition_model"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Return appropriate status code
    status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_status


@router.get(
    "/metrics",
    summary="Prometheus metrics endpoint",
    description="Expose Prometheus metrics for monitoring"
)
async def metrics_endpoint(db: Session = Depends(get_db)):
    """
    Prometheus metrics endpoint.
    
    Exposes metrics in Prometheus text format:
    - search_requests_total: Total number of search requests
    - search_duration_seconds: Search request duration histogram
    - index_requests_total: Total number of index requests
    - index_duration_seconds: Index request duration histogram
    - embeddings_total: Total number of embeddings in database
    - db_connections_active: Number of active database connections
    
    Returns:
        Plain text response in Prometheus format
    """
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
    from fastapi.responses import Response
    from models.face import FaceEmbedding
    from sqlalchemy import func
    
    # Define metrics (these will be registered once)
    try:
        search_requests = Counter(
            'search_requests_total',
            'Total number of search requests',
            ['status']
        )
        search_duration = Histogram(
            'search_duration_seconds',
            'Search request duration in seconds'
        )
        index_requests = Counter(
            'index_requests_total',
            'Total number of index requests',
            ['status']
        )
        index_duration = Histogram(
            'index_duration_seconds',
            'Index request duration in seconds'
        )
        embeddings_total = Gauge(
            'embeddings_total',
            'Total number of embeddings in database'
        )
        db_connections = Gauge(
            'db_connections_active',
            'Number of active database connections'
        )
    except Exception:
        # Metrics already registered, get them from registry
        pass
    
    # Update gauge metrics
    try:
        # Count total embeddings
        total_embeddings = db.query(func.count(FaceEmbedding.id)).scalar()
        embeddings_total.set(total_embeddings)
        
        # Get active connections (approximate)
        db_connections.set(1)  # Current connection
        
    except Exception as e:
        logger.error(f"Error updating metrics: {str(e)}")
    
    # Generate Prometheus format
    metrics_output = generate_latest(REGISTRY)
    
    return Response(
        content=metrics_output,
        media_type="text/plain; version=0.0.4"
    )
