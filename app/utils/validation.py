"""
Input validation utilities for FacePass.

This module provides validation functions for file uploads, parameters,
and other user inputs to ensure security and data integrity.
"""

import logging
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_DIMENSION = 4096
ALLOWED_CONTENT_TYPES = [
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp',
    'image/heic',
    'image/heif'
]


async def validate_image_upload(file: UploadFile) -> bytes:
    """
    Validate uploaded image file.
    
    Checks:
    1. Content type is image
    2. File size is within limits
    3. Image format is valid (can be opened by PIL)
    4. Image dimensions are within limits
    
    Args:
        file: Uploaded file from FastAPI
        
    Returns:
        bytes: Validated image data
        
    Raises:
        HTTPException 400: If validation fails
    """
    # Check content type
    if not file.content_type or file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Invalid content type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
    
    # Read file data
    try:
        file_data = await file.read()
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Check file size
    file_size = len(file_data)
    if file_size > MAX_FILE_SIZE:
        logger.warning(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024):.1f}MB"
        )
    
    if file_size == 0:
        logger.warning("Empty file uploaded")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file"
        )
    
    # Validate image format and dimensions
    try:
        image = Image.open(io.BytesIO(file_data))
        
        # Verify image (checks for corrupted files)
        image.verify()
        
        # Re-open for dimension check (verify() closes the file)
        image = Image.open(io.BytesIO(file_data))
        width, height = image.size
        
        # Check dimensions
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            logger.warning(f"Image dimensions too large: {width}x{height}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image dimensions too large. Maximum: {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}"
            )
        
        if width < 10 or height < 10:
            logger.warning(f"Image dimensions too small: {width}x{height}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image dimensions too small (minimum: 10x10)"
            )
        
        logger.info(f"Image validated: {width}x{height}, {file_size} bytes, {image.format}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invalid image format: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format: {str(e)}"
        )
    
    return file_data


def validate_session_id(session_id: str) -> None:
    """
    Validate session ID format.
    
    Args:
        session_id: Session ID to validate
        
    Raises:
        HTTPException 400: If validation fails
    """
    if not session_id or len(session_id) < 1 or len(session_id) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id (must be 1-255 characters)"
        )
    
    # Check for SQL injection patterns
    dangerous_patterns = ["'", '"', ';', '--', '/*', '*/', 'DROP', 'DELETE', 'UPDATE', 'INSERT']
    session_id_upper = session_id.upper()
    
    for pattern in dangerous_patterns:
        if pattern in session_id_upper:
            logger.warning(f"Potential SQL injection attempt in session_id: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session_id format"
            )


def validate_photo_id(photo_id: str) -> None:
    """
    Validate photo ID format.
    
    Args:
        photo_id: Photo ID to validate
        
    Raises:
        HTTPException 400: If validation fails
    """
    if not photo_id or len(photo_id) < 1 or len(photo_id) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo_id (must be 1-255 characters)"
        )
    
    # Check for SQL injection patterns
    dangerous_patterns = ["'", '"', ';', '--', '/*', '*/', 'DROP', 'DELETE', 'UPDATE', 'INSERT']
    photo_id_upper = photo_id.upper()
    
    for pattern in dangerous_patterns:
        if pattern in photo_id_upper:
            logger.warning(f"Potential SQL injection attempt in photo_id: {photo_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid photo_id format"
            )


def validate_threshold(threshold: float) -> None:
    """
    Validate similarity threshold.
    
    Args:
        threshold: Threshold value to validate
        
    Raises:
        HTTPException 400: If validation fails
    """
    if not 0.0 <= threshold <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Threshold must be between 0.0 and 1.0"
        )


def validate_limit(limit: int) -> None:
    """
    Validate result limit.
    
    Args:
        limit: Limit value to validate
        
    Raises:
        HTTPException 400: If validation fails
    """
    if not 1 <= limit <= 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 1000"
        )
