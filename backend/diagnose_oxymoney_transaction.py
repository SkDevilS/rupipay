#!/usr/bin/env python3
"""
Diagnose Oxymoney Transaction
Check why VPA usage is not being recorded for successful transactions
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def diagnose_transaction():
    """Diagnose Oxymoney transactions"""
    print("=" * 80)
    print("OXYMONEY TRANSACTION DIAGNOSIS")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Check recent Oxymoney transactions
            print("\n1. Recent Oxymoney Transactions:")
            print("-" * 80)
            cursor.execute("""
                SELECT txn_id, order_id, amount, status, payment_url, 
                       pg_txn_id, created_at, completed_at
                FROM payin_transactions
                WHERE pg_partner = 'Oxymoney_Grosmart'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            transactions = cursor.fetchall()
            
            if not transactions:
                print("❌ No Oxymoney transactions found")
                return
            
            print(f"Found {len(transactions)} transaction(s):\n")
            
            for txn in transactions:
                print(f"Transaction ID: {txn['txn_id']}")
                print(f"  Order ID: {txn['order_id']}")
                print(f"  Amount: ₹{txn['amount']}")
                print(f"  Status: {txn['status']}")
                print(f"  PG Txn ID: {txn['pg_txn_id']}")
                print(f"  Payment URL: {txn['payment_url'][:50] if txn['payment_url'] else 'None'}...")
                print(f"  Created: {txn['created_at']}")
                print(f"  Completed: {txn['completed_at']}")
                
                # Check if VPA is in payment_url
                if txn['payment_url'] and '|VPA:' in txn['payment_url']:
                    vpa = txn['payment_url'].split('|VPA:')[1].split('|')[0]
                    print(f"  VPA in URL: {vpa}")
                else:
                    print(f"  ⚠️  VPA NOT found in payment_url")
                
                # Check if VPA usage recorded
                cursor.execute("""
                    SELECT * FROM oxymoney_vpa_usage
                    WHERE txn_id = %s
                """, (txn['txn_id'],))
                
                vpa_usage = cursor.fetchone()
                
                if vpa_usage:
                    print(f"  ✓ VPA usage recorded: {vpa_usage['vpa']} - ₹{vpa_usage['amount']}")
                else:
                    print(f"  ❌ VPA usage NOT recorded")
                    
                    if txn['status'] == 'SUCCESS':
                        print(f"  ⚠️  Transaction is SUCCESS but VPA usage not recorded!")
                
                print()
            
            # Check VPA usage table
            print("\n2. VPA Usage Today:")
            print("-" * 80)
            cursor.execute("""
                SELECT vpa, COUNT(*) as count, SUM(amount) as total
                FROM oxymoney_vpa_usage
                WHERE DATE(created_at) = CURDATE()
                GROUP BY vpa
            """)
            
            vpa_usage_today = cursor.fetchall()
            
            if not vpa_usage_today:
                print("❌ No VPA usage recorded today")
            else:
                for usage in vpa_usage_today:
                    print(f"VPA: {usage['vpa']}")
                    print(f"  Transactions: {usage['count']}")
                    print(f"  Total: ₹{usage['total']}")
            
            # Check successful transactions without VPA usage
            print("\n3. Successful Transactions WITHOUT VPA Usage:")
            print("-" * 80)
            cursor.execute("""
                SELECT pt.txn_id, pt.order_id, pt.amount, pt.status, 
                       pt.payment_url, pt.completed_at
                FROM payin_transactions pt
                LEFT JOIN oxymoney_vpa_usage ovu ON pt.txn_id = ovu.txn_id
                WHERE pt.pg_partner = 'Oxymoney_Grosmart'
                AND pt.status = 'SUCCESS'
                AND ovu.txn_id IS NULL
                ORDER BY pt.completed_at DESC
                LIMIT 10
            """)
            
            missing_usage = cursor.fetchall()
            
            if not missing_usage:
                print("✓ All successful transactions have VPA usage recorded")
            else:
                print(f"⚠️  Found {len(missing_usage)} successful transaction(s) without VPA usage:\n")
                
                for txn in missing_usage:
                    print(f"Transaction ID: {txn['txn_id']}")
                    print(f"  Order ID: {txn['order_id']}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  Status: {txn['status']}")
                    print(f"  Completed: {txn['completed_at']}")
                    
                    # Check if VPA is in payment_url
                    if txn['payment_url'] and '|VPA:' in txn['payment_url']:
                        vpa = txn['payment_url'].split('|VPA:')[1].split('|')[0]
                        print(f"  VPA in URL: {vpa}")
                        print(f"  ⚠️  VPA usage should be recorded for this transaction!")
                    else:
                        print(f"  ⚠️  VPA NOT found in payment_url (old format)")
                    
                    print()
            
            # Check callback logs if table exists
            print("\n4. Checking Callback Logs:")
            print("-" * 80)
            try:
                cursor.execute("""
                    SELECT merchant_id, txn_id, callback_url, response_code, 
                           response_data, created_at
                    FROM callback_logs
                    WHERE txn_id IN (
                        SELECT txn_id FROM payin_transactions 
                        WHERE pg_partner = 'Oxymoney_Grosmart'
                    )
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                
                callback_logs = cursor.fetchall()
                
                if not callback_logs:
                    print("No callback logs found")
                else:
                    print(f"Found {len(callback_logs)} callback log(s):\n")
                    for log in callback_logs:
                        print(f"Transaction ID: {log['txn_id']}")
                        print(f"  Response Code: {log['response_code']}")
                        print(f"  Created: {log['created_at']}")
                        print()
            except Exception as e:
                print(f"⚠️  Callback logs table not available: {e}")
            
            print("\n" + "=" * 80)
            print("DIAGNOSIS COMPLETE")
            print("=" * 80)
            
    finally:
        conn.close()

if __name__ == '__main__':
    diagnose_transaction()
