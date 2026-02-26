"""
Database connection and session management module.

This module provides SQLAlchemy engine and session management for the
vector database, along with dependency injection functions for FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from core.config import get_settings

settings = get_settings()

# Database Engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for database session.
    
    This function is designed to be used as a FastAPI dependency to provide
    database sessions to route handlers. It ensures proper session cleanup
    after each request.
    
    Yields:
        Session: SQLAlchemy session for vector database
        
    Example:
        @app.get("/embeddings")
        def get_embeddings(db: Session = Depends(get_db)):
            return db.query(FaceEmbedding).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
