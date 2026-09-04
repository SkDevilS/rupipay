#!/usr/bin/env python3
"""
Diagnose balance inconsistency issue
Check for multiple instances, replication lag, or caching
"""

import sys
sys.path.insert(0, '/home/ubuntu/moneyone_backend/backend')

from database import get_db_connection
import time

def check_balance_consistency(merchant_id='9000000001'):
    """Check if balance is consistent across multiple reads"""
    print(f"Checking balance consistency for merchant: {merchant_id}")
    print("=" * 60)
    
    balances = []
    
    # Read balance 10 times with small delays
    for i in range(10):
        conn = get_db_connection()
        if not conn:
            print(f"❌ Connection {i+1} failed")
            continue
            
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        settled_balance, 
                        unsettled_balance,
                        balance as old_balance
                    FROM merchant_wallet
                    WHERE merchant_id = %s
                """, (merchant_id,))
                result = cursor.fetchone()
                
                if result:
                    settled = float(result['settled_balance'])
                    unsettled = float(result['unsettled_balance'])
                    old = float(result['old_balance'])
                    
                    balances.append({
                        'read': i+1,
                        'settled': settled,
                        'unsettled': unsettled,
                        'old': old
                    })
                    
                    print(f"Read {i+1}: Settled=₹{settled:.2f}, Unsettled=₹{unsettled:.2f}, Old=₹{old:.2f}")
                else:
                    print(f"❌ No wallet found for merchant {merchant_id}")
                    
            conn.close()
            time.sleep(0.1)  # Small delay between reads
            
        except Exception as e:
            print(f"❌ Error on read {i+1}: {e}")
            conn.close()
    
    # Analyze results
    print("\n" + "=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    
    if not balances:
        print("❌ No successful reads")
        return
    
    # Check if all values are the same
    settled_values = set(b['settled'] for b in balances)
    unsettled_values = set(b['unsettled'] for b in balances)
    
    if len(settled_values) == 1:
        print(f"✅ Settled balance is CONSISTENT: ₹{balances[0]['settled']:.2f}")
    else:
        print(f"❌ Settled balance is INCONSISTENT!")
        print(f"   Found {len(settled_values)} different values: {sorted(settled_values)}")
        print(f"   This indicates: Database replication lag or multiple instances")
    
    if len(unsettled_values) == 1:
        print(f"✅ Unsettled balance is CONSISTENT: ₹{balances[0]['unsettled']:.2f}")
    else:
        print(f"❌ Unsettled balance is INCONSISTENT!")
        print(f"   Found {len(unsettled_values)} different values: {sorted(unsettled_values)}")

def check_database_replication():
    """Check if database has replication enabled"""
    print("\n" + "=" * 60)
    print("CHECKING DATABASE REPLICATION:")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check if this is a replica
            cursor.execute("SHOW SLAVE STATUS")
            slave_status = cursor.fetchone()
            
            if slave_status:
                print("⚠️  This is a REPLICA database!")
                print(f"   Master Host: {slave_status.get('Master_Host', 'N/A')}")
                print(f"   Seconds Behind Master: {slave_status.get('Seconds_Behind_Master', 'N/A')}")
                print("\n   SOLUTION: Always read from MASTER for wallet balance")
            else:
                print("✅ This is a MASTER database (no replication)")
            
            # Check transaction isolation level
            cursor.execute("SELECT @@session.tx_isolation as isolation")
            isolation = cursor.fetchone()
            print(f"\n✅ Transaction Isolation: {isolation['isolation']}")
            
            # Check if autocommit is on
            cursor.execute("SELECT @@autocommit as autocommit")
            autocommit = cursor.fetchone()
            print(f"✅ Autocommit: {autocommit['autocommit']}")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking replication: {e}")
        conn.close()

def check_recent_transactions(merchant_id='9000000001'):
    """Check recent wallet transactions"""
    print("\n" + "=" * 60)
    print("RECENT WALLET TRANSACTIONS:")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    txn_id,
                    txn_type,
                    amount,
                    balance_before,
                    balance_after,
                    description,
                    created_at
                FROM merchant_wallet_transactions
                WHERE merchant_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (merchant_id,))
            
            transactions = cursor.fetchall()
            
            if transactions:
                for txn in transactions:
                    print(f"\n{txn['created_at']} | {txn['txn_type']}")
                    print(f"  Amount: ₹{txn['amount']:.2f}")
                    print(f"  Before: ₹{txn['balance_before']:.2f} → After: ₹{txn['balance_after']:.2f}")
                    print(f"  Desc: {txn['description']}")
            else:
                print("No transactions found")
                
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.close()

if __name__ == "__main__":
    merchant_id = sys.argv[1] if len(sys.argv) > 1 else '9000000001'
    
    check_balance_consistency(merchant_id)
    check_database_replication()
    check_recent_transactions(merchant_id)
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)
