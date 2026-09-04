#!/usr/bin/env python3
"""
Diagnose Payout Data Disappearance Issue
Checks for:
1. Data actually exists in database
2. Transaction isolation issues
3. Connection pooling problems
4. Any filtering logic hiding data
5. Rollback scenarios
"""

import sys
from database import get_db_connection
from datetime import datetime, timedelta

def check_payout_data_exists():
    """Check if payout data actually exists in database"""
    print("=" * 80)
    print("CHECKING PAYOUT DATA IN DATABASE")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check total payout records
            cursor.execute("SELECT COUNT(*) as total FROM payout_transactions")
            total = cursor.fetchone()
            print(f"\n📊 Total Payout Records: {total['total']}")
            
            # Check recent payouts (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) as recent_count
                FROM payout_transactions
                WHERE created_at >= NOW() - INTERVAL 24 HOUR
            """)
            recent = cursor.fetchone()
            print(f"📊 Payouts in Last 24 Hours: {recent['recent_count']}")
            
            # Check payouts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM payout_transactions
                GROUP BY status
            """)
            status_counts = cursor.fetchall()
            print(f"\n📊 Payouts by Status:")
            for row in status_counts:
                print(f"   {row['status']}: {row['count']}")
            
            # Check most recent payouts
            cursor.execute("""
                SELECT 
                    txn_id,
                    merchant_id,
                    order_id,
                    amount,
                    status,
                    created_at,
                    updated_at
                FROM payout_transactions
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent_payouts = cursor.fetchall()
            
            print(f"\n📋 Last 10 Payout Transactions:")
            print("-" * 80)
            for payout in recent_payouts:
                print(f"TXN ID: {payout['txn_id']}")
                print(f"Merchant: {payout['merchant_id']}")
                print(f"Order ID: {payout['order_id']}")
                print(f"Amount: ₹{payout['amount']:.2f}")
                print(f"Status: {payout['status']}")
                print(f"Created: {payout['created_at']}")
                print(f"Updated: {payout['updated_at']}")
                print("-" * 80)
            
            # Check for any NULL or problematic data
            cursor.execute("""
                SELECT COUNT(*) as null_merchant_count
                FROM payout_transactions
                WHERE merchant_id IS NULL OR merchant_id = ''
            """)
            null_merchant = cursor.fetchone()
            print(f"\n⚠️  Payouts with NULL/Empty Merchant ID: {null_merchant['null_merchant_count']}")
            
            # Check for orphaned records (merchant doesn't exist)
            cursor.execute("""
                SELECT COUNT(*) as orphaned_count
                FROM payout_transactions pt
                LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                WHERE m.merchant_id IS NULL
            """)
            orphaned = cursor.fetchone()
            print(f"⚠️  Orphaned Payout Records: {orphaned['orphaned_count']}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking payout data: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_transaction_isolation():
    """Check transaction isolation level and autocommit settings"""
    print("\n" + "=" * 80)
    print("CHECKING TRANSACTION ISOLATION SETTINGS")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check isolation level
            cursor.execute("SELECT @@transaction_isolation")
            isolation = cursor.fetchone()
            print(f"\n🔒 Transaction Isolation Level: {list(isolation.values())[0]}")
            
            # Check autocommit
            cursor.execute("SELECT @@autocommit")
            autocommit = cursor.fetchone()
            print(f"🔒 Autocommit: {list(autocommit.values())[0]}")
            
            # Check for any locks on payout_transactions table
            cursor.execute("""
                SELECT * FROM information_schema.INNODB_LOCKS
                WHERE lock_table LIKE '%payout_transactions%'
            """)
            locks = cursor.fetchall()
            if locks:
                print(f"\n⚠️  Active Locks on payout_transactions: {len(locks)}")
                for lock in locks:
                    print(f"   {lock}")
            else:
                print(f"\n✅ No active locks on payout_transactions table")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking transaction settings: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_specific_merchant_payouts(merchant_id=None):
    """Check payouts for a specific merchant"""
    print("\n" + "=" * 80)
    print("CHECKING MERCHANT-SPECIFIC PAYOUT DATA")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            if merchant_id:
                query = """
                    SELECT 
                        txn_id,
                        merchant_id,
                        order_id,
                        amount,
                        charge_amount,
                        net_amount,
                        status,
                        created_at,
                        updated_at,
                        completed_at
                    FROM payout_transactions
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                    LIMIT 20
                """
                cursor.execute(query, (merchant_id,))
            else:
                # Get all merchants with recent payouts
                cursor.execute("""
                    SELECT 
                        merchant_id,
                        COUNT(*) as payout_count,
                        MAX(created_at) as last_payout
                    FROM payout_transactions
                    WHERE created_at >= NOW() - INTERVAL 7 DAY
                    GROUP BY merchant_id
                    ORDER BY last_payout DESC
                """)
                merchants = cursor.fetchall()
                
                print(f"\n📊 Merchants with Payouts in Last 7 Days:")
                for merchant in merchants:
                    print(f"   Merchant: {merchant['merchant_id']}")
                    print(f"   Payout Count: {merchant['payout_count']}")
                    print(f"   Last Payout: {merchant['last_payout']}")
                    print("-" * 40)
                
                conn.close()
                return True
            
            payouts = cursor.fetchall()
            
            if payouts:
                print(f"\n📋 Payouts for Merchant {merchant_id}:")
                print("-" * 80)
                for payout in payouts:
                    print(f"TXN ID: {payout['txn_id']}")
                    print(f"Order ID: {payout['order_id']}")
                    print(f"Amount: ₹{payout['amount']:.2f}")
                    print(f"Charge: ₹{payout['charge_amount']:.2f}")
                    print(f"Net: ₹{payout['net_amount']:.2f}")
                    print(f"Status: {payout['status']}")
                    print(f"Created: {payout['created_at']}")
                    print(f"Updated: {payout['updated_at']}")
                    print(f"Completed: {payout['completed_at']}")
                    print("-" * 80)
            else:
                print(f"\n⚠️  No payouts found for merchant {merchant_id}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking merchant payouts: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_wallet_transactions():
    """Check if wallet debits are recorded but payout records are missing"""
    print("\n" + "=" * 80)
    print("CHECKING WALLET TRANSACTIONS VS PAYOUT RECORDS")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check recent wallet debits for payouts
            cursor.execute("""
                SELECT 
                    merchant_id,
                    txn_id,
                    amount,
                    description,
                    created_at
                FROM merchant_wallet_transactions
                WHERE txn_type = 'DEBIT'
                AND description LIKE '%Payout%'
                AND created_at >= NOW() - INTERVAL 24 HOUR
                ORDER BY created_at DESC
                LIMIT 20
            """)
            wallet_debits = cursor.fetchall()
            
            print(f"\n📊 Recent Wallet Debits for Payouts (Last 24 Hours):")
            print("-" * 80)
            
            for debit in wallet_debits:
                print(f"Merchant: {debit['merchant_id']}")
                print(f"TXN ID: {debit['txn_id']}")
                print(f"Amount: ₹{debit['amount']:.2f}")
                print(f"Description: {debit['description']}")
                print(f"Created: {debit['created_at']}")
                
                # Check if corresponding payout record exists
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM payout_transactions
                    WHERE merchant_id = %s
                    AND created_at BETWEEN %s - INTERVAL 5 SECOND AND %s + INTERVAL 5 SECOND
                """, (debit['merchant_id'], debit['created_at'], debit['created_at']))
                
                payout_exists = cursor.fetchone()
                if payout_exists['count'] > 0:
                    print(f"✅ Corresponding payout record EXISTS")
                else:
                    print(f"❌ Corresponding payout record MISSING!")
                
                print("-" * 80)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking wallet transactions: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database_triggers():
    """Check for any database triggers that might affect payout data"""
    print("\n" + "=" * 80)
    print("CHECKING DATABASE TRIGGERS")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    TRIGGER_NAME,
                    EVENT_MANIPULATION,
                    EVENT_OBJECT_TABLE,
                    ACTION_STATEMENT,
                    ACTION_TIMING
                FROM information_schema.TRIGGERS
                WHERE EVENT_OBJECT_TABLE = 'payout_transactions'
            """)
            triggers = cursor.fetchall()
            
            if triggers:
                print(f"\n⚠️  Found {len(triggers)} triggers on payout_transactions:")
                for trigger in triggers:
                    print(f"\nTrigger: {trigger['TRIGGER_NAME']}")
                    print(f"Event: {trigger['EVENT_MANIPULATION']}")
                    print(f"Timing: {trigger['ACTION_TIMING']}")
                    print(f"Action: {trigger['ACTION_STATEMENT']}")
            else:
                print(f"\n✅ No triggers found on payout_transactions table")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking triggers: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PAYOUT DATA DISAPPEARANCE DIAGNOSTIC TOOL")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Run all diagnostic checks
    check_payout_data_exists()
    check_transaction_isolation()
    check_wallet_transactions()
    check_database_triggers()
    
    # Check specific merchant if provided
    if len(sys.argv) > 1:
        merchant_id = sys.argv[1]
        check_specific_merchant_payouts(merchant_id)
    else:
        check_specific_merchant_payouts()
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
