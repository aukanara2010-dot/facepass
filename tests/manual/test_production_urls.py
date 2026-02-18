#!/usr/bin/env python3
"""
Test FacePass production URLs and routing.
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


def test_local_urls():
    """Test URLs on local development server."""
    print("🏠 Testing Local URLs (localhost:8000)")
    
    session_id = get_test_session_id()
    if not session_id:
        print("❌ No test session available")
        return False
    
    base_url = "http://localhost:8000"
    
    urls_to_test = [
        # Root endpoint
        ("/", "Root API endpoint"),
        
        # Public session interface (new beautiful URL)
        (f"/session/{session_id}", "Public session interface"),
        
        # API endpoints
        (f"/api/v1/sessions/validate/{session_id}", "Session validation API"),
        (f"/api/v1/sessions/{session_id}", "Session details API"),
        (f"/api/v1/sessions/{session_id}/facepass-status", "FacePass status API"),
        
        # Static files
        ("/static/js/face-search.js", "JavaScript file"),
        ("/static/images/facepass-logo.svg", "Logo SVG"),
        ("/static/images/favicon.svg", "Favicon SVG"),
        
        # Error cases
        ("/session/00000000-0000-0000-0000-000000000000", "Non-existent session (should be 404)"),
    ]
    
    all_passed = True
    
    for endpoint, description in urls_to_test:
        url = f"{base_url}{endpoint}"
        
        try:
            print(f"\n📡 Testing: {description}")
            print(f"   URL: {url}")
            
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            # Validate responses
            if endpoint == "/":
                if response.status_code == 200:
                    data = response.json()
                    if "FacePass API" in data.get("message", ""):
                        print("   ✅ Root endpoint working")
                    else:
                        print("   ⚠️  Unexpected root response")
                        all_passed = False
                else:
                    print("   ❌ Root endpoint failed")
                    all_passed = False
                    
            elif endpoint.startswith("/session/"):
                if "00000000-0000-0000-0000-000000000000" in endpoint:
                    # Should be 404
                    if response.status_code == 404:
                        print("   ✅ Correctly returns 404 for non-existent session")
                    else:
                        print("   ⚠️  Should return 404 for non-existent session")
                        all_passed = False
                else:
                    # Should be 200 with HTML
                    if response.status_code == 200 and "text/html" in response.headers.get('content-type', ''):
                        content = response.text
                        if "FacePass" in content and session_id in content:
                            print("   ✅ Session interface loaded correctly")
                        else:
                            print("   ⚠️  Session interface content incomplete")
                            all_passed = False
                    else:
                        print("   ❌ Session interface failed")
                        all_passed = False
                        
            elif endpoint.startswith("/api/v1/"):
                if response.status_code == 200:
                    print("   ✅ API endpoint working")
                else:
                    print("   ❌ API endpoint failed")
                    all_passed = False
                    
            elif endpoint.startswith("/static/"):
                if response.status_code == 200:
                    print(f"   ✅ Static file accessible (Size: {len(response.content)} bytes)")
                else:
                    print("   ❌ Static file not accessible")
                    all_passed = False
                    
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")
            all_passed = False
    
    return all_passed


def test_production_readiness():
    """Test production readiness indicators."""
    print("\n🚀 Testing Production Readiness")
    
    session_id = get_test_session_id()
    if not session_id:
        print("❌ No test session available")
        return False
    
    base_url = "http://localhost:8000"
    session_url = f"{base_url}/session/{session_id}"
    
    try:
        response = requests.get(session_url, timeout=10)
        
        if response.status_code != 200:
            print("❌ Session interface not accessible")
            return False
        
        content = response.text
        
        # Check for production readiness indicators
        checks = [
            ("OpenGraph meta tags", 'property="og:title"' in content),
            ("Twitter Card meta tags", 'name="twitter:card"' in content),
            ("Favicon link", 'rel="icon"' in content),
            ("Proper title", "FacePass" in content and "title>" in content),
            ("Meta description", 'name="description"' in content),
            ("Relative API paths", '"/api/v1/' in content),
            ("Staging domain for purchases", 'staging.pixorasoft.ru' in content),
            ("Session ID injection", session_id in content),
            ("Tailwind CSS", 'tailwindcss.com' in content),
            ("JavaScript file", 'face-search.js' in content),
        ]
        
        print("📋 Production readiness checks:")
        all_passed = True
        
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
            if not passed:
                all_passed = False
        
        return all_passed
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to test production readiness: {str(e)}")
        return False


def test_cors_headers():
    """Test CORS headers for production domains."""
    print("\n🔒 Testing CORS Configuration")
    
    base_url = "http://localhost:8000"
    test_origins = [
        "https://facepass.pixorasoft.ru",
        "https://staging.pixorasoft.ru",
        "https://pixorasoft.ru"
    ]
    
    all_passed = True
    
    for origin in test_origins:
        try:
            print(f"\n📡 Testing CORS for: {origin}")
            
            # Test preflight request
            response = requests.options(
                f"{base_url}/api/v1/sessions/validate/test",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type"
                },
                timeout=5
            )
            
            print(f"   Status: {response.status_code}")
            
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
            }
            
            for header, value in cors_headers.items():
                if value:
                    print(f"   ✅ {header}: {value}")
                else:
                    print(f"   ❌ Missing {header}")
                    all_passed = False
                    
        except requests.exceptions.RequestException as e:
            print(f"   ❌ CORS test failed: {str(e)}")
            all_passed = False
    
    return all_passed


def main():
    """Run all production URL tests."""
    print("🚀 Starting FacePass Production URL Tests\n")
    
    tests = [
        ("Local URLs", test_local_urls),
        ("Production Readiness", test_production_readiness),
        ("CORS Configuration", test_cors_headers)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
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
        print("\n🎉 All tests passed! FacePass is ready for production!")
        print("\n📋 Next steps for production deployment:")
        print("1. Deploy to facepass.pixorasoft.ru server")
        print("2. Configure SSL certificates")
        print("3. Set up Nginx reverse proxy")
        print("4. Update DNS records")
        print("5. Test with real domain")
        print("\n🔗 Production URLs will be:")
        session_id = get_test_session_id()
        if session_id:
            print(f"   https://facepass.pixorasoft.ru/session/{session_id}")
        print("   https://facepass.pixorasoft.ru/api/v1/...")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        print("\n🔧 Common issues:")
        print("1. Make sure FastAPI server is running on port 8000")
        print("2. Check that all static files exist")
        print("3. Verify database connections")
        print("4. Ensure CORS middleware is properly configured")


if __name__ == "__main__":
    main()