"""
Test API Ledger endpoint for VIYONAPAY_BARRINGER to diagnose the error
"""
import sys
sys.path.insert(0, '/var/www/moneyone/moneyone/backend')

from database import get_db_connection

def test_viyonapay_barringer_query():
    """Test the VIYONAPAY_BARRINGER query"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Test the exact query used in the API
            query = """
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as total_amount,
                    COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN (amount - charges) ELSE 0 END), 0) as total_net_amount
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY' 
                AND txn_id LIKE 'VY_BAR_%'
                AND DATE(created_at) = CURDATE()
            """
            
            print("\n" + "="*100)
            print("Testing VIYONAPAY_BARRINGER Query")
            print("="*100)
            print("\nQuery:")
            print(query)
            print("\nExecuting...")
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            print("\n✅ Query executed successfully!")
            print("\nResults:")
            print(f"  Total Transactions: {result['total_transactions']}")
            print(f"  Success Count: {result['success_count']}")
            print(f"  Total Amount: ₹{result['total_amount']}")
            print(f"  Total Net Amount: ₹{result['total_net_amount']}")
            
            # Also check if there are any VY_BAR_ transactions
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY' 
                AND txn_id LIKE 'VY_BAR_%'
            """)
            
            bar_count = cursor.fetchone()
            print(f"\n📊 Total VY_BAR_ transactions in database: {bar_count['count']}")
            
            # Check for any transactions today
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY' 
                AND txn_id LIKE 'VY_BAR_%'
                AND DATE(created_at) = CURDATE()
            """)
            
            today_count = cursor.fetchone()
            print(f"📊 VY_BAR_ transactions today: {today_count['count']}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    test_viyonapay_barringer_query()
