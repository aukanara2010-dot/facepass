#!/usr/bin/env python3
"""
Comprehensive test for the auto-indexing flow in FacePass.

This script tests the complete workflow:
1. Session validation
2. Auto-indexing when no embeddings exist
3. Face search functionality
4. S3 integration
5. Database operations

Run this script to verify the auto-indexing implementation works end-to-end.
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.api.deps import get_db, get_vector_db_session
from core.database import get_pixora_db
from services.photo_indexing import get_photo_indexing_service
from services.face_recognition import get_face_recognition_service
from models.face import FaceEmbedding
from models.photo_session import PhotoSession
from core.s3 import list_s3_objects, S3Error
from core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


class AutoIndexingFlowTester:
    """Test class for auto-indexing flow."""
    
    def __init__(self):
        """Initialize the tester."""
        self.indexing_service = get_photo_indexing_service()
        self.face_service = get_face_recognition_service()
        
    def test_database_connections(self) -> bool:
        """Test all database connections."""
        logger.info("=== Testing Database Connections ===")
        
        try:
            # Test vector database
            logger.info("Testing vector database connection...")
            vector_db = next(get_vector_db_session())
            from sqlalchemy import text
            count = vector_db.execute(text("SELECT COUNT(*) FROM face_embeddings")).scalar()
            logger.info(f"✓ Vector DB connected. Current embeddings: {count}")
            vector_db.close()
            
            # Test Pixora database
            logger.info("Testing Pixora database connection...")
            pixora_db = next(get_pixora_db())
            count = pixora_db.execute(text("SELECT COUNT(*) FROM photo_sessions")).scalar()
            logger.info(f"✓ Pixora DB connected. Total sessions: {count}")
            pixora_db.close()
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Database connection failed: {str(e)}")
            return False
    
    def test_face_recognition_service(self) -> bool:
        """Test face recognition service initialization."""
        logger.info("=== Testing Face Recognition Service ===")
        
        try:
            if not self.face_service.initialized:
                logger.error("✗ Face recognition service not initialized")
                return False
            
            logger.info("✓ Face recognition service initialized")
            return True
            
        except Exception as e:
            logger.error(f"✗ Face recognition service error: {str(e)}")
            return False
    
    def test_s3_connection(self) -> bool:
        """Test S3 connection and basic operations."""
        logger.info("=== Testing S3 Connection ===")
        
        try:
            # Test listing objects with a common prefix
            test_prefix = "sessions/"
            logger.info(f"Testing S3 list with prefix: {test_prefix}")
            
            objects = list_s3_objects(test_prefix)
            logger.info(f"✓ S3 connected. Found {len(objects)} objects with prefix '{test_prefix}'")
            
            # Show first few objects as examples
            if objects:
                logger.info("Sample objects:")
                for obj in objects[:5]:
                    logger.info(f"  - {obj}")
                if len(objects) > 5:
                    logger.info(f"  ... and {len(objects) - 5} more")
            
            return True
            
        except S3Error as e:
            logger.error(f"✗ S3 connection failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected S3 error: {str(e)}")
            return False
    
    def find_test_session(self) -> str:
        """Find a valid session for testing."""
        logger.info("=== Finding Test Session ===")
        
        try:
            pixora_db = next(get_pixora_db())
            
            # Look for sessions with FacePass enabled
            sessions = pixora_db.query(PhotoSession).filter(
                PhotoSession.facepass_enabled == True
            ).limit(5).all()
            
            if not sessions:
                logger.warning("No sessions with FacePass enabled found")
                pixora_db.close()
                return None
            
            # Check which sessions have photos in S3
            for session in sessions:
                try:
                    s3_prefix = f"sessions/{session.id}/previews/"
                    objects = list_s3_objects(s3_prefix)
                    
                    if objects:
                        logger.info(f"✓ Found test session: {session.id} ({session.name})")
                        logger.info(f"  - S3 prefix: {s3_prefix}")
                        logger.info(f"  - Photos in S3: {len(objects)}")
                        pixora_db.close()
                        return str(session.id)
                        
                except S3Error:
                    continue
            
            logger.warning("No sessions with photos in S3 found")
            pixora_db.close()
            return None
            
        except Exception as e:
            logger.error(f"Error finding test session: {str(e)}")
            return None
    
    def test_session_scanning(self, session_id: str) -> bool:
        """Test S3 scanning for a specific session."""
        logger.info(f"=== Testing Session Scanning: {session_id} ===")
        
        try:
            # Test S3 scanning
            photo_keys = self.indexing_service.scan_session_photos(session_id)
            logger.info(f"✓ Found {len(photo_keys)} photos in session")
            
            # Show sample photos
            if photo_keys:
                logger.info("Sample photos:")
                for key in photo_keys[:3]:
                    photo_id = self.indexing_service.extract_photo_id_from_s3_key(key)
                    logger.info(f"  - {key} → photo_id: {photo_id}")
                if len(photo_keys) > 3:
                    logger.info(f"  ... and {len(photo_keys) - 3} more")
            
            return len(photo_keys) > 0
            
        except Exception as e:
            logger.error(f"✗ Session scanning failed: {str(e)}")
            return False
    
    def test_indexing_status_check(self, session_id: str) -> tuple:
        """Test checking indexing status."""
        logger.info(f"=== Testing Indexing Status Check: {session_id} ===")
        
        try:
            vector_db = next(get_vector_db_session())
            is_indexed, count = self.indexing_service.check_session_indexed(session_id, vector_db)
            
            logger.info(f"✓ Session indexed: {is_indexed}")
            logger.info(f"✓ Embedding count: {count}")
            
            vector_db.close()
            return is_indexed, count
            
        except Exception as e:
            logger.error(f"✗ Indexing status check failed: {str(e)}")
            return False, 0
    
    def test_auto_indexing(self, session_id: str) -> bool:
        """Test the auto-indexing functionality."""
        logger.info(f"=== Testing Auto-Indexing: {session_id} ===")
        
        try:
            vector_db = next(get_vector_db_session())
            
            # Clear existing embeddings for clean test
            logger.info("Clearing existing embeddings for clean test...")
            vector_db.query(FaceEmbedding).filter(
                FaceEmbedding.session_id == session_id
            ).delete()
            vector_db.commit()
            
            # Verify no embeddings exist
            is_indexed, count = self.indexing_service.check_session_indexed(session_id, vector_db)
            if is_indexed:
                logger.error(f"✗ Session still shows as indexed after clearing (count: {count})")
                vector_db.close()
                return False
            
            logger.info("✓ Session cleared, starting indexing...")
            
            # Perform indexing (limit to 5 photos for testing)
            processed_count, success_count, error_messages = self.indexing_service.index_session_photos(
                session_id, vector_db, max_photos=5
            )
            
            logger.info(f"✓ Indexing completed:")
            logger.info(f"  - Processed: {processed_count} photos")
            logger.info(f"  - Successful: {success_count} photos")
            logger.info(f"  - Errors: {len(error_messages)}")
            
            if error_messages:
                logger.warning("Indexing errors:")
                for error in error_messages[:3]:
                    logger.warning(f"  - {error}")
            
            # Verify indexing worked
            is_indexed, final_count = self.indexing_service.check_session_indexed(session_id, vector_db)
            logger.info(f"✓ Final status - Indexed: {is_indexed}, Count: {final_count}")
            
            vector_db.close()
            return success_count > 0
            
        except Exception as e:
            logger.error(f"✗ Auto-indexing test failed: {str(e)}")
            return False
    
    def test_search_simulation(self, session_id: str) -> bool:
        """Test the search functionality with a dummy embedding."""
        logger.info(f"=== Testing Search Simulation: {session_id} ===")
        
        try:
            vector_db = next(get_vector_db_session())
            
            # Check if we have embeddings to search
            embedding_count = vector_db.query(FaceEmbedding).filter(
                FaceEmbedding.session_id == session_id
            ).count()
            
            if embedding_count == 0:
                logger.warning("No embeddings found for search test")
                vector_db.close()
                return False
            
            logger.info(f"Found {embedding_count} embeddings for search")
            
            # Create a dummy query embedding (512 dimensions)
            import numpy as np
            dummy_embedding = np.random.rand(512).astype(np.float32)
            
            # Simulate the search query from the API
            from sqlalchemy import text
            
            query_embedding_list = dummy_embedding.tolist()
            query_embedding_str = '[' + ','.join(map(str, query_embedding_list)) + ']'
            
            query = text("""
                SELECT 
                    fe.photo_id,
                    1 - (fe.embedding <=> :query_embedding) as similarity
                FROM face_embeddings fe
                WHERE fe.session_id = :session_id
                    AND (1 - (fe.embedding <=> :query_embedding)) >= :threshold
                ORDER BY fe.embedding <=> :query_embedding ASC
                LIMIT :limit
            """)
            
            result = vector_db.execute(
                query,
                {
                    "query_embedding": query_embedding_str,
                    "session_id": session_id,
                    "threshold": 0.1,  # Low threshold for testing
                    "limit": 10
                }
            )
            
            matches = list(result)
            logger.info(f"✓ Search completed: {len(matches)} matches found")
            
            # Show sample matches
            for i, match in enumerate(matches[:3]):
                photo_id = match[0]
                similarity = match[1]
                logger.info(f"  Match {i+1}: photo_id={photo_id}, similarity={similarity:.3f}")
            
            vector_db.close()
            return len(matches) > 0
            
        except Exception as e:
            logger.error(f"✗ Search simulation failed: {str(e)}")
            return False
    
    def run_complete_test(self) -> bool:
        """Run the complete auto-indexing flow test."""
        logger.info("🚀 Starting Complete Auto-Indexing Flow Test")
        logger.info("=" * 60)
        
        # Test 1: Database connections
        if not self.test_database_connections():
            logger.error("❌ Database connection test failed")
            return False
        
        # Test 2: Face recognition service
        if not self.test_face_recognition_service():
            logger.error("❌ Face recognition service test failed")
            return False
        
        # Test 3: S3 connection
        if not self.test_s3_connection():
            logger.error("❌ S3 connection test failed")
            return False
        
        # Test 4: Find test session
        test_session_id = self.find_test_session()
        if not test_session_id:
            logger.error("❌ No suitable test session found")
            return False
        
        # Test 5: Session scanning
        if not self.test_session_scanning(test_session_id):
            logger.error("❌ Session scanning test failed")
            return False
        
        # Test 6: Indexing status check
        is_indexed, count = self.test_indexing_status_check(test_session_id)
        logger.info(f"Initial indexing status: {is_indexed} ({count} embeddings)")
        
        # Test 7: Auto-indexing
        if not self.test_auto_indexing(test_session_id):
            logger.error("❌ Auto-indexing test failed")
            return False
        
        # Test 8: Search simulation
        if not self.test_search_simulation(test_session_id):
            logger.error("❌ Search simulation test failed")
            return False
        
        logger.info("=" * 60)
        logger.info("🎉 All tests passed! Auto-indexing flow is working correctly.")
        logger.info(f"✅ Test session: {test_session_id}")
        
        return True


def main():
    """Main test function."""
    try:
        tester = AutoIndexingFlowTester()
        success = tester.run_complete_test()
        
        if success:
            logger.info("\n✅ AUTO-INDEXING FLOW TEST: PASSED")
            sys.exit(0)
        else:
            logger.error("\n❌ AUTO-INDEXING FLOW TEST: FAILED")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()