"""
Diagnose Oxymoney VPA Limit Update Issue
Checks why VPA limit is not being updated after successful callback
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime
import json

def diagnose_vpa_issue(txn_id=None, order_id=None):
    """
    Diagnose VPA limit update issue for a specific transaction
    
    Args:
        txn_id: Transaction ID
        order_id: Order ID
    """
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print("=" * 80)
            print("OXYMONEY VPA LIMIT UPDATE DIAGNOSTIC")
            print("=" * 80)
            
            # Find transaction
            if txn_id:
                cursor.execute("""
                    SELECT * FROM payin_transactions
                    WHERE txn_id = %s AND pg_partner = 'Oxymoney_Grosmart'
                """, (txn_id,))
            elif order_id:
                cursor.execute("""
                    SELECT * FROM payin_transactions
                    WHERE order_id = %s AND pg_partner = 'Oxymoney_Grosmart'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (order_id,))
            else:
                # Get most recent Oxymoney transaction
                cursor.execute("""
                    SELECT * FROM payin_transactions
                    WHERE pg_partner = 'Oxymoney_Grosmart'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
            
            txn = cursor.fetchone()
            
            if not txn:
                print("❌ No Oxymoney transaction found")
                return
            
            print(f"\n📋 TRANSACTION DETAILS:")
            print(f"  Transaction ID: {txn['txn_id']}")
            print(f"  Order ID: {txn['order_id']}")
            print(f"  Merchant ID: {txn['merchant_id']}")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Status: {txn['status']}")
            print(f"  PG Txn ID: {txn.get('pg_txn_id', 'N/A')}")
            print(f"  Bank Ref No (UTR): {txn.get('bank_ref_no', 'N/A')}")
            print(f"  Created At: {txn['created_at']}")
            print(f"  Completed At: {txn.get('completed_at', 'N/A')}")
            
            # Extract VPA from payment_url
            payment_url = txn.get('payment_url', '')
            vpa_used = None
            if '|VPA:' in payment_url:
                vpa_used = payment_url.split('|VPA:')[1].split('|')[0]
                print(f"  VPA Used: {vpa_used}")
            else:
                print(f"  ⚠️  VPA not found in payment_url")
                print(f"  Payment URL: {payment_url}")
            
            # Check wallet transactions
            print(f"\n💰 WALLET TRANSACTIONS:")
            cursor.execute("""
                SELECT * FROM merchant_wallet_transactions
                WHERE reference_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            wallet_txns = cursor.fetchall()
            
            if wallet_txns:
                print(f"  Found {len(wallet_txns)} wallet transaction(s):")
                for wt in wallet_txns:
                    print(f"    - Type: {wt['txn_type']}")
                    print(f"      Amount: ₹{wt['amount']}")
                    print(f"      Balance After: ₹{wt['balance_after']}")
                    print(f"      Created At: {wt['created_at']}")
            else:
                print(f"  ⚠️  No wallet transactions found")
                print(f"  This means wallet was NOT credited!")
            
            # Check VPA usage record
            print(f"\n📊 VPA USAGE RECORD:")
            cursor.execute("""
                SELECT * FROM oxymoney_vpa_usage
                WHERE txn_id = %s
            """, (txn['txn_id'],))
            
            vpa_usage = cursor.fetchone()
            
            if vpa_usage:
                print(f"  ✅ VPA usage recorded:")
                print(f"    VPA: {vpa_usage['vpa']}")
                print(f"    Amount: ₹{vpa_usage['amount']}")
                print(f"    Merchant ID: {vpa_usage['merchant_id']}")
                print(f"    Created At: {vpa_usage['created_at']}")
            else:
                print(f"  ❌ VPA usage NOT recorded!")
                print(f"  This is the problem - VPA limit was not updated")
            
            # Check callback logs
            print(f"\n📞 CALLBACK LOGS:")
            cursor.execute("""
                SELECT * FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            callback_logs = cursor.fetchall()
            
            if callback_logs:
                print(f"  Found {len(callback_logs)} callback attempt(s):")
                for cb in callback_logs:
                    print(f"    - URL: {cb['callback_url']}")
                    print(f"      Response Code: {cb['response_code']}")
                    print(f"      Created At: {cb['created_at']}")
                    if cb['response_data']:
                        print(f"      Response: {cb['response_data'][:100]}...")
            else:
                print(f"  ⚠️  No callback logs found")
            
            # Check today's VPA usage for this VPA
            if vpa_used:
                print(f"\n📈 TODAY'S VPA USAGE ({vpa_used}):")
                today = datetime.now().date()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as txn_count,
                        SUM(amount) as total_amount
                    FROM oxymoney_vpa_usage
                    WHERE vpa = %s AND DATE(created_at) = %s
                """, (vpa_used, today))
                
                usage = cursor.fetchone()
                
                if usage and usage['total_amount']:
                    total_usage = float(usage['total_amount'])
                    limit = 960000.00
                    percentage = (total_usage / limit) * 100
                    remaining = limit - total_usage
                    
                    print(f"  Total Transactions: {usage['txn_count']}")
                    print(f"  Total Amount: ₹{total_usage:,.2f}")
                    print(f"  Daily Limit: ₹{limit:,.2f}")
                    print(f"  Usage: {percentage:.2f}%")
                    print(f"  Remaining: ₹{remaining:,.2f}")
                else:
                    print(f"  No usage recorded for today")
            
            # Diagnosis
            print(f"\n🔍 DIAGNOSIS:")
            print("=" * 80)
            
            if txn['status'] != 'SUCCESS':
                print(f"❌ Transaction status is '{txn['status']}', not 'SUCCESS'")
                print(f"   VPA usage is only recorded for successful transactions")
            elif not wallet_txns:
                print(f"❌ Wallet was NOT credited")
                print(f"   This indicates callback processing failed or was skipped")
            elif not vpa_usage:
                print(f"❌ VPA usage was NOT recorded")
                print(f"   Possible causes:")
                print(f"   1. VPA not found in payment_url field")
                print(f"   2. Callback handler failed before VPA recording")
                print(f"   3. VPA recording code was inside wallet credit check")
                print(f"   4. Database error during VPA recording")
            else:
                print(f"✅ Everything looks correct!")
                print(f"   Transaction successful, wallet credited, VPA usage recorded")
            
            # Check if this is a duplicate callback scenario
            if wallet_txns and not vpa_usage:
                print(f"\n⚠️  DUPLICATE CALLBACK SCENARIO DETECTED:")
                print(f"   Wallet was credited but VPA usage not recorded")
                print(f"   This happens when:")
                print(f"   1. First callback: Wallet credited + VPA recorded")
                print(f"   2. Second callback: Wallet already credited, VPA recording skipped")
                print(f"   Solution: Move VPA recording outside wallet credit check")
            
            print("\n" + "=" * 80)
            
    except Exception as e:
        print(f"❌ Diagnostic error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

def show_all_recent_oxymoney_transactions():
    """Show all recent Oxymoney transactions"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        
        with conn.cursor() as cursor:
            print("\n" + "=" * 80)
            print("RECENT OXYMONEY TRANSACTIONS")
            print("=" * 80)
            
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    status,
                    created_at,
                    completed_at
                FROM payin_transactions
                WHERE pg_partner = 'Oxymoney_Grosmart'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            txns = cursor.fetchall()
            
            if txns:
                print(f"\nFound {len(txns)} recent transaction(s):\n")
                for idx, txn in enumerate(txns, 1):
                    print(f"{idx}. {txn['txn_id']}")
                    print(f"   Order: {txn['order_id']}")
                    print(f"   Amount: ₹{txn['amount']}")
                    print(f"   Status: {txn['status']}")
                    print(f"   Created: {txn['created_at']}")
                    print()
            else:
                print("\nNo Oxymoney transactions found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnose Oxymoney VPA limit update issue')
    parser.add_argument('--txn-id', help='Transaction ID to diagnose')
    parser.add_argument('--order-id', help='Order ID to diagnose')
    parser.add_argument('--list', action='store_true', help='List recent Oxymoney transactions')
    
    args = parser.parse_args()
    
    if args.list:
        show_all_recent_oxymoney_transactions()
    else:
        diagnose_vpa_issue(txn_id=args.txn_id, order_id=args.order_id)
