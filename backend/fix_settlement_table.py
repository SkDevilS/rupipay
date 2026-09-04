"""
Fix settlement_transactions table by dropping and recreating with correct types
"""

import pymysql
from config import Config

def get_db_connection():
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def fix_settlement_table():
    print("=" * 80)
    print("FIXING SETTLEMENT_TRANSACTIONS TABLE")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'settlement_transactions'
            """, (Config.DB_NAME,))
            
            if cursor.fetchone()['count'] == 0:
                print("✓ settlement_transactions table doesn't exist, nothing to fix")
                conn.close()
                return True
            
            # Drop the table
            print("Dropping existing settlement_transactions table...")
            cursor.execute("DROP TABLE IF EXISTS settlement_transactions")
            print("✓ Dropped settlement_transactions table")
            print()
            
            conn.commit()
        
        conn.close()
        
        print("=" * 80)
        print("✅ TABLE DROPPED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("Now run the migration script again:")
        print("  python3 migrate_settled_unsettled_wallet.py migrate")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        return False

if __name__ == "__main__":
    import sys
    fix_settlement_table()
    sys.exit(0)
