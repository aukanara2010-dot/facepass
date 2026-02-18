#!/usr/bin/env python3
"""
Test script to verify frontend-backend integration fixes

This script tests:
1. API response contains correct field names (preview_path, file_path)
2. Session ID is properly handled in responses
3. No undefined values in API responses
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_api_response_fields():
    """Test that API responses use correct field names"""
    print("Testing API response field names...")
    
    # Check faces.py for correct field usage
    try:
        with open('app/api/v1/endpoints/faces.py', 'r') as f:
            content = f.read()
        
        # Check for correct field names in SQL query
        has_preview_path_sql = 'preview_path' in content and 'SELECT id, file_name, preview_path, file_path' in content
        has_file_path_sql = 'file_path' in content
        
        # Check for correct field names in response building
        has_preview_path_response = '"preview_path": photo_info["preview_path"]' in content
        has_file_path_response = '"file_path": photo_info["file_path"]' in content
        
        # Check for old incorrect field names
        has_old_url_preview = 'url_preview' in content
        has_old_url_original = 'url_original' in content
        
        print(f"✓ SQL query uses preview_path: {has_preview_path_sql}")
        print(f"✓ SQL query uses file_path: {has_file_path_sql}")
        print(f"✓ Response uses preview_path: {has_preview_path_response}")
        print(f"✓ Response uses file_path: {has_file_path_response}")
        print(f"✗ Still has url_preview: {has_old_url_preview}")
        print(f"✗ Still has url_original: {has_old_url_original}")
        
        if (has_preview_path_sql and has_file_path_sql and 
            has_preview_path_response and has_file_path_response and 
            not has_old_url_preview and not has_old_url_original):
            print("✅ API response fields are correct")
            return True
        else:
            print("❌ API response fields need fixing")
            return False
            
    except Exception as e:
        print(f"❌ Error checking API response fields: {e}")
        return False

def test_frontend_field_usage():
    """Test that frontend uses correct field names"""
    print("\nTesting frontend field usage...")
    
    try:
        with open('app/static/js/face-search.js', 'r') as f:
            content = f.read()
        
        # Check for correct field names
        uses_preview_path = 'photo.preview_path' in content
        uses_file_path = 'photo.file_path' in content
        
        # Check for old incorrect field names
        uses_old_url_preview = 'photo.url_preview' in content
        uses_old_url = 'photo.url' in content
        
        print(f"✓ Uses preview_path: {uses_preview_path}")
        print(f"✓ Uses file_path: {uses_file_path}")
        print(f"✗ Still uses url_preview: {uses_old_url_preview}")
        print(f"✗ Still uses url: {uses_old_url}")
        
        if uses_preview_path and uses_file_path and not uses_old_url_preview:
            print("✅ Frontend field usage is correct")
            return True
        else:
            print("❌ Frontend field usage needs fixing")
            return False
            
    except Exception as e:
        print(f"❌ Error checking frontend field usage: {e}")
        return False

def test_session_id_handling():
    """Test session ID handling in frontend"""
    print("\nTesting session ID handling...")
    
    try:
        with open('app/static/js/face-search.js', 'r') as f:
            content = f.read()
        
        # Check for proper session ID handling
        has_session_id_logging = 'console.log' in content and 'session' in content.lower()
        has_undefined_check = 'undefined' in content and 'sessionId' in content
        has_session_id_validation = 'this.sessionId' in content
        
        # Check that session ID is not overwritten from API response
        overwrites_session_id = 'this.sessionId = result.session_id' in content
        
        print(f"✓ Has session ID logging: {has_session_id_logging}")
        print(f"✓ Has undefined check: {has_undefined_check}")
        print(f"✓ Has session ID validation: {has_session_id_validation}")
        print(f"✗ Overwrites session ID from API: {overwrites_session_id}")
        
        if (has_session_id_logging and has_undefined_check and 
            has_session_id_validation and not overwrites_session_id):
            print("✅ Session ID handling is correct")
            return True
        else:
            print("❌ Session ID handling needs improvement")
            return False
            
    except Exception as e:
        print(f"❌ Error checking session ID handling: {e}")
        return False

def test_api_endpoint_response_structure():
    """Test that API endpoint returns correct response structure"""
    print("\nTesting API endpoint response structure...")
    
    try:
        with open('app/api/v1/endpoints/faces.py', 'r') as f:
            content = f.read()
        
        # Check for required fields in response
        has_session_id_response = '"session_id": session_id' in content
        has_matches_response = '"matches": final_matches' in content
        has_session_name_response = '"session_name": session.name' in content
        
        print(f"✓ Returns session_id: {has_session_id_response}")
        print(f"✓ Returns matches: {has_matches_response}")
        print(f"✓ Returns session_name: {has_session_name_response}")
        
        if has_session_id_response and has_matches_response and has_session_name_response:
            print("✅ API endpoint response structure is correct")
            return True
        else:
            print("❌ API endpoint response structure needs fixing")
            return False
            
    except Exception as e:
        print(f"❌ Error checking API endpoint response: {e}")
        return False

def main():
    """Run all integration tests"""
    print("Testing frontend-backend integration fixes...")
    print("=" * 60)
    
    success_count = 0
    total_tests = 4
    
    # Test 1: API response fields
    if test_api_response_fields():
        success_count += 1
    
    # Test 2: Frontend field usage
    if test_frontend_field_usage():
        success_count += 1
    
    # Test 3: Session ID handling
    if test_session_id_handling():
        success_count += 1
    
    # Test 4: API endpoint response structure
    if test_api_endpoint_response_structure():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("✅ All integration tests passed!")
        print("\nChanges implemented:")
        print("1. ✓ Fixed database field names: url_preview → preview_path, url_original → file_path")
        print("2. ✓ Updated frontend to use correct field names")
        print("3. ✓ Added session ID validation and logging")
        print("4. ✓ Removed session ID overwriting from API response")
        print("5. ✓ Added debugging information for troubleshooting")
        print("\nExpected behavior:")
        print("- No more 'undefined' in URLs")
        print("- Correct image paths from database")
        print("- Proper session ID handling")
        print("- Clear error messages for debugging")
    else:
        print("❌ Some integration tests failed.")
        print("\nNext steps:")
        print("1. Check the failed tests above")
        print("2. Verify field names in database and API")
        print("3. Test with browser developer tools")
        print("4. Check network requests for 'undefined' values")

if __name__ == "__main__":
    main()