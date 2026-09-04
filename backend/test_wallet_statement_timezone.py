#!/usr/bin/env python3
"""
Test script to check wallet statement timezone conversion
"""

import pymysql
from database import get_db_connection

def test_wallet_statement_query():
    """Test the wallet statement query to see what dates are returned"""
    
    merchant_id = "test"  # Replace with actual merchant_id from screenshot
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Test query with timezone conversion
            query = """
                SELECT 
                    id,
                    CAST(settlement_id AS CHAR) as txn_id,
                    'UNSETTLED_SETTLEMENT' as category,
                    'CREDIT' as txn_type,
                    amount,
                    DATE_FORMAT(CONVERT_TZ(created_at, '+00:00', '+05:30'), '%Y-%m-%d %H:%i:%s') as created_at,
                    'COMPLETED' as status
                FROM settlement_transactions
                WHERE merchant_id = %s
                LIMIT 5
            """
            
            cursor.execute(query, (merchant_id,))
            results = cursor.fetchall()
            
            print("\n" + "="*80)
            print("WALLET STATEMENT TIMEZONE TEST")
            print("="*80)
            print(f"\nMerchant ID: {merchant_id}")
            print(f"Results found: {len(results)}")
            print("\n" + "-"*80)
            
            for row in results:
                print(f"\nTransaction ID: {row['txn_id']}")
                print(f"Category: {row['category']}")
                print(f"Amount: {row['amount']}")
                print(f"Created At (IST): {row['created_at']}")
                print(f"Type: {type(row['created_at'])}")
                print("-"*80)
            
            # Also test the raw created_at without conversion
            query_raw = """
                SELECT 
                    settlement_id,
                    created_at as utc_time,
                    CONVERT_TZ(created_at, '+00:00', '+05:30') as ist_time,
                    DATE_FORMAT(CONVERT_TZ(created_at, '+00:00', '+05:30'), '%Y-%m-%d %H:%i:%s') as formatted_ist
                FROM settlement_transactions
                WHERE merchant_id = %s
                LIMIT 3
            """
            
            cursor.execute(query_raw, (merchant_id,))
            raw_results = cursor.fetchall()
            
            print("\n" + "="*80)
            print("RAW TIMEZONE COMPARISON")
            print("="*80)
            
            for row in raw_results:
                print(f"\nSettlement ID: {row['settlement_id']}")
                print(f"UTC Time: {row['utc_time']}")
                print(f"IST Time (datetime): {row['ist_time']}")
                print(f"IST Time (formatted): {row['formatted_ist']}")
                print("-"*80)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    test_wallet_statement_query()
