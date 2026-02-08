from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from core.database import Base


class Event(Base):
    """
    Event model for main database
    
    Represents a photography event (wedding, conference, party, etc.)
    where photos are taken and later searched by attendees.
    """
    __tablename__ = "events"
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, index=True)
    event_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    event_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
