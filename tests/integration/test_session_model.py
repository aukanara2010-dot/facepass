#!/usr/bin/env python3
"""
Test PhotoSession model with real data from Pixora database.
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import PixoraSessionLocal
from models.photo_session import PhotoSession


def test_session_model():
    """Test PhotoSession model with real data."""
    print("🧪 Testing PhotoSession model with real data...")
    
    try:
        db = PixoraSessionLocal()
        
        # Get all sessions
        sessions = db.query(PhotoSession).all()
        print(f"✅ Found {len(sessions)} sessions in database")
        
        for session in sessions:
            print(f"\n📋 Session Details:")
            print(f"   ID: {session.id}")
            print(f"   Name: {session.name}")
            print(f"   Description: {session.description}")
            print(f"   Studio ID: {session.studio_id}")
            print(f"   Photographer ID: {session.photographer_id}")
            print(f"   Status: {session.status}")
            print(f"   FacePass Enabled: {session.facepass_enabled}")
            print(f"   FacePass Active: {session.is_facepass_active()}")
            print(f"   Created: {session.created_at}")
            print(f"   Updated: {session.updated_at}")
            
            if session.scheduled_at:
                print(f"   Scheduled: {session.scheduled_at}")
            if session.completed_at:
                print(f"   Completed: {session.completed_at}")
            if session.service_package_id:
                print(f"   Service Package: {session.service_package_id}")
            if session.settings:
                print(f"   Settings: {session.settings}")
        
        # Test filtering by FacePass enabled
        facepass_sessions = db.query(PhotoSession).filter(
            PhotoSession.facepass_enabled == True
        ).all()
        
        print(f"\n🎯 Sessions with FacePass enabled: {len(facepass_sessions)}")
        
        if facepass_sessions:
            test_session = facepass_sessions[0]
            print(f"\n🔍 Testing with session: {test_session.id}")
            
            # Test finding by ID
            found_session = db.query(PhotoSession).filter(
                PhotoSession.id == test_session.id
            ).first()
            
            if found_session:
                print(f"✅ Successfully found session by ID")
                print(f"   Name: {found_session.name}")
                print(f"   FacePass Active: {found_session.is_facepass_active()}")
            else:
                print("❌ Could not find session by ID")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_session_model()
    sys.exit(0 if success else 1)