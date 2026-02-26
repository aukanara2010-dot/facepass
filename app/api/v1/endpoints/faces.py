"""
Face recognition search endpoints.

This module provides the core face search functionality for the isolated
FacePass microservice. It works only with pre-indexed embeddings and does
not interact with external databases.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import logging
import numpy as np

from core.database import get_db
from models.face import FaceEmbedding
from services.face_recognition import get_face_recognition_service
from core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search-session", response_model=dict)
async def search_faces_in_session(
    session_id: str = Form(..., description="Photo session UUID to search within"),
    file: UploadFile = File(..., description="Selfie photo from client"),
    threshold: float = Form(None, description="Similarity threshold (0.0-1.0), uses config default if not provided"),
    limit: int = Form(1000, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Search for similar faces within a photo session.
    
    This endpoint allows clients to find their photos from a specific photo session
    by uploading a selfie. Works only with pre-indexed photos.
    
    **IMPORTANT**: This endpoint only searches pre-indexed embeddings. Photos must be
    indexed first using the /api/v1/index endpoints.
    
    Workflow:
    1. Extracts embedding from uploaded selfie using InsightFace
    2. Searches for similar faces in vector database filtered by session
    3. Returns matching photo_ids with similarity scores
    
    Args:
        session_id: The photo session UUID to search within
        file: Selfie image from client
        threshold: Minimum similarity score (default from config)
        limit: Maximum number of results
    
    Returns:
        Dictionary with matches array containing photo_ids and similarity scores
    """
    start_time = time.time()
    settings = get_settings()
    
    # Use config default if threshold not provided
    if threshold is None:
        threshold = settings.FACE_SIMILARITY_THRESHOLD
    
    logger.info(f"Starting face search for session {session_id} with threshold {threshold}")
    
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
        
        # Normalize the embedding for consistent similarity calculation
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
    
    # Check if session has any indexed photos
    try:
        embedding_count = db.query(FaceEmbedding).filter(
            FaceEmbedding.session_id == session_id
        ).count()
        
        if embedding_count == 0:
            logger.info(f"No indexed photos found for session {session_id}")
            return {
                "matches": [],
                "query_time_ms": (time.time() - start_time) * 1000,
                "message": "No indexed photos found for this session. Please index photos first.",
                "indexed_photos": 0
            }
        
        logger.info(f"Session {session_id} has {embedding_count} indexed photos")
        
    except Exception as e:
        logger.error(f"Error checking indexed photos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Perform vector similarity search with session_id filter
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
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
