"""
Test if unsettled wallet credit is working correctly
"""

import pymysql
from database import get_db_connection
from wallet_service import wallet_service

def test_unsettled_credit():
    """Test crediting unsettled wallet"""
    print("=" * 80)
    print("TESTING UNSETTLED WALLET CREDIT")
    print("=" * 80)
    
    # Test merchant ID
    test_merchant_id = "TEST_MERCHANT_001"
    test_amount = 100.00
    test_ref_id = "TEST_TXN_001"
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check if test merchant wallet exists
            cursor.execute("""
                SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
            """, (test_merchant_id,))
            
            wallet = cursor.fetchone()
            
            if wallet:
                before_balance = float(wallet['unsettled_balance'])
                print(f"✓ Test merchant wallet exists")
                print(f"  Unsettled Balance Before: ₹{before_balance}")
            else:
                print(f"Creating test merchant wallet...")
                cursor.execute("""
                    INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                    VALUES (%s, 0.00, 0.00, 0.00)
                """, (test_merchant_id,))
                conn.commit()
                before_balance = 0.00
                print(f"✓ Test merchant wallet created")
            
            # Test credit_unsettled_wallet function
            print(f"\nTesting credit_unsettled_wallet with ₹{test_amount}...")
            result = wallet_service.credit_unsettled_wallet(
                merchant_id=test_merchant_id,
                amount=test_amount,
                description=f"Test payin credit",
                reference_id=test_ref_id
            )
            
            if result['success']:
                print(f"✅ Credit successful!")
                print(f"   TXN ID: {result['txn_id']}")
                print(f"   Balance Before: ₹{result['unsettled_before']}")
                print(f"   Balance After: ₹{result['unsettled_after']}")
                
                # Verify in database
                cursor.execute("""
                    SELECT unsettled_balance FROM merchant_wallet WHERE merchant_id = %s
                """, (test_merchant_id,))
                
                wallet_after = cursor.fetchone()
                actual_balance = float(wallet_after['unsettled_balance'])
                
                print(f"\n✓ Verified in database:")
                print(f"   Actual Unsettled Balance: ₹{actual_balance}")
                
                if actual_balance == before_balance + test_amount:
                    print(f"✅ BALANCE UPDATED CORRECTLY!")
                else:
                    print(f"❌ BALANCE MISMATCH!")
                    print(f"   Expected: ₹{before_balance + test_amount}")
                    print(f"   Actual: ₹{actual_balance}")
                
                # Check transaction record
                cursor.execute("""
                    SELECT * FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                """, (test_ref_id,))
                
                txn = cursor.fetchone()
                if txn:
                    print(f"\n✓ Transaction record found:")
                    print(f"   TXN ID: {txn['txn_id']}")
                    print(f"   Amount: ₹{txn['amount']}")
                    print(f"   Description: {txn['description']}")
                else:
                    print(f"\n❌ Transaction record NOT found!")
                
            else:
                print(f"❌ Credit failed: {result.get('message')}")
            
            # Cleanup - delete test data
            print(f"\nCleaning up test data...")
            cursor.execute("""
                DELETE FROM merchant_wallet_transactions WHERE reference_id = %s
            """, (test_ref_id,))
            cursor.execute("""
                UPDATE merchant_wallet SET unsettled_balance = %s WHERE merchant_id = %s
            """, (before_balance, test_merchant_id))
            conn.commit()
            print(f"✓ Test data cleaned up")
            
    finally:
        conn.close()
    
    print("=" * 80)

if __name__ == '__main__':
    test_unsettled_credit()
