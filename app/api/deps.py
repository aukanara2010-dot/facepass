"""
API Dependencies
Dependency injection functions for FastAPI endpoints
"""
from typing import Generator
from sqlalchemy.orm import Session
from core.database import MainSessionLocal, VectorSessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting main database session
    
    Yields:
        Session: SQLAlchemy session for main database
    """
    db = MainSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_vector_db_session() -> Generator[Session, None, None]:
    """
    Dependency for getting vector database session
    
    Yields:
        Session: SQLAlchemy session for vector database
    """
    db = VectorSessionLocal()
    try:
        yield db
    finally:
        db.close()
