#!/usr/bin/env python3
"""
Test Rang API using PG TXN ID instead of Order ID
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
from database import get_db_connection

def test_with_pg_txn_id():
    """Test status check using PG TXN ID"""
    print("TESTING RANG API WITH PG TXN ID")
    print("=" * 50)
    
    # Get transaction with PG TXN ID
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT txn_id, order_id, pg_txn_id, amount, status
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND pg_txn_id IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        txn = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not txn:
            print("❌ No transactions with PG TXN ID found")
            return
        
        print(f"Testing with transaction:")
        print(f"  TXN ID: {txn['txn_id']}")
        print(f"  Order ID: {txn['order_id']}")
        print(f"  PG TXN ID: {txn['pg_txn_id']}")
        print(f"  Amount: ₹{txn['amount']}")
        print(f"  Status: {txn['status']}")
        
        # Test with PG TXN ID
        rang_service = RangService()
        
        print(f"\n🔍 Testing with PG TXN ID: {txn['pg_txn_id']}")
        result = rang_service.check_payment_status(txn['pg_txn_id'])
        
        print(f"Result: {result}")
        
        if result['success']:
            print("✅ SUCCESS! PG TXN ID works for status check")
            return True
        else:
            print(f"❌ Failed with PG TXN ID: {result.get('message')}")
            
        # Also test with Order ID for comparison
        print(f"\n🔍 Testing with Order ID: {txn['order_id']}")
        result2 = rang_service.check_payment_status(txn['order_id'])
        
        print(f"Result: {result2}")
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_with_pg_txn_id()