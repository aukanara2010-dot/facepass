#!/usr/bin/env python3
"""
Initialize FacePass database tables.

This script creates the necessary tables for FacePass in both
the main database and vector database.
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from core.config import get_settings
from core.database import Base, main_engine, vector_engine
from models.face import Face, FaceEmbedding
from models.event import Event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_main_database():
    """Initialize main database tables."""
    print("🗄️  Initializing main database...")
    
    try:
        # Create tables in main database
        Base.metadata.create_all(bind=main_engine, tables=[Face.__table__, Event.__table__])
        
        # Test connection
        with main_engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print(f"✅ Main database connected: {result[0]}")
            
            # Check if faces table exists
            faces_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'faces'
                );
            """)).fetchone()
            
            # Check if events table exists
            events_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'events'
                );
            """)).fetchone()
            
            if faces_check[0]:
                print("✅ faces table created/exists")
            else:
                print("❌ faces table was not created")
                return False
                
            if events_check[0]:
                print("✅ events table created/exists")
            else:
                print("❌ events table was not created")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Main database initialization failed: {str(e)}")
        return False


def init_vector_database():
    """Initialize vector database tables."""
    print("\n🔍 Initializing vector database...")
    
    try:
        # First, ensure pgvector extension is installed
        with vector_engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                print("✅ pgvector extension enabled")
            except Exception as e:
                print(f"⚠️  Could not enable pgvector extension: {str(e)}")
                print("   Make sure pgvector is installed on your PostgreSQL server")
        
        # Create tables in vector database
        Base.metadata.create_all(bind=vector_engine, tables=[FaceEmbedding.__table__])
        
        # Test connection and table
        with vector_engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print(f"✅ Vector database connected: {result[0]}")
            
            # Check if face_embeddings table exists
            table_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'face_embeddings'
                );
            """)).fetchone()
            
            if table_check[0]:
                print("✅ face_embeddings table created/exists")
                
                # Check if vector column exists with correct dimension
                try:
                    settings = get_settings()
                    vector_check = conn.execute(text("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'face_embeddings' 
                            AND column_name = 'embedding'
                    """)).fetchone()
                    
                    if vector_check:
                        print(f"✅ embedding column exists: {vector_check[1]}")
                    else:
                        print("❌ embedding column not found")
                        return False
                        
                except Exception as e:
                    print(f"⚠️  Could not verify vector column: {str(e)}")
            else:
                print("❌ face_embeddings table was not created")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Vector database initialization failed: {str(e)}")
        return False


def create_indexes():
    """Create performance indexes."""
    print("\n📊 Creating performance indexes...")
    
    try:
        # Indexes for main database
        with main_engine.connect() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_faces_session_id ON faces(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_faces_photo_id ON faces(photo_id)",
                "CREATE INDEX IF NOT EXISTS idx_faces_created_at ON faces(created_at)",
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    print(f"✅ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    print(f"⚠️  Index creation warning: {str(e)}")
            
            conn.commit()
        
        # Indexes for vector database
        with vector_engine.connect() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_face_embeddings_session_id ON face_embeddings(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_face_embeddings_photo_id ON face_embeddings(photo_id)",
                "CREATE INDEX IF NOT EXISTS idx_face_embeddings_created_at ON face_embeddings(created_at)",
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    print(f"✅ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    print(f"⚠️  Index creation warning: {str(e)}")
            
            # Create vector similarity index (HNSW)
            try:
                hnsw_index = """
                CREATE INDEX IF NOT EXISTS idx_face_embeddings_embedding_hnsw 
                ON face_embeddings 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
                """
                conn.execute(text(hnsw_index))
                print("✅ Created HNSW vector similarity index")
            except Exception as e:
                print(f"⚠️  HNSW index creation failed: {str(e)}")
                print("   Trying IVFFlat index as fallback...")
                
                try:
                    ivfflat_index = """
                    CREATE INDEX IF NOT EXISTS idx_face_embeddings_embedding_ivfflat 
                    ON face_embeddings 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                    """
                    conn.execute(text(ivfflat_index))
                    print("✅ Created IVFFlat vector similarity index")
                except Exception as e2:
                    print(f"❌ Vector index creation failed: {str(e2)}")
                    print("   Vector similarity search may be slow without indexes")
            
            conn.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ Index creation failed: {str(e)}")
        return False


def verify_setup():
    """Verify the database setup."""
    print("\n🔍 Verifying database setup...")
    
    try:
        settings = get_settings()
        
        # Check main database
        with main_engine.connect() as conn:
            # Count faces table
            count = conn.execute(text("SELECT COUNT(*) FROM faces")).fetchone()
            print(f"✅ faces table: {count[0]} records")
        
        # Check vector database
        with vector_engine.connect() as conn:
            # Count face_embeddings table
            count = conn.execute(text("SELECT COUNT(*) FROM face_embeddings")).fetchone()
            print(f"✅ face_embeddings table: {count[0]} records")
            
            # Test vector operations
            try:
                # Create a test vector
                test_vector = "[" + ",".join(["0.1"] * settings.EMBEDDING_DIMENSION) + "]"
                
                # Test vector similarity query (should work even with empty table)
                test_query = text("""
                    SELECT COUNT(*) 
                    FROM face_embeddings 
                    WHERE (1 - (embedding <=> :test_vector)) > 0.5
                """)
                
                result = conn.execute(test_query, {"test_vector": test_vector}).fetchone()
                print(f"✅ Vector similarity operations working: {result[0]} matches")
                
            except Exception as e:
                print(f"⚠️  Vector operations test failed: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False


def main():
    """Main initialization function."""
    print("🚀 Starting FacePass Database Initialization\n")
    
    try:
        settings = get_settings()
        print(f"📋 Configuration:")
        print(f"   Main DB: {settings.main_database_url}")
        print(f"   Vector DB: {settings.vector_database_url}")
        print(f"   Embedding Dimension: {settings.EMBEDDING_DIMENSION}")
        
    except Exception as e:
        print(f"❌ Configuration error: {str(e)}")
        return False
    
    steps = [
        ("Main Database", init_main_database),
        ("Vector Database", init_vector_database),
        ("Performance Indexes", create_indexes),
        ("Setup Verification", verify_setup),
    ]
    
    results = []
    
    for step_name, step_func in steps:
        print(f"\n{'='*50}")
        print(f"Step: {step_name}")
        print('='*50)
        
        try:
            result = step_func()
            results.append((step_name, result))
            
            if not result:
                print(f"❌ {step_name} failed. Stopping initialization.")
                break
                
        except Exception as e:
            print(f"❌ {step_name} crashed: {str(e)}")
            results.append((step_name, False))
            break
    
    # Summary
    print(f"\n{'='*50}")
    print("INITIALIZATION SUMMARY")
    print('='*50)
    
    passed = 0
    for step_name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{status} - {step_name}")
        if result:
            passed += 1
    
    print(f"\nCompleted: {passed}/{len(results)} steps")
    
    if passed == len(results):
        print("\n🎉 Database initialization completed successfully!")
        print("\n📋 Next steps:")
        print("1. Run configuration tests: python test_s3_config.py")
        print("2. Start the FastAPI server: uvicorn app.main:app --reload")
        print("3. Test the interface: http://localhost:8000/session/{session_id}")
        return True
    else:
        print("\n❌ Database initialization failed.")
        print("\n🔧 Troubleshooting:")
        print("1. Check database connections in .env")
        print("2. Ensure PostgreSQL is running")
        print("3. Install pgvector extension: CREATE EXTENSION vector;")
        print("4. Check database permissions")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)