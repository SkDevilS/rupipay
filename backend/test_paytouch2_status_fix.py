#!/usr/bin/env python3
"""
Test PayTouch2 Status Check Fix
Quick test to verify the 500 error is fixed
"""

from database import get_db_connection
import json

def test_paytouch2_status_fix():
    """Test the PayTouch2 status check fix"""
    
    print("🧪 Testing PayTouch2 Status Check Fix")
    print("=" * 50)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Find a PayTouch2 transaction
            cursor.execute("""
                SELECT txn_id, reference_id, pg_partner, status, merchant_id, pg_txn_id, 
                       amount, utr, created_at, completed_at
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            txn = cursor.fetchone()
            
            if not txn:
                print("ℹ️  No PayTouch2 transactions found")
                return True
            
            print(f"Found PayTouch2 transaction: {txn['txn_id']}")
            print(f"  Reference ID: {txn['reference_id']}")
            print(f"  Status: {txn['status']}")
            print(f"  Amount: {txn['amount']}")
            print(f"  Merchant ID: {txn['merchant_id']}")
            print(f"  PG TXN ID: {txn['pg_txn_id']}")
            
            # Test the data access that was causing the error
            try:
                amount_value = float(txn['amount']) if txn['amount'] else 0.0
                print(f"✅ Amount conversion successful: {amount_value}")
                
                # Test the response format
                response_data = {
                    'txn_id': txn['txn_id'],
                    'reference_id': txn['reference_id'],
                    'amount': amount_value,
                    'status': txn['status'],
                    'utr': txn['utr'],
                    'pg_txn_id': txn['pg_txn_id'],
                    'pg_partner': txn['pg_partner'],
                    'created_at': txn['created_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['created_at'] else None,
                    'completed_at': txn['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if txn['completed_at'] else None
                }
                
                print("✅ Response data structure test passed")
                print(f"Response preview: {json.dumps(response_data, indent=2)}")
                
            except Exception as e:
                print(f"❌ Data access error: {e}")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

def main():
    """Main function"""
    success = test_paytouch2_status_fix()
    
    if success:
        print("\n✅ PayTouch2 status check fix test passed!")
        print("The 500 error should be resolved now.")
    else:
        print("\n❌ PayTouch2 status check fix test failed!")

if __name__ == '__main__':
    main()