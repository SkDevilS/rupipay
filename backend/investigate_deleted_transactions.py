#!/usr/bin/env python3
"""
Investigate why transactions are being deleted from database
"""

from database import get_db_connection
from datetime import datetime, timedelta

def check_for_delete_operations():
    """Check for any DELETE operations in the codebase"""
    print("=" * 80)
    print("INVESTIGATING TRANSACTION DELETION")
    print("=" * 80)
    
    # Check database for recent deletions (if binary logging is enabled)
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check if there are any foreign key constraints that could cascade delete
            cursor.execute("""
                SELECT 
                    TABLE_NAME,
                    CONSTRAINT_NAME,
                    REFERENCED_TABLE_NAME,
                    DELETE_RULE
                FROM information_schema.REFERENTIAL_CONSTRAINTS
                WHERE CONSTRAINT_SCHEMA = DATABASE()
                AND TABLE_NAME = 'payout_transactions'
            """)
            fk_constraints = cursor.fetchall()
            
            if fk_constraints:
                print("\n⚠️  FOREIGN KEY CONSTRAINTS ON payout_transactions:")
                for fk in fk_constraints:
                    print(f"  Constraint: {fk['CONSTRAINT_NAME']}")
                    print(f"  References: {fk['REFERENCED_TABLE_NAME']}")
                    print(f"  On Delete: {fk['DELETE_RULE']}")
                    if fk['DELETE_RULE'] == 'CASCADE':
                        print(f"  ⚠️  CASCADE DELETE ENABLED - Deleting {fk['REFERENCED_TABLE_NAME']} will delete payouts!")
                    print()
            else:
                print("\n✅ No foreign key constraints with CASCADE delete")
            
            # Check for any triggers that might delete data
            cursor.execute("""
                SELECT 
                    TRIGGER_NAME,
                    EVENT_MANIPULATION,
                    ACTION_STATEMENT,
                    ACTION_TIMING
                FROM information_schema.TRIGGERS
                WHERE EVENT_OBJECT_SCHEMA = DATABASE()
                AND (EVENT_OBJECT_TABLE = 'payout_transactions' 
                     OR ACTION_STATEMENT LIKE '%payout_transactions%')
            """)
            triggers = cursor.fetchall()
            
            if triggers:
                print("\n⚠️  TRIGGERS THAT AFFECT payout_transactions:")
                for trigger in triggers:
                    print(f"  Trigger: {trigger['TRIGGER_NAME']}")
                    print(f"  Event: {trigger['EVENT_MANIPULATION']}")
                    print(f"  Timing: {trigger['ACTION_TIMING']}")
                    print(f"  Action: {trigger['ACTION_STATEMENT'][:200]}...")
                    print()
            else:
                print("\n✅ No triggers affecting payout_transactions")
            
            # Check for scheduled events that might delete data
            cursor.execute("""
                SELECT 
                    EVENT_NAME,
                    EVENT_DEFINITION,
                    INTERVAL_VALUE,
                    INTERVAL_FIELD,
                    STATUS
                FROM information_schema.EVENTS
                WHERE EVENT_SCHEMA = DATABASE()
                AND EVENT_DEFINITION LIKE '%payout_transactions%'
            """)
            events = cursor.fetchall()
            
            if events:
                print("\n⚠️  SCHEDULED EVENTS THAT AFFECT payout_transactions:")
                for event in events:
                    print(f"  Event: {event['EVENT_NAME']}")
                    print(f"  Status: {event['STATUS']}")
                    print(f"  Interval: Every {event['INTERVAL_VALUE']} {event['INTERVAL_FIELD']}")
                    print(f"  Definition: {event['EVENT_DEFINITION'][:200]}...")
                    print()
            else:
                print("\n✅ No scheduled events affecting payout_transactions")
            
            # Check transaction log for recent activity
            print("\n" + "=" * 80)
            print("CHECKING FOR UNCOMMITTED TRANSACTIONS")
            print("=" * 80)
            
            cursor.execute("""
                SELECT 
                    trx_id,
                    trx_state,
                    trx_started,
                    trx_query,
                    trx_operation_state,
                    trx_tables_in_use,
                    trx_tables_locked
                FROM information_schema.INNODB_TRX
            """)
            active_trx = cursor.fetchall()
            
            if active_trx:
                print(f"\n⚠️  Found {len(active_trx)} active transactions:")
                for trx in active_trx:
                    print(f"  Transaction ID: {trx['trx_id']}")
                    print(f"  State: {trx['trx_state']}")
                    print(f"  Started: {trx['trx_started']}")
                    print(f"  Query: {trx['trx_query']}")
                    print()
            else:
                print("\n✅ No active uncommitted transactions")
            
            # Check for connection issues
            print("\n" + "=" * 80)
            print("CHECKING DATABASE CONNECTION SETTINGS")
            print("=" * 80)
            
            cursor.execute("SHOW VARIABLES LIKE 'wait_timeout'")
            wait_timeout = cursor.fetchone()
            print(f"\nWait Timeout: {wait_timeout['Value']} seconds")
            
            cursor.execute("SHOW VARIABLES LIKE 'interactive_timeout'")
            interactive_timeout = cursor.fetchone()
            print(f"Interactive Timeout: {interactive_timeout['Value']} seconds")
            
            cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
            max_conn = cursor.fetchone()
            print(f"Max Connections: {max_conn['Value']}")
            
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            threads = cursor.fetchone()
            print(f"Current Connections: {threads['Value']}")
            
            # Check for table corruption
            print("\n" + "=" * 80)
            print("CHECKING TABLE INTEGRITY")
            print("=" * 80)
            
            cursor.execute("CHECK TABLE payout_transactions")
            check_result = cursor.fetchone()
            print(f"\nTable Check: {check_result['Msg_text']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def check_wallet_consistency():
    """Check if wallet was debited but payout record is missing"""
    print("\n" + "=" * 80)
    print("CHECKING WALLET DEBIT WITHOUT PAYOUT RECORD")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Find wallet debits in last 24 hours without corresponding payout
            cursor.execute("""
                SELECT 
                    mwt.id,
                    mwt.merchant_id,
                    mwt.txn_id,
                    mwt.amount,
                    mwt.description,
                    mwt.created_at,
                    COUNT(pt.id) as payout_count
                FROM merchant_wallet_transactions mwt
                LEFT JOIN payout_transactions pt ON (
                    mwt.merchant_id = pt.merchant_id
                    AND mwt.created_at BETWEEN pt.created_at - INTERVAL 10 SECOND 
                                            AND pt.created_at + INTERVAL 10 SECOND
                )
                WHERE mwt.txn_type = 'DEBIT'
                AND mwt.description LIKE '%Payout%'
                AND mwt.created_at >= NOW() - INTERVAL 24 HOUR
                GROUP BY mwt.id
                HAVING payout_count = 0
                ORDER BY mwt.created_at DESC
            """)
            
            orphaned_debits = cursor.fetchall()
            
            if orphaned_debits:
                print(f"\n⚠️  CRITICAL: Found {len(orphaned_debits)} wallet debits WITHOUT payout records!")
                print("This means money was deducted but payout record was deleted!\n")
                
                for debit in orphaned_debits:
                    print(f"Merchant: {debit['merchant_id']}")
                    print(f"Amount Debited: ₹{debit['amount']:.2f}")
                    print(f"Description: {debit['description']}")
                    print(f"Time: {debit['created_at']}")
                    print("-" * 80)
                
                print(f"\n💡 RECOMMENDATION:")
                print(f"These wallet debits indicate payouts were initiated but records were deleted.")
                print(f"This is a CRITICAL DATA LOSS issue that needs immediate attention!")
            else:
                print("\n✅ All wallet debits have corresponding payout records")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TRANSACTION DELETION INVESTIGATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    check_for_delete_operations()
    check_wallet_consistency()
    
    print("\n" + "=" * 80)
    print("INVESTIGATION COMPLETE")
    print("=" * 80)
    
    print("\n📋 NEXT STEPS:")
    print("1. Check application logs for any DELETE queries")
    print("2. Check if any cleanup scripts are running")
    print("3. Enable MySQL general query log to track all queries")
    print("4. Check if load balancer is routing to wrong database")
    print("5. Verify no one has direct database access deleting records")
