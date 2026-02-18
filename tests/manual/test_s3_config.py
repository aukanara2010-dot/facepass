#!/usr/bin/env python3
"""
Test S3 configuration and connectivity.
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import get_settings
from core.s3 import get_s3_client, S3ConnectionError, S3UploadError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_s3_configuration():
    """Test S3 configuration parameters."""
    print("🔧 Testing S3 Configuration")
    
    try:
        settings = get_settings()
        
        # Check required S3 settings
        s3_config = {
            "S3_ENDPOINT": settings.S3_ENDPOINT,
            "S3_ACCESS_KEY": settings.S3_ACCESS_KEY,
            "S3_SECRET_KEY": settings.S3_SECRET_KEY,
            "S3_BUCKET": settings.S3_BUCKET,
            "S3_REGION": settings.S3_REGION,
        }
        
        print("📋 S3 Configuration:")
        for key, value in s3_config.items():
            if "KEY" in key:
                # Mask sensitive keys
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                print(f"   {key}: {masked_value}")
            else:
                print(f"   {key}: {value}")
        
        # Check for missing values
        missing_configs = []
        for key, value in s3_config.items():
            if not value or value.strip() == "":
                missing_configs.append(key)
        
        if missing_configs:
            print(f"❌ Missing S3 configuration: {', '.join(missing_configs)}")
            return False
        
        print("✅ All S3 configuration parameters are set")
        return True
        
    except Exception as e:
        print(f"❌ Error reading S3 configuration: {str(e)}")
        return False


def test_s3_client_creation():
    """Test S3 client creation."""
    print("\n🔌 Testing S3 Client Creation")
    
    try:
        client = get_s3_client()
        print("✅ S3 client created successfully")
        return client
        
    except S3ConnectionError as e:
        print(f"❌ S3 connection error: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error creating S3 client: {str(e)}")
        return None


def test_s3_connectivity(client):
    """Test S3 connectivity and permissions."""
    print("\n📡 Testing S3 Connectivity")
    
    if not client:
        print("❌ No S3 client available")
        return False
    
    try:
        settings = get_settings()
        
        # Test 1: List buckets (basic connectivity)
        print("1️⃣ Testing bucket listing...")
        try:
            response = client.list_buckets()
            buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
            print(f"   ✅ Connected to S3. Found {len(buckets)} buckets")
            
            if settings.S3_BUCKET in buckets:
                print(f"   ✅ Target bucket '{settings.S3_BUCKET}' exists")
            else:
                print(f"   ⚠️  Target bucket '{settings.S3_BUCKET}' not found in: {buckets}")
                
        except Exception as e:
            print(f"   ❌ Failed to list buckets: {str(e)}")
            return False
        
        # Test 2: Check bucket permissions
        print("2️⃣ Testing bucket permissions...")
        try:
            # Try to list objects in the bucket
            response = client.list_objects_v2(
                Bucket=settings.S3_BUCKET,
                MaxKeys=1
            )
            print(f"   ✅ Can read from bucket '{settings.S3_BUCKET}'")
            
        except Exception as e:
            print(f"   ❌ Cannot read from bucket: {str(e)}")
            return False
        
        # Test 3: Test upload (small test file)
        print("3️⃣ Testing upload permissions...")
        try:
            test_key = "facepass-test/connectivity-test.txt"
            test_content = b"FacePass connectivity test"
            
            client.put_object(
                Bucket=settings.S3_BUCKET,
                Key=test_key,
                Body=test_content,
                ContentType='text/plain'
            )
            print(f"   ✅ Can upload to bucket '{settings.S3_BUCKET}'")
            
            # Clean up test file
            try:
                client.delete_object(
                    Bucket=settings.S3_BUCKET,
                    Key=test_key
                )
                print(f"   ✅ Test file cleaned up")
            except:
                print(f"   ⚠️  Could not clean up test file: {test_key}")
                
        except Exception as e:
            print(f"   ❌ Cannot upload to bucket: {str(e)}")
            return False
        
        print("✅ All S3 connectivity tests passed")
        return True
        
    except Exception as e:
        print(f"❌ S3 connectivity test failed: {str(e)}")
        return False


def test_face_recognition_service():
    """Test face recognition service initialization."""
    print("\n🤖 Testing Face Recognition Service")
    
    try:
        from services.face_recognition import get_face_recognition_service
        
        print("1️⃣ Initializing face recognition service...")
        face_service = get_face_recognition_service()
        
        if face_service.initialized:
            print("   ✅ Face recognition service initialized successfully")
            
            # Test with a small dummy image
            print("2️⃣ Testing with dummy image...")
            try:
                # Create a small test image (1x1 pixel PNG)
                import io
                from PIL import Image
                
                # Create a tiny test image
                img = Image.new('RGB', (100, 100), color='red')
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='JPEG')
                test_image_data = img_bytes.getvalue()
                
                # Try to extract embedding (will likely fail due to no face, but tests the pipeline)
                embeddings = face_service.get_embeddings(test_image_data)
                print(f"   ✅ Face service processing works (found {len(embeddings)} faces)")
                
            except Exception as e:
                print(f"   ⚠️  Face processing test: {str(e)} (this is expected for test image)")
            
            return True
        else:
            print("   ❌ Face recognition service failed to initialize")
            return False
            
    except ImportError as e:
        print(f"   ❌ Cannot import face recognition service: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ Face recognition service error: {str(e)}")
        return False


def test_database_connections():
    """Test database connections."""
    print("\n🗄️  Testing Database Connections")
    
    try:
        from app.api.deps import get_db, get_vector_db_session
        from core.database import get_pixora_db
        from sqlalchemy import text
        
        # Test main database
        print("1️⃣ Testing main database connection...")
        try:
            db = next(get_db())
            # Simple test query
            result = db.execute(text("SELECT 1 as test")).fetchone()
            db.close()
            print(f"   ✅ Main database connected: {result[0]}")
        except Exception as e:
            print(f"   ❌ Main database connection failed: {str(e)}")
            return False
        
        # Test vector database
        print("2️⃣ Testing vector database connection...")
        try:
            vector_db = next(get_vector_db_session())
            # Test pgvector extension
            result = vector_db.execute(text("SELECT 1 as test")).fetchone()
            vector_db.close()
            print(f"   ✅ Vector database connected: {result[0]}")
        except Exception as e:
            print(f"   ❌ Vector database connection failed: {str(e)}")
            return False
        
        # Test Pixora database
        print("3️⃣ Testing Pixora database connection...")
        try:
            pixora_db = next(get_pixora_db())
            result = pixora_db.execute(text("SELECT 1 as test")).fetchone()
            pixora_db.close()
            print(f"   ✅ Pixora database connected: {result[0]}")
        except Exception as e:
            print(f"   ❌ Pixora database connection failed: {str(e)}")
            return False
        
        print("✅ All database connections successful")
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {str(e)}")
        return False


def main():
    """Run all configuration tests."""
    print("🚀 Starting FacePass Configuration Tests\n")
    
    tests = [
        ("S3 Configuration", test_s3_configuration),
        ("S3 Client Creation", test_s3_client_creation),
        ("Face Recognition Service", test_face_recognition_service),
        ("Database Connections", test_database_connections),
    ]
    
    results = []
    s3_client = None
    
    for test_name, test_func in tests:
        print(f"{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            if test_name == "S3 Client Creation":
                result = test_func()
                s3_client = result if result else None
                results.append((test_name, bool(result)))
            else:
                result = test_func()
                results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Additional S3 connectivity test if client was created
    if s3_client:
        print(f"{'='*60}")
        print("Running: S3 Connectivity")
        print('='*60)
        try:
            result = test_s3_connectivity(s3_client)
            results.append(("S3 Connectivity", result))
        except Exception as e:
            print(f"❌ S3 connectivity test crashed: {str(e)}")
            results.append(("S3 Connectivity", False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("\n🎉 All configuration tests passed!")
        print("✅ FacePass is properly configured and ready to use")
    else:
        print("\n⚠️  Some configuration tests failed.")
        print("\n🔧 Common fixes:")
        print("1. Check .env file for missing or incorrect values")
        print("2. Verify S3 credentials and bucket permissions")
        print("3. Ensure InsightFace is properly installed")
        print("4. Check database connections and credentials")
        print("5. Run: pip install insightface onnxruntime")


if __name__ == "__main__":
    main()