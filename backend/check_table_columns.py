#!/usr/bin/env python3
"""Check actual columns in database tables"""

from database import get_db_connection

def check_table_columns():
    """Check columns in key tables"""
    tables_to_check = [
        'fund_requests',
        'payout_transactions', 
        'merchant_wallet_transactions',
        'merchant_banks',
        'admin_wallet',
        'admin_wallet_transactions'
    ]
    
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return
    
    try:
        with conn.cursor() as cursor:
            for table in tables_to_check:
                print(f"\n{table}:")
                print("-" * 60)
                
                try:
                    cursor.execute(f"DESCRIBE {table}")
                    columns = cursor.fetchall()
                    
                    for col in columns:
                        print(f"  {col['Field']:30s} {col['Type']:20s} {col['Null']:5s} {col['Key']:5s}")
                        
                except Exception as e:
                    print(f"  ERROR: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    check_table_columns()
