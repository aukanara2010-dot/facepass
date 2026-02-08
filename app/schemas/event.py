from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class EventCreate(BaseModel):
    """Request schema for event creation"""
    event_uuid: Optional[str] = Field(
        None, 
        description="UUID from external system (optional, will be generated if not provided)"
    )
    name: str = Field(..., description="Event name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    event_date: Optional[datetime] = Field(None, description="Event date and time")


class EventResponse(BaseModel):
    """Response schema for event"""
    id: int = Field(..., description="Event ID")
    event_uuid: UUID = Field(..., description="Event UUID")
    name: str = Field(..., description="Event name")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    event_date: Optional[datetime] = Field(None, description="Event date and time")
    is_active: bool = Field(..., description="Whether event is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True  # Pydantic v2 (allows reading from SQLAlchemy models)
        # orm_mode = True  # Pydantic v1 (uncomment if using Pydantic v1)


class EventUpdate(BaseModel):
    """Request schema for event update"""
    name: Optional[str] = Field(None, description="Event name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    event_date: Optional[datetime] = Field(None, description="Event date and time")
    is_active: Optional[bool] = Field(None, description="Whether event is active")


class EventPublicResponse(BaseModel):
    """Public response schema for event (no sensitive data)"""
    event_uuid: UUID = Field(..., description="Event UUID")
    name: str = Field(..., description="Event name")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    event_date: Optional[datetime] = Field(None, description="Event date and time")
    preview_image_url: Optional[str] = Field(None, description="Preview image URL")
    
    class Config:
        from_attributes = True
