"""
Database connection and session management module.

This module provides SQLAlchemy engine and session management for both
main database and vector database, along with dependency injection functions
for FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from core.config import get_settings

settings = get_settings()

# Main Database Engine
main_engine = create_engine(
    settings.main_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

MainSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=main_engine)

# Vector Database Engine
vector_engine = create_engine(
    settings.vector_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

VectorSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=vector_engine)

# External Pixora Database Engine (Read-only)
pixora_engine = create_engine(
    settings.MAIN_APP_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

PixoraSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pixora_engine)

# Base class for models
Base = declarative_base()


def get_main_db() -> Generator[Session, None, None]:
    """
    Dependency for main database session.
    
    This function is designed to be used as a FastAPI dependency to provide
    database sessions to route handlers. It ensures proper session cleanup
    after each request.
    
    Yields:
        Session: SQLAlchemy session for main database
        
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_main_db)):
            return db.query(User).all()
    """
    db = MainSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_vector_db() -> Generator[Session, None, None]:
    """
    Dependency for vector database session.
    
    This function is designed to be used as a FastAPI dependency to provide
    database sessions to route handlers. It ensures proper session cleanup
    after each request.
    
    Yields:
        Session: SQLAlchemy session for vector database
        
    Example:
        @app.get("/embeddings")
        def get_embeddings(db: Session = Depends(get_vector_db)):
            return db.query(FaceEmbedding).all()
    """
    db = VectorSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pixora_db() -> Generator[Session, None, None]:
    """
    Dependency for external Pixora database session (READ-ONLY).
    
    This function provides read-only access to the external Pixora database
    for session validation and FacePass status checking.
    
    Yields:
        Session: SQLAlchemy session for Pixora database
        
    Example:
        @app.get("/session/{session_id}")
        def validate_session(session_id: str, pixora_db: Session = Depends(get_pixora_db)):
            return pixora_db.query(PhotoSession).filter_by(id=session_id).first()
    """
    db = PixoraSessionLocal()
    try:
        yield db
    finally:
        db.close()
