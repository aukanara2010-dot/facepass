from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid as uuid_lib

from app.api.deps import get_db
from models.event import Event
from models.face import Face
from app.schemas.event import EventCreate, EventResponse, EventUpdate, EventPublicResponse

router = APIRouter()


@router.post("/", response_model=EventResponse, status_code=201)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """
    Create a new event
    
    Photographers create events before uploading photos.
    event_uuid can be provided from external system or auto-generated.
    """
    # Parse or generate UUID
    if event.event_uuid:
        try:
            event_uuid = uuid_lib.UUID(event.event_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")
        
        # Check if UUID already exists
        existing = db.query(Event).filter(Event.event_uuid == event_uuid).first()
        if existing:
            raise HTTPException(status_code=400, detail="Event with this UUID already exists")
    else:
        event_uuid = uuid_lib.uuid4()
    
    # Create new event
    db_event = Event(
        event_uuid=event_uuid,
        name=event.name,
        description=event.description,
        location=event.location,
        event_date=event.event_date,
        is_active=True
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return db_event


@router.get("/", response_model=List[EventResponse])
async def list_events(
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all events
    
    Query params:
    - skip: Number of records to skip
    - limit: Maximum number of records to return
    - active_only: Filter only active events
    """
    query = db.query(Event)
    if active_only:
        query = query.filter(Event.is_active == True)
    
    events = query.offset(skip).limit(limit).all()
    return events


@router.get("/uuid/{event_uuid}", response_model=EventResponse)
async def get_event_by_uuid(event_uuid: str, db: Session = Depends(get_db)):
    """
    Get event by UUID
    
    This is the main lookup method for attendees searching their photos.
    """
    try:
        uuid_obj = uuid_lib.UUID(event_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    event = db.query(Event).filter(Event.event_uuid == uuid_obj).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """
    Get event by ID
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_update: EventUpdate,
    db: Session = Depends(get_db)
):
    """
    Update event details
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update only provided fields
    update_data = event_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    """
    Delete event
    
    Note: This will NOT cascade delete faces. 
    Use face_service.delete_event_faces() first if needed.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(event)
    db.commit()
    return None


@router.get("/public/{event_uuid}", response_model=EventPublicResponse)
async def get_public_event(event_uuid: str, db: Session = Depends(get_db)):
    """
    Get public event information by UUID (no authentication required)
    
    This endpoint is used by attendees to view event details before searching photos.
    Returns basic event information and a preview image if available.
    
    Args:
        event_uuid: The UUID of the event
        
    Returns:
        Public event information including name, description, date, and preview image
    """
    try:
        uuid_obj = uuid_lib.UUID(event_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Get event
    event = db.query(Event).filter(Event.event_uuid == uuid_obj).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if event is active
    if not event.is_active:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get first face image as preview (if any)
    preview_face = db.query(Face).filter(Face.event_id == event.id).first()
    preview_image_url = preview_face.image_url if preview_face else None
    
    return EventPublicResponse(
        event_uuid=event.event_uuid,
        name=event.name,
        description=event.description,
        location=event.location,
        event_date=event.event_date,
        preview_image_url=preview_image_url
    )
