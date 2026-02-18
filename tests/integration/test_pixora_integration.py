"""
Test script for Pixora database integration.

This script tests the connection to the external Pixora database
and validates session endpoints functionality.
"""

import asyncio
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import get_pixora_db, PixoraSessionLocal
from models.photo_session import PhotoSession
from core.config import get_settings


async def test_pixora_connection():
    """Test connection to external Pixora database."""
    print("🔍 Testing Pixora database connection...")
    
    try:
        settings = get_settings()
        print(f"📡 Connecting to: {settings.MAIN_APP_DATABASE_URL}")
        
        # Test basic connection
        db = PixoraSessionLocal()
        
        # Test simple query
        result = db.execute(text("SELECT 1 as test")).fetchone()
        print(f"✅ Basic connection test: {result}")
        
        # Test photo_sessions table existence
        table_check = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'photo_sessions'
            );
        """)).fetchone()
        
        if table_check[0]:
            print("✅ photo_sessions table exists")
            
            # Get table structure
            columns = db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'photo_sessions'
                ORDER BY ordinal_position;
            """)).fetchall()
            
            print("📋 Table structure:")
            for col in columns:
                print(f"   - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
            
            # Count records
            count = db.execute(text("SELECT COUNT(*) FROM photo_sessions")).fetchone()
            print(f"📊 Total sessions: {count[0]}")
            
            # Sample records
            if count[0] > 0:
                samples = db.execute(text("""
                    SELECT id, name, facepass_enabled, studio_id 
                    FROM photo_sessions 
                    LIMIT 5
                """)).fetchall()
                
                print("📝 Sample records:")
                for sample in samples:
                    print(f"   - ID: {sample[0]}, Name: {sample[1]}, FacePass: {sample[2]}, Studio: {sample[3]}")
        else:
            print("❌ photo_sessions table does not exist")
            
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False


async def test_session_model():
    """Test PhotoSession model functionality."""
    print("\n🧪 Testing PhotoSession model...")
    
    try:
        db = PixoraSessionLocal()
        
        # Try to query using the model
        sessions = db.query(PhotoSession).limit(3).all()
        
        print(f"✅ Found {len(sessions)} sessions using model")
        
        for session in sessions:
            print(f"   - {session}")
            print(f"     FacePass Active: {session.is_facepass_active()}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {str(e)}")
        return False


async def test_session_endpoints():
    """Test session validation endpoints."""
    print("\n🌐 Testing session endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Test with a non-existent session
        response = client.get("/api/v1/sessions/validate/99999")
        print(f"📡 Validate non-existent session: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Valid: {data.get('valid')}, Error: {data.get('error')}")
        
        # Get a real session ID for testing
        db = PixoraSessionLocal()
        first_session = db.query(PhotoSession).first()
        
        if first_session:
            session_id = first_session.id
            print(f"🎯 Testing with real session ID: {session_id}")
            
            # Test validation endpoint
            response = client.get(f"/api/v1/sessions/validate/{session_id}")
            print(f"📡 Validate real session: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Valid: {data.get('valid')}")
                if data.get('session'):
                    print(f"   Session: {data['session']['name']}")
            
            # Test session details endpoint
            response = client.get(f"/api/v1/sessions/{session_id}")
            print(f"📡 Get session details: {response.status_code}")
            
            # Test FacePass status endpoint
            response = client.get(f"/api/v1/sessions/{session_id}/facepass-status")
            print(f"📡 Get FacePass status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   FacePass enabled: {data.get('facepass_enabled')}")
            
            # Test interface endpoint
            response = client.get(f"/api/v1/sessions/{session_id}/interface")
            print(f"📡 Get interface page: {response.status_code}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Endpoint test failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting Pixora Integration Tests\n")
    
    tests = [
        ("Database Connection", test_pixora_connection),
        ("Session Model", test_session_model),
        ("API Endpoints", test_session_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("🎉 All tests passed! Pixora integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    asyncio.run(main())