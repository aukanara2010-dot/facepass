import sys
import logging
from sqlalchemy import text, MetaData
from core.database import vector_engine, main_engine, Base
from core.config import get_settings

# Import models to register them with Base
from models.event import Event
from models.face import Face, FaceEmbedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def init_vector_extension():
    """Initialize pgvector extension in vector database"""
    try:
        with vector_engine.connect() as conn:
            # Set search path to public schema
            conn.execute(text("SET search_path TO public"))
            # Create vector extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("✓ pgvector extension initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize pgvector extension: {e}")
        sys.exit(1)


def create_main_tables():
    """
    Create tables for main database (Event, Face)
    
    These tables do NOT use vector type, so they're safe to create
    in the main database.
    """
    try:
        # Create metadata for main database tables only
        main_metadata = MetaData()
        
        # Register only Event and Face tables (not FaceEmbedding)
        Event.__table__.to_metadata(main_metadata)
        Face.__table__.to_metadata(main_metadata)
        
        # Create tables in main database
        main_metadata.create_all(bind=main_engine)
        logger.info("✓ Main database tables created successfully (events, faces)")
    except Exception as e:
        logger.error(f"✗ Failed to create main database tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def create_vector_tables():
    """
    Create tables for vector database (FaceEmbedding)
    
    This table uses the vector type, so it MUST be created
    in the vector database where pgvector extension is installed.
    """
    try:
        with vector_engine.connect() as conn:
            # Set search path to public schema
            conn.execute(text("SET search_path TO public"))
            conn.commit()
        
        # Create metadata for vector database tables only
        vector_metadata = MetaData()
        
        # Register only FaceEmbedding table
        FaceEmbedding.__table__.to_metadata(vector_metadata)
        
        # Create tables in vector database
        vector_metadata.create_all(bind=vector_engine)
        logger.info("✓ Vector database tables created successfully (face_embeddings)")
    except Exception as e:
        logger.error(f"✗ Failed to create vector database tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def verify_configuration():
    """Verify database configuration"""
    logger.info("Database configuration:")
    logger.info(f"  Main DB URL: {settings.main_database_url}")
    logger.info(f"  Vector DB URL: {settings.vector_database_url}")
    
    # Check that databases are different
    if settings.main_database_url == settings.vector_database_url:
        logger.warning("⚠ Main and Vector databases are the same!")
        logger.warning("  This is OK for development, but not recommended for production")


def main():
    logger.info("=" * 60)
    logger.info("FacePass Database Initialization")
    logger.info("=" * 60)
    
    verify_configuration()
    
    logger.info("\nStep 1: Initialize pgvector extension...")
    init_vector_extension()
    
    logger.info("\nStep 2: Create main database tables...")
    create_main_tables()
    
    logger.info("\nStep 3: Create vector database tables...")
    create_vector_tables()
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Database initialization completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
