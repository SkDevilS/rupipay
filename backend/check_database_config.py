#!/usr/bin/env python3
"""
Check database configuration and connection
"""

from database import get_db_connection
from config import Config

def check_database_config():
    """Check which database we're connecting to"""
    print("=" * 80)
    print("DATABASE CONFIGURATION CHECK")
    print("=" * 80)
    
    print(f"\n📋 Configuration from config.py:")
    print(f"DB_HOST: {Config.DB_HOST}")
    print(f"DB_NAME: {Config.DB_NAME}")
    print(f"DB_USER: {Config.DB_USER}")
    
    conn = get_db_connection()
    if not conn:
        print("\n❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check current database
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()
            print(f"\n✅ Connected to database: {list(current_db.values())[0]}")
            
            # Check server info
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"MySQL Version: {list(version.values())[0]}")
            
            # Check connection ID
            cursor.execute("SELECT CONNECTION_ID()")
            conn_id = cursor.fetchone()
            print(f"Connection ID: {list(conn_id.values())[0]}")
            
            # Check current user
            cursor.execute("SELECT USER()")
            user = cursor.fetchone()
            print(f"Connected as: {list(user.values())[0]}")
            
            # Check if there are multiple databases with similar names
            cursor.execute("SHOW DATABASES LIKE '%moneyone%'")
            databases = cursor.fetchall()
            print(f"\n📊 Databases matching 'moneyone':")
            for db in databases:
                db_name = list(db.values())[0]
                cursor.execute(f"SELECT COUNT(*) as count FROM `{db_name}`.payout_transactions")
                count = cursor.fetchone()
                print(f"  - {db_name}: {count['count']} payout records")
            
            # Check table structure
            cursor.execute("DESCRIBE payout_transactions")
            columns = cursor.fetchall()
            print(f"\n📋 payout_transactions table columns:")
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']}")
            
            # Check for the specific reference_id
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM payout_transactions 
                WHERE reference_id = 'DP2026030417553292BE6E'
            """)
            result = cursor.fetchone()
            print(f"\n🔍 Searching for DP2026030417553292BE6E:")
            print(f"  Found: {result['count']} record(s)")
            
            # Check recent inserts
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    merchant_id,
                    amount,
                    status,
                    created_at
                FROM payout_transactions
                WHERE created_at >= NOW() - INTERVAL 1 HOUR
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent = cursor.fetchall()
            print(f"\n📋 Recent payouts (last hour):")
            for txn in recent:
                print(f"  - {txn['reference_id']}: ₹{txn['amount']:.2f} ({txn['status']}) at {txn['created_at']}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    check_database_config()
