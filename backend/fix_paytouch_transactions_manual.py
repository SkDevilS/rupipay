#!/usr/bin/env python3
"""
Manual PayTouch Transaction Status Fix
Manually checks and updates the status of specific PayTouch transactions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from paytouch_service import PayTouchService
from wallet_service import WalletService
from datetime import datetime
import json

def fix_paytouch_transactions():
    """
    Fix the specific PayTouch transactions that are showing as FAILED
    but might actually be successful
    """
    
    # The two transactions from your output
    transactions_to_check = [
        {
            'pg_txn_id': 'ADMIN20260310182521A6904E',
            'txn_id': 'TXN55B24F6EE079',
            'amount': 1.00
        },
        {
            'pg_txn_id': 'ADMIN20260310182131FF1C8D', 
            'txn_id': 'TXNFE9EDCDDBD58',
            'amount': 30000.00
        }
    ]
    
    print("=" * 80)
    print("PayTouch Transaction Status Fix - Manual Check")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    paytouch_service = PayTouchService()
    wallet_service = WalletService()
    
    try:
        with conn.cursor() as cursor:
            for txn_info in transactions_to_check:
                print(f"\n{'='*60}")
                print(f"Checking Transaction: {txn_info['pg_txn_id']}")
                print(f"TXN ID: {txn_info['txn_id']}")
                print(f"Amount: ₹{txn_info['amount']}")
                print(f"{'='*60}")
                
                # Get current transaction details from database
                cursor.execute("""
                    SELECT txn_id, pg_txn_id, reference_id, status, merchant_id, admin_id,
                           amount, net_amount, charge_amount, utr, created_at
                    FROM payout_transactions
                    WHERE pg_txn_id = %s AND pg_partner = 'PayTouch'
                """, (txn_info['pg_txn_id'],))
                
                db_txn = cursor.fetchone()
                
                if not db_txn:
                    print(f"❌ Transaction not found in database: {txn_info['pg_txn_id']}")
                    continue
                
                print(f"📊 Database Status: {db_txn['status']}")
                print(f"📊 Database UTR: {db_txn['utr']}")
                print(f"📊 Merchant ID: {db_txn['merchant_id']}")
                print(f"📊 Admin ID: {db_txn['admin_id']}")
                print(f"📊 Amount: ₹{db_txn['amount']} (Net: ₹{db_txn['net_amount']}, Charges: ₹{db_txn['charge_amount']})")
                
                # Check PayTouch API status
                print(f"\n🔍 Checking PayTouch API status...")
                
                status_result = paytouch_service.check_payout_status(
                    transaction_id=txn_info['pg_txn_id'],
                    external_ref=txn_info['pg_txn_id']
                )
                
                if not status_result['success']:
                    print(f"❌ PayTouch API check failed: {status_result['message']}")
                    continue
                
                api_status = status_result['status']
                api_utr = status_result.get('utr')
                
                print(f"📡 PayTouch API Status: {api_status}")
                print(f"📡 PayTouch API UTR: {api_utr}")
                
                # Compare statuses
                if db_txn['status'] == api_status:
                    print(f"✅ Status matches - no update needed")
                    continue
                
                print(f"⚠️  STATUS MISMATCH!")
                print(f"   Database: {db_txn['status']}")
                print(f"   PayTouch API: {api_status}")
                
                # Ask for confirmation before updating
                print(f"\n🤔 Do you want to update this transaction?")
                print(f"   Transaction: {db_txn['txn_id']}")
                print(f"   From: {db_txn['status']} → To: {api_status}")
                print(f"   UTR: {db_txn['utr']} → {api_utr}")
                
                response = input("Update? (y/N): ").strip().lower()
                
                if response != 'y':
                    print("❌ Skipping update")
                    continue
                
                print(f"\n🔄 Updating transaction status...")
                
                # Handle SUCCESS status - need to debit wallet
                if api_status == 'SUCCESS' and db_txn['merchant_id']:
                    print(f"💰 Transaction is SUCCESS - checking wallet deduction...")
                    
                    # Check if wallet was already deducted
                    cursor.execute("""
                        SELECT txn_id FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'DEBIT'
                    """, (db_txn['txn_id'],))
                    
                    wallet_already_deducted = cursor.fetchone()
                    
                    if wallet_already_deducted:
                        print(f"⚠️  Wallet already deducted for this transaction")
                    else:
                        print(f"💸 Debiting merchant wallet...")
                        
                        # Use 'amount' field which contains total deduction
                        total_deduction = float(db_txn['amount'])
                        
                        print(f"   Deducting: ₹{total_deduction:.2f}")
                        print(f"   (Net: ₹{db_txn['net_amount']:.2f} + Charges: ₹{db_txn['charge_amount']:.2f})")
                        
                        # Debit merchant wallet
                        debit_result = wallet_service.debit_merchant_wallet(
                            merchant_id=db_txn['merchant_id'],
                            amount=total_deduction,
                            description=f"Payout: ₹{db_txn['net_amount']:.2f} + Charges: ₹{db_txn['charge_amount']:.2f}",
                            reference_id=db_txn['txn_id']
                        )
                        
                        if debit_result['success']:
                            print(f"✅ WALLET DEBITED")
                            print(f"   Balance: ₹{debit_result['balance_before']:.2f} → ₹{debit_result['balance_after']:.2f}")
                        else:
                            print(f"❌ WALLET DEBIT FAILED: {debit_result['message']}")
                            print(f"❌ Cannot mark transaction as SUCCESS without wallet deduction")
                            continue
                
                # Update transaction status
                if api_status in ['SUCCESS', 'FAILED']:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, utr = %s, 
                            error_message = %s, completed_at = NOW(), updated_at = NOW()
                        WHERE txn_id = %s
                    """, (
                        api_status, 
                        api_utr, 
                        status_result.get('message') if api_status == 'FAILED' else None,
                        db_txn['txn_id']
                    ))
                else:
                    cursor.execute("""
                        UPDATE payout_transactions
                        SET status = %s, updated_at = NOW()
                        WHERE txn_id = %s
                    """, (api_status, db_txn['txn_id']))
                
                conn.commit()
                
                # Verify update
                cursor.execute("""
                    SELECT status, utr, completed_at
                    FROM payout_transactions
                    WHERE txn_id = %s
                """, (db_txn['txn_id'],))
                
                updated_txn = cursor.fetchone()
                
                print(f"✅ TRANSACTION UPDATED")
                print(f"   Status: {updated_txn['status']}")
                print(f"   UTR: {updated_txn['utr']}")
                print(f"   Completed: {updated_txn['completed_at']}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
    
    print(f"\n{'='*80}")
    print("Manual fix completed")
    print(f"{'='*80}")

if __name__ == "__main__":
    fix_paytouch_transactions()