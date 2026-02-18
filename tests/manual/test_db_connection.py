#!/usr/bin/env python3
"""
Simple test for Pixora database connection.
"""

import sys
import os
from sqlalchemy import create_engine, text

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import get_settings


def test_connection():
    """Test connection to external Pixora database."""
    print("🔍 Testing Pixora database connection...")
    
    try:
        settings = get_settings()
        print(f"📡 Connecting to: {settings.MAIN_APP_DATABASE_URL}")
        
        # Create engine
        engine = create_engine(settings.MAIN_APP_DATABASE_URL)
        
        # Test connection
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT 1 as test")).fetchone()
            print(f"✅ Basic connection test: {result[0]}")
            
            # Check PostgreSQL version
            version = conn.execute(text("SELECT version()")).fetchone()
            print(f"📊 PostgreSQL version: {version[0][:50]}...")
            
            # Test photo_sessions table existence
            table_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'photo_sessions'
                );
            """)).fetchone()
            
            if table_check[0]:
                print("✅ photo_sessions table exists")
                
                # Get table structure
                columns = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'photo_sessions'
                    ORDER BY ordinal_position;
                """)).fetchall()
                
                print("📋 Table structure:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
                
                # Count records
                count = conn.execute(text("SELECT COUNT(*) FROM photo_sessions")).fetchone()
                print(f"📊 Total sessions: {count[0]}")
                
                # Sample records with FacePass enabled
                facepass_count = conn.execute(text("""
                    SELECT COUNT(*) FROM photo_sessions 
                    WHERE facepass_enabled = true
                """)).fetchone()
                print(f"🎯 Sessions with FacePass enabled: {facepass_count[0]}")
                
                # Sample records
                if count[0] > 0:
                    samples = conn.execute(text("""
                        SELECT id, name, facepass_enabled, studio_id 
                        FROM photo_sessions 
                        ORDER BY id DESC
                        LIMIT 5
                    """)).fetchall()
                    
                    print("📝 Sample records (latest 5):")
                    for sample in samples:
                        facepass_status = "✅" if sample[2] else "❌"
                        print(f"   - ID: {sample[0]}, Name: {sample[1]}, FacePass: {facepass_status}, Studio: {sample[3]}")
            else:
                print("❌ photo_sessions table does not exist")
                
                # List available tables
                tables = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)).fetchall()
                
                print("📋 Available tables:")
                for table in tables[:10]:  # Show first 10 tables
                    print(f"   - {table[0]}")
                if len(tables) > 10:
                    print(f"   ... and {len(tables) - 10} more tables")
        
        print("\n🎉 Connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)