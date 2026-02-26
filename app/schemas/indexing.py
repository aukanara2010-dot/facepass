"""
Pydantic schemas for indexing endpoints.

This module defines request and response schemas for photo indexing operations
in the isolated FacePass microservice.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class IndexPhotoRequest(BaseModel):
    """Request schema for single photo indexing."""
    photo_id: str = Field(..., description="Unique photo identifier (UUID or filename)")
    session_id: str = Field(..., description="Photo session UUID")
    s3_key: Optional[str] = Field(None, description="S3 key for the photo (if already uploaded)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "photo_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "s3_key": "sessions/7c9e6679-7425-40de-944b-e07fc1f90ae7/photo1.jpg"
            }
        }


class IndexPhotoResponse(BaseModel):
    """Response schema for single photo indexing."""
    indexed: bool = Field(..., description="Whether indexing was successful")
    photo_id: str = Field(..., description="Photo identifier")
    confidence: Optional[float] = Field(None, description="Face detection confidence (0.0-1.0)")
    faces_detected: int = Field(..., description="Number of faces detected in the photo")
    error: Optional[str] = Field(None, description="Error message if indexing failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "indexed": True,
                "photo_id": "550e8400-e29b-41d4-a716-446655440000",
                "confidence": 0.95,
                "faces_detected": 1,
                "error": None
            }
        }


class BatchIndexItem(BaseModel):
    """Single item in batch indexing request."""
    photo_id: str = Field(..., description="Unique photo identifier")
    s3_key: str = Field(..., description="S3 key for the photo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "photo_id": "550e8400-e29b-41d4-a716-446655440000",
                "s3_key": "sessions/session-uuid/photo1.jpg"
            }
        }


class BatchIndexRequest(BaseModel):
    """Request schema for batch photo indexing."""
    session_id: str = Field(..., description="Photo session UUID")
    photos: List[BatchIndexItem] = Field(..., description="List of photos to index")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "photos": [
                    {
                        "photo_id": "550e8400-e29b-41d4-a716-446655440000",
                        "s3_key": "sessions/session-uuid/photo1.jpg"
                    },
                    {
                        "photo_id": "6fa459ea-ee8a-3ca4-894e-db77e160355e",
                        "s3_key": "sessions/session-uuid/photo2.jpg"
                    }
                ]
            }
        }


class BatchIndexResponse(BaseModel):
    """Response schema for batch photo indexing."""
    indexed: int = Field(..., description="Number of photos successfully indexed")
    failed: int = Field(..., description="Number of photos that failed to index")
    total: int = Field(..., description="Total number of photos processed")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "indexed": 98,
                "failed": 2,
                "total": 100,
                "errors": [
                    "photo3.jpg: No face detected",
                    "photo5.jpg: Failed to download from S3"
                ]
            }
        }


class DeleteSessionResponse(BaseModel):
    """Response schema for session deletion."""
    deleted: bool = Field(..., description="Whether deletion was successful")
    session_id: str = Field(..., description="Session UUID")
    embeddings_removed: int = Field(..., description="Number of embeddings removed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "deleted": True,
                "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "embeddings_removed": 150
            }
        }


class SessionStatusResponse(BaseModel):
    """Response schema for session indexing status."""
    indexed: bool = Field(..., description="Whether session has indexed photos")
    session_id: str = Field(..., description="Session UUID")
    photo_count: int = Field(..., description="Number of indexed photos")
    last_indexed: Optional[str] = Field(None, description="Timestamp of last indexing (ISO format)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "indexed": True,
                "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "photo_count": 150,
                "last_indexed": "2024-02-26T10:30:00Z"
            }
        }
