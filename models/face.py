from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from core.database import Base
from core.config import get_settings
import uuid

settings = get_settings()


class Face(Base):
    """
    Face model for main database
    
    Represents a photo taken at an event by a photographer.
    Updated to support both events and sessions.
    """
    __tablename__ = "faces"
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=True, index=True)  # Reference to Event.id (optional for sessions)
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Reference to PhotoSession.id
    photo_id = Column(String(255), nullable=True, index=True)  # Reference to Photo.id (can be UUID or timestamp-hash)
    image_url = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # No relationship - we handle joins manually at the service layer


class FaceEmbedding(Base):
    """
    Face embedding model for vector database
    
    Stores the 512-dimensional face embedding vector for similarity search.
    Updated to support both events and sessions.
    """
    __tablename__ = "face_embeddings"
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, index=True)
    face_id = Column(Integer, nullable=True, index=True)  # Reference to Face.id (optional)
    photo_id = Column(String(255), nullable=True, index=True)  # Direct reference to Photo.id (can be UUID or timestamp-hash)
    event_id = Column(Integer, nullable=True, index=True)  # For events (legacy)
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # For sessions (new)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    confidence = Column(Float, nullable=True)  # Face detection confidence
    created_at = Column(DateTime(timezone=True), server_default=func.now())
