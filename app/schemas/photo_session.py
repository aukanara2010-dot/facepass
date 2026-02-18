"""
Photo Session schemas for API request/response validation.

This module defines Pydantic schemas for photo session data validation
and serialization in API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class PhotoSessionBase(BaseModel):
    """Base schema for photo session data."""
    
    name: str = Field(..., description="Session name")
    studio_id: UUID = Field(..., description="Studio identifier")
    facepass_enabled: bool = Field(default=False, description="FacePass enabled status")


class PhotoSessionResponse(PhotoSessionBase):
    """Schema for photo session API responses."""
    
    id: UUID = Field(..., description="Session identifier")
    description: Optional[str] = Field(None, description="Session description")
    photographer_id: UUID = Field(..., description="Photographer identifier")
    status: str = Field(..., description="Session status")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    service_package_id: Optional[UUID] = Field(None, description="Service package identifier")
    
    class Config:
        from_attributes = True


class SessionValidationResponse(BaseModel):
    """Schema for session validation response."""
    
    valid: bool = Field(..., description="Whether session is valid for FacePass")
    session: Optional[PhotoSessionResponse] = Field(None, description="Session data if valid")
    error: Optional[str] = Field(None, description="Error message if invalid")
    
    class Config:
        from_attributes = True