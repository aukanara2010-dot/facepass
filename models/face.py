"""
Face Embedding model for vector database.

This module contains only the FaceEmbedding model for storing face vectors
in the PostgreSQL database with pgvector extension.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from core.database import Base
from core.config import get_settings

settings = get_settings()


class FaceEmbedding(Base):
    """
    Face embedding model for vector database.
    
    Stores the 512-dimensional face embedding vector for similarity search.
    Simplified to work only with photo_id and session_id (no face_id or event_id).
    """
    __tablename__ = "face_embeddings"
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(String(255), nullable=False, index=True)  # Photo identifier (UUID or timestamp-hash)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Session identifier
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)  # 512-dimensional vector
    confidence = Column(Float, nullable=False)  # Face detection confidence
    created_at = Column(DateTime(timezone=True), server_default=func.now())
