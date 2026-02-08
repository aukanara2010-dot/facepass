from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from core.database import Base
from core.config import get_settings

settings = get_settings()


class Face(Base):
    """
    Face model for main database
    
    Represents a photo taken at an event by a photographer.
    event_id references Event.id (no FK - manual relationship at service layer).
    """
    __tablename__ = "faces"
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)  # Reference to Event.id (no FK)
    image_url = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # No relationship - we handle joins manually at the service layer


class FaceEmbedding(Base):
    """
    Face embedding model for vector database
    
    Stores the 512-dimensional face embedding vector for similarity search.
    Note: This model is stored in a separate database (vector DB),
    so we don't use ForeignKey to Face table. The face_id is just
    an integer reference to the Face.id in the main database.
    """
    __tablename__ = "face_embeddings"
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, index=True)
    face_id = Column(Integer, nullable=False, index=True)  # Reference to Face.id (no FK across databases)
    event_id = Column(Integer, nullable=False, index=True)  # Denormalized for fast filtering
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
