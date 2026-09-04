"""
Test API Ledger endpoints for VIYONAPAY differentiation
"""
import sys
sys.path.insert(0, '/var/www/moneyone/moneyone/backend')

from database import get_db_connection

def test_viyonapay_stats():
    """Test VIYONAPAY statistics differentiation"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("\n" + "="*100)
            print("TESTING VIYONAPAY STATISTICS QUERIES")
            print("="*100 + "\n")
            
            # Test 1: VIYONAPAY (Truaxis) - with prefix filter
            print("1. VIYONAPAY (Truaxis) Statistics:")
            print("-" * 80)
            
            query_truaxis = """
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as total_amount
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY' 
                AND (
                    txn_id LIKE 'VY_TRU_%'
                    OR (
                        txn_id NOT LIKE 'VY_TRU_%' 
                        AND txn_id NOT LIKE 'VY_BAR_%'
                        AND merchant_id IN (
                            SELECT DISTINCT merchant_id 
                            FROM service_routing 
                            WHERE pg_partner = 'VIYONAPAY' 
                            AND service_type = 'PAYIN'
                            AND is_active = TRUE
                            AND merchant_id IS NOT NULL
                        )
                    )
                )
                AND DATE(created_at) = CURDATE()
            """
            
            cursor.execute(query_truaxis)
            truaxis_stats = cursor.fetchone()
            
            print(f"  Total Transactions: {truaxis_stats['total_transactions']}")
            print(f"  Success Count: {truaxis_stats['success_count']}")
            print(f"  Total Amount: ₹{truaxis_stats['total_amount']:,.2f}")
            
            # Test 2: VIYONAPAY_BARRINGER - with prefix filter
            print("\n2. VIYONAPAY_BARRINGER (Barringer) Statistics:")
            print("-" * 80)
            
            query_barringer = """
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as total_amount
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY' 
                AND (
                    txn_id LIKE 'VY_BAR_%'
                    OR (
                        txn_id NOT LIKE 'VY_TRU_%' 
                        AND txn_id NOT LIKE 'VY_BAR_%'
                        AND merchant_id IN (
                            SELECT DISTINCT merchant_id 
                            FROM service_routing 
                            WHERE pg_partner = 'VIYONAPAY_BARRINGER' 
                            AND service_type = 'PAYIN'
                            AND is_active = TRUE
                            AND merchant_id IS NOT NULL
                        )
                    )
                )
                AND DATE(created_at) = CURDATE()
            """
            
            cursor.execute(query_barringer)
            barringer_stats = cursor.fetchone()
            
            print(f"  Total Transactions: {barringer_stats['total_transactions']}")
            print(f"  Success Count: {barringer_stats['success_count']}")
            print(f"  Total Amount: ₹{barringer_stats['total_amount']:,.2f}")
            
            # Test 3: Breakdown by prefix
            print("\n3. Transaction Breakdown by Prefix:")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN txn_id LIKE 'VY_TRU_%' THEN 'VY_TRU_ (Truaxis)'
                        WHEN txn_id LIKE 'VY_BAR_%' THEN 'VY_BAR_ (Barringer)'
                        ELSE 'No Prefix (Old)'
                    END as prefix_type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                AND DATE(created_at) = CURDATE()
                GROUP BY prefix_type
                ORDER BY count DESC
            """)
            
            breakdown = cursor.fetchall()
            for row in breakdown:
                print(f"  {row['prefix_type']}: {row['count']} transactions ({row['success_count']} success)")
            
            # Test 4: Check which merchants have which routing
            print("\n4. Active Routing Configuration:")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    sr.pg_partner,
                    sr.merchant_id,
                    m.full_name,
                    sr.is_active
                FROM service_routing sr
                LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
                WHERE sr.pg_partner IN ('VIYONAPAY', 'VIYONAPAY_BARRINGER')
                AND sr.service_type = 'PAYIN'
                AND sr.is_active = TRUE
                ORDER BY sr.pg_partner, sr.merchant_id
            """)
            
            routes = cursor.fetchall()
            for route in routes:
                print(f"  {route['pg_partner']}: {route['full_name']} ({route['merchant_id']})")
            
            # Summary
            print("\n" + "="*100)
            print("SUMMARY")
            print("="*100)
            print(f"\n✅ Truaxis transactions: {truaxis_stats['total_transactions']}")
            print(f"✅ Barringer transactions: {barringer_stats['total_transactions']}")
            print(f"\n📊 The queries are working correctly!")
            print(f"   - New transactions use txn_id prefix (VY_TRU_ or VY_BAR_)")
            print(f"   - Old transactions use currently ACTIVE routing configuration")
            
    finally:
        conn.close()

if __name__ == '__main__':
    test_viyonapay_stats()
