#!/usr/bin/env python3
"""
Test database connection with new isolation level settings
"""

import sys
sys.path.insert(0, '/home/ubuntu/moneyone_backend/backend')

from database import get_db_connection

def test_connection():
    print("Testing database connection...")
    
    conn = get_db_connection()
    
    if not conn:
        print("❌ Database connection failed!")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Test basic query
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            print(f"✅ Basic query works: {result}")
            
            # Check timezone
            cursor.execute("SELECT @@session.time_zone as tz")
            tz = cursor.fetchone()
            print(f"✅ Timezone: {tz['tz']}")
            
            # Check isolation level
            cursor.execute("SELECT @@session.tx_isolation as isolation")
            isolation = cursor.fetchone()
            print(f"✅ Isolation Level: {isolation['isolation']}")
            
            # Test a real query
            cursor.execute("SELECT COUNT(*) as count FROM merchants")
            merchants = cursor.fetchone()
            print(f"✅ Merchants count: {merchants['count']}")
            
        conn.close()
        print("\n✅ All tests passed! Database connection is working properly.")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
