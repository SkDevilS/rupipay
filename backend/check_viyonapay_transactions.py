"""
Check VIYONAPAY transactions to identify patterns for differentiation
"""
import sys
sys.path.insert(0, '/var/www/moneyone/moneyone/backend')

from database import get_db_connection

def check_viyonapay_transactions():
    """Check VIYONAPAY transactions and their routing"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get sample VIYONAPAY transactions with merchant routing info
            cursor.execute("""
                SELECT 
                    t.txn_id,
                    t.merchant_id,
                    t.pg_txn_id,
                    t.created_at,
                    t.status,
                    sr.pg_partner as routed_to,
                    m.full_name as merchant_name
                FROM payin_transactions t
                LEFT JOIN service_routing sr ON t.merchant_id = sr.merchant_id 
                    AND sr.service_type = 'PAYIN' 
                    AND sr.is_active = TRUE
                LEFT JOIN merchants m ON t.merchant_id = m.merchant_id
                WHERE t.pg_partner = 'VIYONAPAY'
                ORDER BY t.created_at DESC
                LIMIT 20
            """)
            
            transactions = cursor.fetchall()
            
            print("\n" + "="*100)
            print("VIYONAPAY TRANSACTIONS ANALYSIS")
            print("="*100)
            
            if not transactions:
                print("\n❌ No VIYONAPAY transactions found")
                return
            
            print(f"\nFound {len(transactions)} recent VIYONAPAY transactions:\n")
            
            for txn in transactions:
                print(f"Transaction ID: {txn['txn_id']}")
                print(f"  Merchant: {txn['merchant_name']} ({txn['merchant_id']})")
                print(f"  Routed To: {txn['routed_to']}")
                print(f"  PG Txn ID: {txn['pg_txn_id']}")
                print(f"  Status: {txn['status']}")
                print(f"  Created: {txn['created_at']}")
                print()
            
            # Check service routing for VIYONAPAY
            print("\n" + "="*100)
            print("SERVICE ROUTING CONFIGURATION")
            print("="*100 + "\n")
            
            cursor.execute("""
                SELECT 
                    sr.id,
                    sr.merchant_id,
                    m.full_name as merchant_name,
                    sr.pg_partner,
                    sr.routing_type,
                    sr.is_active,
                    sr.created_at
                FROM service_routing sr
                LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
                WHERE sr.pg_partner IN ('VIYONAPAY', 'VIYONAPAY_BARRINGER')
                AND sr.service_type = 'PAYIN'
                ORDER BY sr.pg_partner, sr.merchant_id
            """)
            
            routes = cursor.fetchall()
            
            if routes:
                print("VIYONAPAY Routing Configuration:\n")
                for route in routes:
                    print(f"Config: {route['pg_partner']}")
                    print(f"  Merchant: {route['merchant_name']} ({route['merchant_id']})")
                    print(f"  Type: {route['routing_type']}")
                    print(f"  Active: {route['is_active']}")
                    print(f"  Created: {route['created_at']}")
                    print()
            else:
                print("❌ No VIYONAPAY routing configuration found")
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_viyonapay_transactions()
