"""
API Dependencies
Dependency injection functions for FastAPI endpoints
"""
from typing import Generator
from sqlalchemy.orm import Session
from core.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session
    
    Yields:
        Session: SQLAlchemy session for vector database
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
