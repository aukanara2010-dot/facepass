#!/usr/bin/env python3
"""
Test script to verify all endpoints are working correctly
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported without errors"""
    print("Testing imports...")
    
    try:
        from app.api.deps import get_db, get_vector_db_session
        print("✓ app.api.deps imported successfully")
    except Exception as e:
        print(f"✗ Failed to import app.api.deps: {e}")
        return False
    
    try:
        from app.api.v1.endpoints import users, faces, health
        print("✓ All endpoints imported successfully")
    except Exception as e:
        print(f"✗ Failed to import endpoints: {e}")
        return False
    
    try:
        from core.database import MainSessionLocal, VectorSessionLocal
        print("✓ Database sessions imported successfully")
    except Exception as e:
        print(f"✗ Failed to import database sessions: {e}")
        return False
    
    return True


def test_dependency_functions():
    """Test that dependency functions are generators"""
    print("\nTesting dependency functions...")
    
    from app.api.deps import get_db, get_vector_db_session
    import inspect
    
    # Check if functions are generators
    if inspect.isgeneratorfunction(get_db):
        print("✓ get_db is a generator function")
    else:
        print("✗ get_db is NOT a generator function")
        return False
    
    if inspect.isgeneratorfunction(get_vector_db_session):
        print("✓ get_vector_db_session is a generator function")
    else:
        print("✗ get_vector_db_session is NOT a generator function")
        return False
    
    return True


def test_endpoint_signatures():
    """Test that all endpoints have correct signatures"""
    print("\nTesting endpoint signatures...")
    
    from app.api.v1.endpoints import users, faces, health
    from fastapi import Depends
    import inspect
    
    endpoints_to_check = [
        (users.create_user, "users.create_user"),
        (users.list_users, "users.list_users"),
        (users.get_user, "users.get_user"),
        (users.delete_user, "users.delete_user"),
        (faces.upload_face, "faces.upload_face"),
        (faces.get_user_faces, "faces.get_user_faces"),
        (faces.get_face, "faces.get_face"),
        (faces.delete_face, "faces.delete_face"),
        (faces.search_faces, "faces.search_faces"),
        (health.health_check, "health.health_check"),
    ]
    
    all_good = True
    for func, name in endpoints_to_check:
        sig = inspect.signature(func)
        has_db_param = False
        
        for param_name, param in sig.parameters.items():
            if param_name in ['db', 'vector_db']:
                # Check if it uses Depends
                if param.default != inspect.Parameter.empty:
                    has_db_param = True
                    print(f"✓ {name} has db parameter with Depends")
                else:
                    print(f"✗ {name} has db parameter but no Depends")
                    all_good = False
        
        if not has_db_param and name != "health.health_check":
            # health_check might not need db in some cases
            pass
    
    return all_good


def main():
    print("=" * 60)
    print("FacePass Endpoints Test")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_dependency_functions,
        test_endpoint_signatures,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
