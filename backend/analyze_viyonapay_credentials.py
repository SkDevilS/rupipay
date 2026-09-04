"""
Analyze VIYONAPAY transactions to determine which credential was used
"""
import sys
sys.path.insert(0, '/var/www/moneyone/moneyone/backend')

from database import get_db_connection

def analyze_credentials():
    """Analyze which credentials were used for VIYONAPAY transactions"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get transactions without prefix (older transactions)
            cursor.execute("""
                SELECT 
                    t.txn_id,
                    t.merchant_id,
                    t.created_at,
                    t.status,
                    m.full_name as merchant_name
                FROM payin_transactions t
                LEFT JOIN merchants m ON t.merchant_id = m.merchant_id
                WHERE t.pg_partner = 'VIYONAPAY'
                AND t.txn_id NOT LIKE 'VY_TRU_%'
                AND t.txn_id NOT LIKE 'VY_BAR_%'
                ORDER BY t.created_at DESC
                LIMIT 50
            """)
            
            old_transactions = cursor.fetchall()
            
            print("\n" + "="*100)
            print("OLDER VIYONAPAY TRANSACTIONS (WITHOUT PREFIX)")
            print("="*100 + "\n")
            
            if not old_transactions:
                print("✅ No old transactions found - all transactions have prefixes!")
                return
            
            print(f"Found {len(old_transactions)} transactions without prefix:\n")
            
            # Group by merchant
            merchant_txns = {}
            for txn in old_transactions:
                merchant_id = txn['merchant_id']
                if merchant_id not in merchant_txns:
                    merchant_txns[merchant_id] = []
                merchant_txns[merchant_id].append(txn)
            
            # For each merchant, check their current and historical routing
            for merchant_id, txns in merchant_txns.items():
                merchant_name = txns[0]['merchant_name']
                print(f"\n{'='*80}")
                print(f"Merchant: {merchant_name} ({merchant_id})")
                print(f"{'='*80}")
                
                # Check current routing
                cursor.execute("""
                    SELECT pg_partner, is_active, created_at, updated_at
                    FROM service_routing
                    WHERE merchant_id = %s
                    AND service_type = 'PAYIN'
                    AND pg_partner IN ('VIYONAPAY', 'VIYONAPAY_BARRINGER')
                    ORDER BY created_at DESC
                """, (merchant_id,))
                
                routes = cursor.fetchall()
                
                if routes:
                    print(f"\nRouting Configuration:")
                    for route in routes:
                        status = "✅ ACTIVE" if route['is_active'] else "❌ INACTIVE"
                        print(f"  • {route['pg_partner']} - {status}")
                        print(f"    Created: {route['created_at']}")
                        if route['updated_at']:
                            print(f"    Updated: {route['updated_at']}")
                else:
                    print("\n⚠️  No routing configuration found")
                
                # Show sample transactions
                print(f"\nSample Transactions ({len(txns)} total):")
                for i, txn in enumerate(txns[:5], 1):
                    print(f"  {i}. {txn['txn_id']}")
                    print(f"     Date: {txn['created_at']}")
                    print(f"     Status: {txn['status']}")
                
                if len(txns) > 5:
                    print(f"  ... and {len(txns) - 5} more")
            
            # Summary
            print("\n" + "="*100)
            print("ANALYSIS SUMMARY")
            print("="*100 + "\n")
            
            print(f"Total merchants with old transactions: {len(merchant_txns)}")
            print(f"Total old transactions: {len(old_transactions)}")
            
            # Check if we can determine credential from routing history
            print("\n📊 Credential Determination Strategy:")
            print("  1. Transactions WITH prefix (VY_TRU_ or VY_BAR_) → Use prefix")
            print("  2. Transactions WITHOUT prefix → Check service_routing for that merchant")
            print("     - If merchant has VIYONAPAY routing → Assign to Truaxis")
            print("     - If merchant has VIYONAPAY_BARRINGER routing → Assign to Barringer")
            print("     - If merchant has both → Use the ACTIVE one")
            
    finally:
        conn.close()

if __name__ == '__main__':
    analyze_credentials()
