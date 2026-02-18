#!/usr/bin/env python3
"""
Diagnose 500 errors in FacePass search-session endpoint.

This script helps identify common issues that cause 500 errors
without proper logging.
"""

import sys
import os
import logging
import traceback

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test all required imports."""
    print("📦 Testing imports...")
    
    imports_to_test = [
        ("FastAPI", "from fastapi import FastAPI"),
        ("SQLAlchemy", "from sqlalchemy import create_engine"),
        ("pgvector", "from pgvector.sqlalchemy import Vector"),
        ("InsightFace", "import insightface"),
        ("PIL", "from PIL import Image"),
        ("numpy", "import numpy as np"),
        ("boto3", "import boto3"),
    ]
    
    failed_imports = []
    
    for name, import_statement in imports_to_test:
        try:
            exec(import_statement)
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name}: {str(e)}")
            failed_imports.append(name)
        except Exception as e:
            print(f"   ⚠️  {name}: {str(e)}")
    
    if failed_imports:
        print(f"\n❌ Failed imports: {', '.join(failed_imports)}")
        print("💡 Fix: pip install missing packages")
        return False
    
    print("✅ All imports successful")
    return True


def test_configuration():
    """Test configuration loading."""
    print("\n⚙️  Testing configuration...")
    
    try:
        from core.config import get_settings
        settings = get_settings()
        
        # Check critical settings
        critical_settings = [
            "MAIN_APP_DATABASE_URL",
            "S3_ENDPOINT",
            "S3_ACCESS_KEY",
            "S3_SECRET_KEY",
            "S3_BUCKET",
            "EMBEDDING_DIMENSION"
        ]
        
        missing_settings = []
        for setting in critical_settings:
            value = getattr(settings, setting, None)
            if not value:
                missing_settings.append(setting)
            else:
                print(f"   ✅ {setting}: {'*' * min(len(str(value)), 10)}")
        
        if missing_settings:
            print(f"\n❌ Missing settings: {', '.join(missing_settings)}")
            return False
        
        print("✅ Configuration loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {str(e)}")
        traceback.print_exc()
        return False


def test_database_connections():
    """Test all database connections."""
    print("\n🗄️  Testing database connections...")
    
    try:
        from core.database import get_db, get_vector_db_session, get_pixora_db
        
        # Test main database
        try:
            db = next(get_db())
            result = db.execute("SELECT 1").fetchone()
            db.close()
            print("   ✅ Main database")
        except Exception as e:
            print(f"   ❌ Main database: {str(e)}")
            return False
        
        # Test vector database
        try:
            vector_db = next(get_vector_db_session())
            result = vector_db.execute("SELECT 1").fetchone()
            vector_db.close()
            print("   ✅ Vector database")
        except Exception as e:
            print(f"   ❌ Vector database: {str(e)}")
            return False
        
        # Test Pixora database
        try:
            pixora_db = next(get_pixora_db())
            result = pixora_db.execute("SELECT 1").fetchone()
            pixora_db.close()
            print("   ✅ Pixora database")
        except Exception as e:
            print(f"   ❌ Pixora database: {str(e)}")
            return False
        
        print("✅ All database connections working")
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_table_structure():
    """Test database table structure."""
    print("\n📋 Testing table structure...")
    
    try:
        from core.database import get_vector_db_session, get_pixora_db
        from sqlalchemy import text
        
        # Test vector database tables
        vector_db = next(get_vector_db_session())
        try:
            # Check if face_embeddings table exists
            table_check = vector_db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'face_embeddings'
                );
            """)).fetchone()
            
            if not table_check[0]:
                print("   ❌ face_embeddings table does not exist")
                print("   💡 Fix: Run python scripts/init_db.py")
                return False
            
            # Check table structure
            columns = vector_db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'face_embeddings'
                ORDER BY ordinal_position;
            """)).fetchall()
            
            required_columns = ['id', 'session_id', 'photo_id', 'embedding']
            existing_columns = [col[0] for col in columns]
            
            missing_columns = []
            for req_col in required_columns:
                if req_col not in existing_columns:
                    missing_columns.append(req_col)
            
            if missing_columns:
                print(f"   ❌ Missing columns in face_embeddings: {missing_columns}")
                print("   💡 Fix: Update table schema or recreate with scripts/init_db.py")
                return False
            
            print("   ✅ face_embeddings table structure correct")
            
        finally:
            vector_db.close()
        
        # Test Pixora database tables
        pixora_db = next(get_pixora_db())
        try:
            # Check if photo_sessions table exists
            table_check = pixora_db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'photo_sessions'
                );
            """)).fetchone()
            
            if not table_check[0]:
                print("   ❌ photo_sessions table does not exist in Pixora DB")
                return False
            
            print("   ✅ photo_sessions table exists")
            
        finally:
            pixora_db.close()
        
        print("✅ Table structure verification passed")
        return True
        
    except Exception as e:
        print(f"❌ Table structure test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_face_recognition():
    """Test face recognition service."""
    print("\n🤖 Testing face recognition service...")
    
    try:
        from services.face_recognition import get_face_recognition_service
        
        face_service = get_face_recognition_service()
        
        if not face_service.initialized:
            print("   ❌ Face recognition service not initialized")
            print("   💡 Fix: pip install insightface onnxruntime")
            return False
        
        print("   ✅ Face recognition service initialized")
        
        # Test with dummy image
        try:
            from PIL import Image
            import io
            
            # Create test image
            img = Image.new('RGB', (200, 200), color='white')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            test_data = img_bytes.getvalue()
            
            # Test embedding extraction (will likely find no faces, but tests the pipeline)
            embeddings = face_service.get_embeddings(test_data)
            print(f"   ✅ Face processing pipeline works (found {len(embeddings)} faces)")
            
        except Exception as e:
            print(f"   ⚠️  Face processing test: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Face recognition test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_s3_service():
    """Test S3 service."""
    print("\n☁️  Testing S3 service...")
    
    try:
        from core.s3 import get_s3_client
        
        client = get_s3_client()
        print("   ✅ S3 client created")
        
        # Test basic connectivity
        try:
            response = client.list_buckets()
            print(f"   ✅ S3 connectivity works ({len(response.get('Buckets', []))} buckets)")
        except Exception as e:
            print(f"   ❌ S3 connectivity failed: {str(e)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ S3 service test failed: {str(e)}")
        traceback.print_exc()
        return False


def simulate_search_request():
    """Simulate a search request to find potential issues."""
    print("\n🔍 Simulating search request...")
    
    try:
        # Test session validation
        from core.database import get_pixora_db
        from models.photo_session import PhotoSession
        
        print("1️⃣ Testing session validation...")
        pixora_db = next(get_pixora_db())
        try:
            session = pixora_db.query(PhotoSession).first()
            if session:
                print(f"   ✅ Found test session: {session.id}")
                
                if session.is_facepass_active():
                    print("   ✅ FacePass is active")
                else:
                    print("   ⚠️  FacePass is not active for this session")
            else:
                print("   ❌ No sessions found in Pixora database")
                return False
        finally:
            pixora_db.close()
        
        # Test vector database query
        print("2️⃣ Testing vector database query...")
        from core.database import get_vector_db_session
        from sqlalchemy import text
        
        vector_db = next(get_vector_db_session())
        try:
            # Test basic vector query structure
            test_query = text("""
                SELECT COUNT(*) 
                FROM face_embeddings 
                WHERE session_id IS NOT NULL
            """)
            
            result = vector_db.execute(test_query).fetchone()
            print(f"   ✅ Vector database query works ({result[0]} embeddings with session_id)")
            
            if result[0] == 0:
                print("   ⚠️  No face embeddings found with session_id")
                print("   💡 You may need to populate the face_embeddings table")
        
        finally:
            vector_db.close()
        
        print("✅ Search request simulation completed")
        return True
        
    except Exception as e:
        print(f"❌ Search request simulation failed: {str(e)}")
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests."""
    print("🔍 FacePass 500 Error Diagnostic Tool\n")
    
    tests = [
        ("Package Imports", test_imports),
        ("Configuration", test_configuration),
        ("Database Connections", test_database_connections),
        ("Table Structure", test_table_structure),
        ("Face Recognition", test_face_recognition),
        ("S3 Service", test_s3_service),
        ("Search Simulation", simulate_search_request),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if not result:
                print(f"\n⚠️  {test_name} failed - this may be causing 500 errors")
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary and recommendations
    print(f"\n{'='*60}")
    print("DIAGNOSTIC SUMMARY")
    print('='*60)
    
    passed = 0
    failed_tests = []
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
        else:
            failed_tests.append(test_name)
    
    print(f"\nPassed: {passed}/{len(results)}")
    
    if failed_tests:
        print(f"\n🚨 LIKELY CAUSES OF 500 ERRORS:")
        
        if "Package Imports" in failed_tests:
            print("• Missing Python packages - run: pip install -r requirements.txt")
        
        if "Configuration" in failed_tests:
            print("• Invalid .env configuration - check database URLs and S3 settings")
        
        if "Database Connections" in failed_tests:
            print("• Database connection issues - verify credentials and server availability")
        
        if "Table Structure" in failed_tests:
            print("• Missing or incorrect database tables - run: python scripts/init_db.py")
        
        if "Face Recognition" in failed_tests:
            print("• InsightFace not properly installed - run: pip install insightface onnxruntime")
        
        if "S3 Service" in failed_tests:
            print("• S3 configuration issues - check credentials and endpoint")
        
        print(f"\n🔧 RECOMMENDED FIXES:")
        print("1. Fix the failed tests above")
        print("2. Enable detailed logging in your FastAPI app")
        print("3. Check server logs for more specific error messages")
        print("4. Test with a simple endpoint first")
        
    else:
        print("\n🎉 All diagnostic tests passed!")
        print("If you're still getting 500 errors, check:")
        print("1. Server logs for detailed error messages")
        print("2. Network connectivity between services")
        print("3. Resource limits (memory, disk space)")


if __name__ == "__main__":
    main()