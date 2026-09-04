#!/usr/bin/env python3
"""
Clear all data from database tables while keeping table structure intact
"""
import pymysql
from config import Config

def clear_all_data():
    """Truncate all tables in the database"""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Disable foreign key checks temporarily
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            # List of all tables in order (respecting dependencies)
            tables = [
                'admin_activity_logs',
                'callback_logs',
                'payu_webhook_logs',
                'payu_webhook_config',
                'payu_tokens',
                'wallet_transactions',
                'admin_wallet_transactions',
                'merchant_unsettled_wallet',
                'merchant_wallet',
                'admin_wallet',
                'payout_transactions',
                'payin_transactions',
                'fund_requests',
                'service_routing',
                'merchant_callbacks',
                'merchant_ip_whitelist',
                'merchant_documents',
                'merchant_banks',
                'admin_banks',
                'commercial_charges',
                'merchants',
                'commercial_schemes',
                'admin_users'
            ]
            
            print("Starting to clear all data from tables...")
            print("=" * 60)
            
            for table in tables:
                try:
                    cursor.execute(f"TRUNCATE TABLE {table}")
                    print(f"✓ Cleared data from: {table}")
                except Exception as e:
                    print(f"✗ Error clearing {table}: {e}")
            
            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            connection.commit()
            print("=" * 60)
            print("✓ All data cleared successfully!")
            print("\nNote: Table structures are intact. You can now:")
            print("1. Run create_admin_user.py to create a new admin")
            print("2. Run create_test_merchant.py to create test merchants")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("WARNING: This will delete ALL data from the database!")
    print("Table structures will remain intact.")
    confirm = input("\nAre you sure you want to continue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        clear_all_data()
    else:
        print("Operation cancelled.")
