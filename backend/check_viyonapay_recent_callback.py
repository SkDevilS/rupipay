"""
Check if Viyonapay sent callback for the most recent transaction
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
import json
from datetime import datetime

def check_recent_viyonapay_callback():
    """Check the most recent Viyonapay transaction and callback logs"""
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            print("\n" + "="*70)
            print("🔍 CHECKING VIYONAPAY RECENT TRANSACTION & CALLBACK")
            print("="*70)
            
            # Get most recent Viyonapay transaction
            cursor.execute("""
                SELECT 
                    txn_id,
                    order_id,
                    merchant_id,
                    amount,
                    net_amount,
                    charge_amount,
                    status,
                    pg_txn_id,
                    bank_ref_no,
                    payment_mode,
                    callback_url,
                    created_at,
                    completed_at
                FROM payin_transactions
                WHERE pg_partner = 'VIYONAPAY'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            txn = cursor.fetchone()
            
            if not txn:
                print("\n❌ No Viyonapay transactions found in database")
                return
            
            print(f"\n📋 MOST RECENT VIYONAPAY TRANSACTION:")
            print(f"{'─'*70}")
            print(f"  Transaction ID: {txn['txn_id']}")
            print(f"  Order ID: {txn['order_id']}")
            print(f"  Merchant ID: {txn['merchant_id']}")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Net Amount: ₹{txn['net_amount']}")
            print(f"  Charge: ₹{txn['charge_amount']}")
            print(f"  Status: {txn['status']}")
            print(f"  PG Txn ID: {txn['pg_txn_id'] or 'Not set'}")
            print(f"  Bank Ref: {txn['bank_ref_no'] or 'Not set'}")
            print(f"  Payment Mode: {txn['payment_mode'] or 'Not set'}")
            print(f"  Created: {txn['created_at']}")
            print(f"  Completed: {txn['completed_at'] or 'Not completed'}")
            print(f"  Callback URL: {txn['callback_url'] or 'Not set'}")
            
            # Check if callback was received in callback_logs table
            print(f"\n📞 CHECKING CALLBACK LOGS:")
            print(f"{'─'*70}")
            
            cursor.execute("""
                SELECT 
                    id,
                    callback_url,
                    request_data,
                    response_code,
                    response_data,
                    created_at
                FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            callbacks = cursor.fetchall()
            
            if callbacks:
                print(f"✅ Found {len(callbacks)} callback log(s) for this transaction:\n")
                
                for idx, cb in enumerate(callbacks, 1):
                    print(f"  Callback #{idx}:")
                    print(f"    Timestamp: {cb['created_at']}")
                    print(f"    Callback URL: {cb['callback_url']}")
                    print(f"    Response Code: {cb['response_code']}")
                    
                    # Parse request data
                    try:
                        request_data = json.loads(cb['request_data']) if cb['request_data'] else {}
                        print(f"    Request Data:")
                        print(f"      - Status: {request_data.get('status', 'N/A')}")
                        print(f"      - Order ID: {request_data.get('order_id', 'N/A')}")
                        print(f"      - Amount: ₹{request_data.get('amount', 'N/A')}")
                        print(f"      - UTR: {request_data.get('utr', 'N/A')}")
                    except:
                        print(f"    Request Data: {cb['request_data'][:100]}...")
                    
                    print(f"    Response: {cb['response_data'][:200] if cb['response_data'] else 'No response'}")
                    print()
            else:
                print("⚠️  NO callback logs found for this transaction")
                print("    This means either:")
                print("    1. Viyonapay hasn't sent the callback yet")
                print("    2. The callback was received but not logged")
                print("    3. The callback failed before reaching the logging code")
            
            # Check merchant callback configuration
            print(f"\n🔧 MERCHANT CALLBACK CONFIGURATION:")
            print(f"{'─'*70}")
            
            cursor.execute("""
                SELECT 
                    payin_callback_url,
                    payout_callback_url
                FROM merchant_callbacks
                WHERE merchant_id = %s
            """, (txn['merchant_id'],))
            
            merchant_cb = cursor.fetchone()
            
            if merchant_cb:
                print(f"  PayIn Callback URL: {merchant_cb['payin_callback_url'] or 'Not configured'}")
                print(f"  PayOut Callback URL: {merchant_cb['payout_callback_url'] or 'Not configured'}")
            else:
                print("  ⚠️  No callback configuration found for this merchant")
            
            # Check wallet transactions
            print(f"\n💰 WALLET TRANSACTIONS:")
            print(f"{'─'*70}")
            
            cursor.execute("""
                SELECT 
                    txn_type,
                    amount,
                    description,
                    created_at
                FROM merchant_wallet_transactions
                WHERE reference_id = %s
                ORDER BY created_at DESC
            """, (txn['txn_id'],))
            
            wallet_txns = cursor.fetchall()
            
            if wallet_txns:
                print(f"✅ Found {len(wallet_txns)} wallet transaction(s):\n")
                for wt in wallet_txns:
                    print(f"  - {wt['txn_type']}: ₹{wt['amount']}")
                    print(f"    Description: {wt['description']}")
                    print(f"    Time: {wt['created_at']}")
                    print()
            else:
                print("⚠️  No wallet transactions found")
                print("    Wallet should be credited when callback is received with SUCCESS status")
            
            # Summary
            print(f"\n📊 SUMMARY:")
            print(f"{'─'*70}")
            
            if txn['status'] == 'INITIATED':
                print("  Status: Transaction is still INITIATED")
                print("  ⏳ Waiting for Viyonapay callback...")
            elif txn['status'] == 'PENDING':
                print("  Status: Transaction is PENDING")
                print("  ⏳ Waiting for final status from Viyonapay...")
            elif txn['status'] == 'SUCCESS':
                print("  Status: ✅ Transaction is SUCCESS")
                if callbacks:
                    print("  Callback: ✅ Callback was received and processed")
                else:
                    print("  Callback: ⚠️  No callback log found (might have been processed before logging was added)")
                if wallet_txns:
                    print("  Wallet: ✅ Wallet was credited")
                else:
                    print("  Wallet: ⚠️  Wallet not credited (possible issue)")
            elif txn['status'] == 'FAILED':
                print("  Status: ❌ Transaction FAILED")
                if callbacks:
                    print("  Callback: ✅ Callback was received")
                else:
                    print("  Callback: ⚠️  No callback log found")
            
            print(f"\n{'='*70}")
            
            # Check server logs for encrypted callbacks
            print(f"\n� CHECKING SERVER LOGS FOR ENCRYPTED CALLBACKS:")
            print(f"{'─'*70}")
            
            try:
                import subprocess
                
                # Check if running as systemd service
                print("  Searching for Viyonapay callbacks in server logs...")
                
                # Try to read from journalctl (systemd service logs)
                try:
                    result = subprocess.run(
                        ['journalctl', '-u', 'moneyone-api', '-n', '500', '--no-pager'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        logs = result.stdout
                        
                        # Search for Viyonapay callback entries
                        viyona_lines = [line for line in logs.split('\n') if 'VIYONAPAY' in line or 'viyonapay' in line.lower()]
                        
                        if viyona_lines:
                            print(f"\n  ✅ Found {len(viyona_lines)} Viyonapay-related log entries:")
                            print(f"  (Showing last 10)\n")
                            
                            for line in viyona_lines[-10:]:
                                print(f"    {line[:150]}")
                            
                            # Check for encrypted_data in logs
                            encrypted_found = any('encrypted_data' in line for line in viyona_lines)
                            if encrypted_found:
                                print(f"\n  ✅ ENCRYPTED CALLBACK DATA FOUND in logs!")
                                print(f"     Viyonapay sent encrypted webhook to your server")
                            else:
                                print(f"\n  ⚠️  No encrypted_data found in recent logs")
                        else:
                            print(f"  ⚠️  No Viyonapay entries found in recent logs")
                    else:
                        print(f"  ⚠️  Could not read systemd logs (journalctl failed)")
                        
                except FileNotFoundError:
                    print(f"  ⚠️  journalctl not available (not a systemd service)")
                except subprocess.TimeoutExpired:
                    print(f"  ⚠️  Log reading timed out")
                    
            except Exception as e:
                print(f"  ⚠️  Could not check server logs: {e}")
            
            # Manual log check instructions
            print(f"\n💡 MANUAL LOG CHECK COMMANDS:")
            print(f"{'─'*70}")
            print(f"  For systemd service (moneyone-api):")
            print(f"  sudo journalctl -u moneyone-api -n 500 --no-pager | grep -i viyonapay")
            print(f"  ")
            print(f"  To see encrypted callback data:")
            print(f"  sudo journalctl -u moneyone-api -n 500 --no-pager | grep -A 10 'encrypted_data'")
            print(f"  ")
            print(f"  To follow live logs:")
            print(f"  sudo journalctl -u moneyone-api -f | grep -i viyonapay")
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_recent_viyonapay_callback()
