from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class FaceUploadResponse(BaseModel):
    """Response schema for face upload"""
    face_id: int = Field(..., description="ID of the uploaded face")
    image_url: str = Field(..., description="URL of the uploaded image in S3")
    confidence: float = Field(..., description="Face detection confidence score", ge=0.0, le=1.0)
    task_id: str = Field(..., description="Celery task ID for async processing")


class FaceSearchResult(BaseModel):
    """Individual face search result"""
    face_id: int = Field(..., description="ID of the matched face")
    event_id: int = Field(..., description="ID of the event")
    similarity: float = Field(..., description="Similarity score", ge=0.0, le=1.0)
    image_url: str = Field(..., description="URL of the matched face image")


class FaceSearchResponse(BaseModel):
    """Response schema for face search"""
    results: list[FaceSearchResult] = Field(..., description="List of matching faces")
    query_time_ms: float = Field(..., description="Query execution time in milliseconds", ge=0.0)
    task_id: Optional[str] = Field(None, description="Celery task ID if async")


class S3SyncRequest(BaseModel):
    """Request schema for S3 sync"""
    event_uuid: str = Field(..., description="Event UUID")
    s3_prefix: str = Field(..., description="S3 prefix to sync (e.g., 'events/1/previews/')")


class S3SyncResponse(BaseModel):
    """Response schema for S3 sync"""
    task_id: str = Field(..., description="Celery task ID for async processing")
    event_id: int = Field(..., description="Event ID")
    s3_prefix: str = Field(..., description="S3 prefix being synced")
    message: str = Field(..., description="Status message")
