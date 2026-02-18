#!/usr/bin/env python3
"""
Test FacePass interactive interface functionality.
"""

import sys
import os
import requests
from urllib.parse import urljoin

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import PixoraSessionLocal
from models.photo_session import PhotoSession


def get_test_session_id():
    """Get a real session ID for testing."""
    db = PixoraSessionLocal()
    session = db.query(PhotoSession).first()
    db.close()
    return str(session.id) if session else None


def test_interface_accessibility():
    """Test that the interface is accessible via HTTP."""
    print("🌐 Testing FacePass interface accessibility...")
    
    session_id = get_test_session_id()
    if not session_id:
        print("❌ No test session available")
        return False
    
    base_url = "http://localhost:8000"
    interface_url = f"{base_url}/api/v1/sessions/{session_id}/interface"
    
    try:
        print(f"📡 Testing URL: {interface_url}")
        
        # Test interface endpoint
        response = requests.get(interface_url, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key elements
            checks = [
                ("FacePass title", "FacePass" in content),
                ("Session title element", "session-title" in content),
                ("Camera button", "camera-btn" in content),
                ("Upload button", "upload-btn" in content),
                ("Results section", "results-section" in content),
                ("JavaScript file", "face-search.js" in content),
                ("Tailwind CSS", "tailwindcss.com" in content)
            ]
            
            print("   ✅ Interface loaded successfully")
            print("   📋 Content checks:")
            
            all_passed = True
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"      {status} {check_name}")
                if not passed:
                    all_passed = False
            
            return all_passed
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {str(e)}")
        return False


def test_static_files():
    """Test that static files are accessible."""
    print("\n📁 Testing static file accessibility...")
    
    base_url = "http://localhost:8000"
    static_files = [
        "/static/js/face-search.js"
    ]
    
    all_passed = True
    
    for file_path in static_files:
        url = f"{base_url}{file_path}"
        
        try:
            print(f"📡 Testing: {url}")
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"   ✅ Accessible (Size: {len(response.content)} bytes)")
                
                # Basic content validation for JS file
                if file_path.endswith('.js'):
                    content = response.text
                    js_checks = [
                        ("Class definition", "class FacePassGallery" in content),
                        ("Camera functionality", "getUserMedia" in content),
                        ("Search functionality", "searchFaces" in content),
                        ("Modal functionality", "showModal" in content)
                    ]
                    
                    for check_name, passed in js_checks:
                        status = "✅" if passed else "❌"
                        print(f"      {status} {check_name}")
                        if not passed:
                            all_passed = False
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                all_passed = False
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")
            all_passed = False
    
    return all_passed


def test_api_endpoints():
    """Test API endpoints used by the interface."""
    print("\n🔌 Testing API endpoints...")
    
    session_id = get_test_session_id()
    if not session_id:
        print("❌ No test session available")
        return False
    
    base_url = "http://localhost:8000"
    endpoints = [
        f"/api/v1/sessions/validate/{session_id}",
        f"/api/v1/sessions/{session_id}",
        f"/api/v1/sessions/{session_id}/facepass-status"
    ]
    
    all_passed = True
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        
        try:
            print(f"📡 Testing: {endpoint}")
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success")
                
                # Basic validation based on endpoint
                if "validate" in endpoint:
                    if "valid" in data:
                        print(f"      Valid: {data['valid']}")
                    else:
                        print("      ⚠️  Missing 'valid' field")
                        all_passed = False
                        
                elif "facepass-status" in endpoint:
                    if "facepass_enabled" in data:
                        print(f"      FacePass: {data['facepass_enabled']}")
                    else:
                        print("      ⚠️  Missing 'facepass_enabled' field")
                        all_passed = False
                        
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                all_passed = False
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")
            all_passed = False
        except ValueError as e:
            print(f"   ❌ JSON parsing failed: {str(e)}")
            all_passed = False
    
    return all_passed


def main():
    """Run all interface tests."""
    print("🚀 Starting FacePass Interface Tests\n")
    
    tests = [
        ("Interface Accessibility", test_interface_accessibility),
        ("Static Files", test_static_files),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
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
        print("🎉 All tests passed! FacePass interface is ready!")
        print("\n📋 Next steps:")
        print("1. Start the FastAPI server: uvicorn app.main:app --reload")
        print(f"2. Open interface: http://localhost:8000/api/v1/sessions/{{session_id}}/interface")
        print("3. Test with real photos and camera")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure FastAPI server is running")
        print("2. Check that all static files exist")
        print("3. Verify database connections")


if __name__ == "__main__":
    main()