"""
Check merchant_id column types across tables
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

def check_column_types():
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Check merchant_id in merchants table
            cursor.execute("""
                SELECT COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, COLLATION_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'merchants'
                AND COLUMN_NAME = 'merchant_id'
            """, (Config.DB_NAME,))
            merchants_col = cursor.fetchone()
            
            # Check merchant_id in merchant_wallet table
            cursor.execute("""
                SELECT COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, COLLATION_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'merchant_wallet'
                AND COLUMN_NAME = 'merchant_id'
            """, (Config.DB_NAME,))
            wallet_col = cursor.fetchone()
            
            # Check admin_id in admin_users table
            cursor.execute("""
                SELECT COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, COLLATION_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'admin_users'
                AND COLUMN_NAME = 'admin_id'
            """, (Config.DB_NAME,))
            admin_col = cursor.fetchone()
            
            print("=" * 80)
            print("COLUMN TYPE ANALYSIS")
            print("=" * 80)
            print()
            
            print("merchants.merchant_id:")
            print(f"  Type: {merchants_col['COLUMN_TYPE']}")
            print(f"  Max Length: {merchants_col['CHARACTER_MAXIMUM_LENGTH']}")
            print(f"  Collation: {merchants_col['COLLATION_NAME']}")
            print()
            
            print("merchant_wallet.merchant_id:")
            print(f"  Type: {wallet_col['COLUMN_TYPE']}")
            print(f"  Max Length: {wallet_col['CHARACTER_MAXIMUM_LENGTH']}")
            print(f"  Collation: {wallet_col['COLLATION_NAME']}")
            print()
            
            print("admin_users.admin_id:")
            print(f"  Type: {admin_col['COLUMN_TYPE']}")
            print(f"  Max Length: {admin_col['CHARACTER_MAXIMUM_LENGTH']}")
            print(f"  Collation: {admin_col['COLLATION_NAME']}")
            print()
            
            # Recommendation
            print("=" * 80)
            print("RECOMMENDATION FOR settlement_transactions TABLE:")
            print("=" * 80)
            print()
            print(f"merchant_id should be: {merchants_col['COLUMN_TYPE']}")
            print(f"settled_by should be: {admin_col['COLUMN_TYPE']}")
            print()
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        conn.close()

if __name__ == "__main__":
    check_column_types()
