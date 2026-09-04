"""
Diagnose PayTouch API Error
Checks the specific transaction and PayTouch API response
"""

import sys
import pymysql
from database import get_db_connection

def diagnose_transaction(txn_id):
    """Diagnose specific transaction"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get transaction details
            cursor.execute("""
                SELECT * FROM payout_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"❌ Transaction {txn_id} not found")
                return
            
            print("=" * 80)
            print(f"Transaction Details: {txn_id}")
            print("=" * 80)
            print(f"Merchant ID: {txn.get('merchant_id')}")
            print(f"Admin ID: {txn.get('admin_id')}")
            print(f"Reference ID: {txn.get('reference_id')}")
            print(f"Amount: ₹{txn.get('amount')}")
            print(f"Charge Amount: ₹{txn.get('charge_amount')}")
            print(f"Net Amount: ₹{txn.get('net_amount')}")
            print(f"Status: {txn.get('status')}")
            print(f"PG Partner: {txn.get('pg_partner')}")
            print(f"PG TXN ID: {txn.get('pg_txn_id')}")
            print(f"Error Message: {txn.get('error_message')}")
            print(f"Created At: {txn.get('created_at')}")
            print(f"Updated At: {txn.get('updated_at')}")
            print(f"Completed At: {txn.get('completed_at')}")
            print()
            
            print("Bank Details:")
            print(f"  Beneficiary Name: {txn.get('bene_name')}")
            print(f"  Account Number: {txn.get('account_no')}")
            print(f"  IFSC Code: {txn.get('ifsc_code')}")
            print(f"  Bank Name: {txn.get('bene_bank')}")
            print(f"  Payment Type: {txn.get('payment_type')}")
            print()
            
            # Check if merchant exists
            if txn.get('merchant_id'):
                cursor.execute("""
                    SELECT merchant_id, full_name, email, is_active, scheme_id
                    FROM merchants
                    WHERE merchant_id = %s
                """, (txn['merchant_id'],))
                
                merchant = cursor.fetchone()
                if merchant:
                    print("Merchant Details:")
                    print(f"  ID: {merchant['merchant_id']}")
                    print(f"  Name: {merchant['full_name']}")
                    print(f"  Email: {merchant['email']}")
                    print(f"  Active: {merchant['is_active']}")
                    print(f"  Scheme ID: {merchant['scheme_id']}")
                    print()
                    
                    # Check wallet balance
                    cursor.execute("""
                        SELECT settled_balance, unsettled_balance, balance
                        FROM merchant_wallet
                        WHERE merchant_id = %s
                    """, (txn['merchant_id'],))
                    
                    wallet = cursor.fetchone()
                    if wallet:
                        print("Wallet Balance:")
                        print(f"  Settled: ₹{wallet.get('settled_balance', 0):.2f}")
                        print(f"  Unsettled: ₹{wallet.get('unsettled_balance', 0):.2f}")
                        print(f"  Total: ₹{wallet.get('balance', 0):.2f}")
                        print()
            
            # Check service routing
            if txn.get('merchant_id'):
                cursor.execute("""
                    SELECT * FROM service_routing
                    WHERE merchant_id = %s AND service_type = 'PAYOUT' AND is_active = TRUE
                """, (txn['merchant_id'],))
                
                routing = cursor.fetchone()
                if routing:
                    print("Service Routing (Merchant Specific):")
                    print(f"  PG Partner: {routing['pg_partner']}")
                    print(f"  Priority: {routing['priority']}")
                    print(f"  Routing Type: {routing['routing_type']}")
                    print()
                else:
                    # Check ALL_USERS routing
                    cursor.execute("""
                        SELECT * FROM service_routing
                        WHERE service_type = 'PAYOUT' AND routing_type = 'ALL_USERS' AND is_active = TRUE
                    """)
                    
                    routing = cursor.fetchone()
                    if routing:
                        print("Service Routing (All Users):")
                        print(f"  PG Partner: {routing['pg_partner']}")
                        print(f"  Priority: {routing['priority']}")
                        print()
            
            print("=" * 80)
            print("Diagnosis:")
            print("=" * 80)
            
            if txn.get('error_message'):
                error_msg = txn['error_message']
                if 'Expecting value' in error_msg:
                    print("❌ PayTouch API returned empty or invalid JSON response")
                    print()
                    print("Possible causes:")
                    print("1. PayTouch API endpoint is incorrect")
                    print("2. PayTouch token is invalid or expired")
                    print("3. PayTouch API is down or unreachable")
                    print("4. Request payload is malformed")
                    print("5. Network/firewall blocking the request")
                    print()
                    print("Recommended actions:")
                    print("1. Check PayTouch API logs in backend")
                    print("2. Verify PAYTOUCH_BASE_URL and PAYTOUCH_TOKEN in .env")
                    print("3. Test PayTouch API manually with curl")
                    print("4. Contact PayTouch support")
                else:
                    print(f"Error: {error_msg}")
            
            print()
            
    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_paytouch_error.py <txn_id>")
        print("Example: python diagnose_paytouch_error.py TXN8208D22ACC18")
        sys.exit(1)
    
    txn_id = sys.argv[1]
    diagnose_transaction(txn_id)
