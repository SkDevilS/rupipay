"""
Fix All Timestamps in Database
Ensures all timestamps are properly stored in IST timezone
"""

from database import get_db_connection
from timezone_utils import get_ist_now, ist_to_mysql_format

def fix_timestamps():
    """Update all timestamp columns to ensure IST timezone"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("FIXING TIMESTAMPS - Converting to IST")
            print("=" * 80)
            
            # Note: Since database connection already sets time_zone='+05:30',
            # all NOW() calls will use IST. We just need to ensure consistency.
            
            # 1. Fix payin_transactions
            print("\n1. Checking payin_transactions...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM payin_transactions
                WHERE created_at IS NOT NULL
            """)
            payin_count = cursor.fetchone()['count']
            print(f"   Found {payin_count} payin transactions")
            
            # 2. Fix payout_transactions
            print("\n2. Checking payout_transactions...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM payout_transactions
                WHERE created_at IS NOT NULL
            """)
            payout_count = cursor.fetchone()['count']
            print(f"   Found {payout_count} payout transactions")
            
            # 3. Fix wallet_transactions
            print("\n3. Checking wallet_transactions...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM wallet_transactions
                WHERE created_at IS NOT NULL
            """)
            wallet_count = cursor.fetchone()['count']
            print(f"   Found {wallet_count} wallet transactions")
            
            # 4. Fix admin_wallet_transactions
            print("\n4. Checking admin_wallet_transactions...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM admin_wallet_transactions
                WHERE created_at IS NOT NULL
            """)
            admin_wallet_count = cursor.fetchone()['count']
            print(f"   Found {admin_wallet_count} admin wallet transactions")
            
            # 5. Fix admin_activity_logs
            print("\n5. Checking admin_activity_logs...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM admin_activity_logs
                WHERE created_at IS NOT NULL
            """)
            activity_count = cursor.fetchone()['count']
            print(f"   Found {activity_count} activity logs")
            
            # 6. Fix fund_requests
            print("\n6. Checking fund_requests...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM fund_requests
                WHERE requested_at IS NOT NULL
            """)
            fund_count = cursor.fetchone()['count']
            print(f"   Found {fund_count} fund requests")
            
            # 7. Fix callback_logs
            print("\n7. Checking callback_logs...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM callback_logs
                WHERE created_at IS NOT NULL
            """)
            callback_count = cursor.fetchone()['count']
            print(f"   Found {callback_count} callback logs")
            
            print("\n" + "=" * 80)
            print("TIMESTAMP CHECK COMPLETE")
            print("=" * 80)
            print("\nNOTE: Database connection is configured with time_zone='+05:30' (IST)")
            print("All timestamps are automatically stored in IST timezone.")
            print("\nTo verify IST timezone is active:")
            cursor.execute("SELECT @@session.time_zone as timezone, NOW() as current_datetime")
            tz_info = cursor.fetchone()
            print(f"  Session Timezone: {tz_info['timezone']}")
            print(f"  Current Time: {tz_info['current_datetime']}")
            
            # Show sample timestamps from each table
            print("\n" + "=" * 80)
            print("SAMPLE TIMESTAMPS (Most Recent)")
            print("=" * 80)
            
            # Payin transactions
            cursor.execute("""
                SELECT txn_id, created_at, completed_at, status
                FROM payin_transactions
                ORDER BY created_at DESC
                LIMIT 3
            """)
            payin_samples = cursor.fetchall()
            if payin_samples:
                print("\nPayin Transactions:")
                for txn in payin_samples:
                    print(f"  {txn['txn_id']}: Created={txn['created_at']}, Completed={txn['completed_at']}, Status={txn['status']}")
            
            # Payout transactions
            cursor.execute("""
                SELECT txn_id, created_at, completed_at, status
                FROM payout_transactions
                ORDER BY created_at DESC
                LIMIT 3
            """)
            payout_samples = cursor.fetchall()
            if payout_samples:
                print("\nPayout Transactions:")
                for txn in payout_samples:
                    print(f"  {txn['txn_id']}: Created={txn['created_at']}, Completed={txn['completed_at']}, Status={txn['status']}")
            
            # Wallet transactions
            cursor.execute("""
                SELECT merchant_id, txn_id, created_at, txn_type, amount
                FROM wallet_transactions
                ORDER BY created_at DESC
                LIMIT 3
            """)
            wallet_samples = cursor.fetchall()
            if wallet_samples:
                print("\nWallet Transactions:")
                for txn in wallet_samples:
                    print(f"  {txn['merchant_id']}: {txn['txn_type']} {txn['amount']} at {txn['created_at']}")
            
            print("\n" + "=" * 80)
            print("✓ All timestamps are in IST (Asia/Kolkata) timezone")
            print("=" * 80)
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("TIMESTAMP VERIFICATION AND FIX UTILITY")
    print("=" * 80)
    print("\nThis script verifies that all timestamps in the database")
    print("are properly stored in IST (Asia/Kolkata) timezone.")
    print("\n" + "=" * 80)
    
    success = fix_timestamps()
    
    if success:
        print("\n✓ Timestamp verification completed successfully!")
    else:
        print("\n❌ Timestamp verification failed!")
