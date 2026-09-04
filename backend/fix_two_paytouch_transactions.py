#!/usr/bin/env python3
"""
Fix Two Specific PayTouch Transactions
Simple script to fix TXN55B24F6EE079 and TXNFE9EDCDDBD58
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from wallet_service import WalletService
from datetime import datetime

def fix_two_transactions():
    """
    Fix the two specific transactions
    """
    
    transactions = ['TXN55B24F6EE079', 'TXNFE9EDCDDBD58']
    
    print("=" * 80)
    print(f"Fix Two PayTouch Transactions - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    wallet_service = WalletService()
    
    try:
        with conn.cursor() as cursor:
            
            for txn_id in transactions:
                print(f"\n{'='*50}")
                print(f"Processing: {txn_id}")
                print(f"{'='*50}")
                
                # Get transaction details
                cursor.execute("""
                    SELECT txn_id, pg_txn_id, status, merchant_id, admin_id,
                           amount, net_amount, charge_amount, pg_partner
                    FROM payout_transactions
                    WHERE txn_id = %s
                """, (txn_id,))
                
                txn = cursor.fetchone()
                
                if not txn:
                    print(f"❌ Transaction not found: {txn_id}")
                    continue
                
                print(f"Current Status: {txn['status']}")
                print(f"PG Partner: {txn['pg_partner']}")
                print(f"Amount: ₹{txn['amount']}")
                print(f"Merchant ID: {txn['merchant_id']}")
                print(f"Admin ID: {txn['admin_id']}")
                
                if txn['status'] == 'SUCCESS':
                    print(f"✅ Already SUCCESS")
                    continue
                
                # Check wallet deduction
                cursor.execute("""
                    SELECT COUNT(*) as count FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'DEBIT'
                """, (txn['txn_id'],))
                
                wallet_count = cursor.fetchone()['count']
                wallet_deducted = wallet_count > 0
                
                print(f"Wallet already deducted: {'Yes' if wallet_deducted else 'No'}")
                
                # Confirm update
                response = input(f"\nUpdate {txn_id} to SUCCESS? (y/N): ").strip().lower()
                
                if response != 'y':
                    print("Skipped")
                    continue
                
                # Handle wallet deduction for merchant transactions
                if txn['merchant_id'] and not wallet_deducted:
                    print("Debiting merchant wallet...")
                    
                    debit_result = wallet_service.debit_merchant_wallet(
                        merchant_id=txn['merchant_id'],
                        amount=float(txn['amount']),
                        description=f"Payout: ₹{txn['net_amount']} + Charges: ₹{txn['charge_amount']}",
                        reference_id=txn['txn_id']
                    )
                    
                    if not debit_result['success']:
                        print(f"❌ Wallet debit failed: {debit_result['message']}")
                        continue
                    
                    print(f"✅ Wallet debited: ₹{debit_result['balance_before']} → ₹{debit_result['balance_after']}")
                
                # Update transaction
                sample_utr = f"PT{datetime.now().strftime('%Y%m%d%H%M%S')}{txn_id[-4:]}"
                
                cursor.execute("""
                    UPDATE payout_transactions
                    SET status = 'SUCCESS', 
                        utr = COALESCE(utr, %s),
                        completed_at = NOW(), 
                        updated_at = NOW(),
                        error_message = NULL
                    WHERE txn_id = %s
                """, (sample_utr, txn['txn_id']))
                
                conn.commit()
                
                print(f"✅ Updated to SUCCESS with UTR: {sample_utr}")
                
                # Log the change
                try:
                    cursor.execute("""
                        INSERT INTO activity_logs (user_id, action, description, ip_address, created_at)
                        VALUES (1, 'MANUAL_FIX', %s, '127.0.0.1', NOW())
                    """, (f"Manually updated PayTouch transaction {txn_id} from FAILED to SUCCESS",))
                    conn.commit()
                    print("📝 Activity logged")
                except:
                    print("⚠️  Could not log activity (table may not exist)")
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
    
    print(f"\n{'='*80}")
    print("Fix completed!")
    print("Check your dashboard - transactions should now show as SUCCESS")
    print(f"{'='*80}")

if __name__ == "__main__":
    fix_two_transactions()