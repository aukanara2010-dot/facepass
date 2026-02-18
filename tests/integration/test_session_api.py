#!/usr/bin/env python3
"""
Test session API endpoints with real data.
"""

import sys
import os
import asyncio
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from core.database import PixoraSessionLocal
from models.photo_session import PhotoSession


def get_test_session_id():
    """Get a real session ID for testing."""
    db = PixoraSessionLocal()
    session = db.query(PhotoSession).first()
    db.close()
    return str(session.id) if session else None


def test_session_endpoints():
    """Test session API endpoints."""
    print("🌐 Testing session API endpoints...")
    
    try:
        # Import app after setting up path
        from app.main import app
        
        client = TestClient(app)
        
        # Get real session ID
        session_id = get_test_session_id()
        if not session_id:
            print("❌ No sessions found in database")
            return False
        
        print(f"🎯 Testing with session ID: {session_id}")
        
        # Test 1: Validate session endpoint
        print("\n1️⃣ Testing session validation...")
        response = client.get(f"/api/v1/sessions/validate/{session_id}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Valid: {data.get('valid')}")
            if data.get('session'):
                print(f"   Session Name: {data['session']['name']}")
                print(f"   FacePass Enabled: {data['session']['facepass_enabled']}")
            if data.get('error'):
                print(f"   Error: {data['error']}")
        else:
            print(f"   Error: {response.text}")
        
        # Test 2: Get session details
        print("\n2️⃣ Testing session details...")
        response = client.get(f"/api/v1/sessions/{session_id}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Name: {data.get('name')}")
            print(f"   Studio ID: {data.get('studio_id')}")
            print(f"   FacePass: {data.get('facepass_enabled')}")
        else:
            print(f"   Error: {response.text}")
        
        # Test 3: FacePass status
        print("\n3️⃣ Testing FacePass status...")
        response = client.get(f"/api/v1/sessions/{session_id}/facepass-status")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   FacePass Enabled: {data.get('facepass_enabled')}")
            print(f"   Is Active: {data.get('is_active')}")
            print(f"   Session Name: {data.get('session_name')}")
        else:
            print(f"   Error: {response.text}")
        
        # Test 4: Interface page
        print("\n4️⃣ Testing interface page...")
        response = client.get(f"/api/v1/sessions/{session_id}/interface")
        print(f"   Status: {response.status_code}")
        print(f"   Content Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            content = response.text
            if "FacePass" in content and session_id in content:
                print("   ✅ HTML content looks correct")
            else:
                print("   ⚠️  HTML content might be incomplete")
        else:
            print(f"   Error: {response.text}")
        
        # Test 5: Non-existent session
        print("\n5️⃣ Testing with non-existent session...")
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/sessions/validate/{fake_uuid}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Valid: {data.get('valid')}")
            print(f"   Error: {data.get('error')}")
        
        print("\n🎉 API endpoint tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_session_endpoints()
    sys.exit(0 if success else 1)