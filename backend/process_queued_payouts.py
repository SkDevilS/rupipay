#!/usr/bin/env python3
"""
Process Queued Payouts for Specific Merchant (TODAY ONLY)
This script processes QUEUED/PENDING/INITIATED payouts one by one using Mudrape API.
"""

import sys
import time
from decimal import Decimal
from datetime import datetime
from database import get_db_connection
from mudrape_service import MudrapeService
from wallet_service import WalletService

def process_queued_payouts(merchant_id, dry_run=True):
    """
    Process queued payouts for a specific merchant (TODAY ONLY).
    
    Args:
        merchant_id: The merchant ID to process
        dry_run: If True, only show what would be done without making changes
    """
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    # Initialize services
    mudrape_service = MudrapeService()
    wallet_service = WalletService()
    
    try:
        with conn.cursor() as cursor:
            # Verify merchant exists
            cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
            merchant = cursor.fetchone()
            
            if not merchant:
                print(f"❌ Merchant {merchant_id} not found")
                return False
            
            print(f"\n{'='*80}")
            print(f"Process Queued Payouts (TODAY ONLY)")
            print(f"{'='*80}")
            print(f"Merchant ID: {merchant['merchant_id']}")
            print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will process payouts)'}")
            print(f"{'='*80}\n")
            
            # Get current wallet balance
            cursor.execute("""
                SELECT settled_balance, unsettled_balance 
                FROM merchant_wallet 
                WHERE merchant_id = %s
            """, (merchant_id,))
            wallet = cursor.fetchone()
            
            if wallet:
                print(f"Current Wallet Balance:")
                print(f"  Settled: ₹{float(wallet['settled_balance']):.2f}")
                print(f"  Unsettled: ₹{float(wallet['unsettled_balance']):.2f}")
            else:
                print(f"⚠️  No wallet found for merchant {merchant_id}")
            
            print(f"\n{'='*80}")
            print("Finding TODAY's queued/pending payouts...")
            print(f"{'='*80}\n")
            
            # Get today's date
            from datetime import date
            today = date.today()
            print(f"Processing payouts for: {today.strftime('%Y-%m-%d')}\n")
            
            # Find queued/pending/initiated payouts from TODAY
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    order_id,
                    merchant_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    pg_partner,
                    account_no,
                    ifsc_code,
                    bene_name,
                    created_at
                FROM payout_transactions
                WHERE merchant_id = %s
                    AND UPPER(status) IN ('QUEUED', 'PENDING', 'INITIATED')
                    AND DATE(created_at) = CURDATE()
                    AND UPPER(pg_partner) = 'MUDRAPE'
                ORDER BY created_at ASC
            """, (merchant_id,))
            
            queued_payouts = cursor.fetchall()
            
            if not queued_payouts:
                print("✅ No queued payouts found for TODAY.")
                return True
            
            print(f"Found {len(queued_payouts)} queued payout(s) from TODAY:\n")
            
            processed_count = 0
            failed_count = 0
            skipped_count = 0
            
            for idx, payout in enumerate(queued_payouts, 1):
                txn_id = payout['txn_id']
                reference_id = payout['reference_id']
                order_id = payout['order_id']
                amount = Decimal(str(payout['amount']))
                charge_amount = Decimal(str(payout['charge_amount']))
                net_amount = Decimal(str(payout['net_amount']))
                status = payout['status']
                account_no = payout['account_no']
                ifsc_code = payout['ifsc_code']
                bene_name = payout['bene_name']
                created_at = payout['created_at']
                
                print(f"{idx}. Transaction: {txn_id}")
                print(f"   Reference ID: {reference_id}")
                print(f"   Order ID: {order_id}")
                print(f"   Amount: ₹{float(amount):.2f}")
                print(f"   Charges: ₹{float(charge_amount):.2f}")
                print(f"   Net to Bank: ₹{float(net_amount):.2f}")
                print(f"   Status: {status}")
                print(f"   Beneficiary: {bene_name}")
                print(f"   Account: {account_no}")
                print(f"   IFSC: {ifsc_code}")
                print(f"   Created: {created_at}")
                
                if dry_run:
                    print(f"   🔍 WOULD PROCESS via Mudrape API")
                else:
                    try:
                        # Call Mudrape API
                        print(f"   📤 Calling Mudrape API...")
                        result = mudrape_service.call_imps_payout_api(
                            account_number=account_no,
                            ifsc_code=ifsc_code,
                            client_txn_id=reference_id,
                            amount=float(net_amount),
                            beneficiary_name=bene_name
                        )
                        
                        if result['success']:
                            api_status = result.get('status', 'INITIATED')
                            mudrape_txn_id = result.get('mudrape_txn_id', '')
                            
                            print(f"   ✅ Mudrape API Response: {api_status}")
                            print(f"   Mudrape TxnID: {mudrape_txn_id}")
                            
                            # Update transaction status
                            if api_status in ['SUCCESS', 'FAILED']:
                                cursor.execute("""
                                    UPDATE payout_transactions 
                                    SET status = %s, pg_txn_id = %s, completed_at = NOW(), updated_at = NOW()
                                    WHERE txn_id = %s
                                """, (api_status, mudrape_txn_id, txn_id))
                            else:
                                cursor.execute("""
                                    UPDATE payout_transactions 
                                    SET status = %s, pg_txn_id = %s, updated_at = NOW()
                                    WHERE txn_id = %s
                                """, (api_status, mudrape_txn_id, txn_id))
                            
                            conn.commit()
                            
                            # If status is SUCCESS, deduct wallet
                            if api_status == 'SUCCESS':
                                print(f"   💰 Deducting wallet...")
                                debit_result = wallet_service.debit_merchant_wallet(
                                    merchant_id=merchant_id,
                                    amount=amount,
                                    description=f"Payout: ₹{float(net_amount):.2f} + Charges: ₹{float(charge_amount):.2f}",
                                    reference_id=txn_id
                                )
                                
                                if debit_result['success']:
                                    print(f"   ✅ Wallet debited: ₹{float(debit_result['balance_before']):.2f} → ₹{float(debit_result['balance_after']):.2f}")
                                else:
                                    print(f"   ⚠️  Wallet deduction failed: {debit_result['message']}")
                            
                            # If status is INITIATED, check status after 2 seconds
                            if api_status == 'INITIATED':
                                print(f"   ⏳ Waiting 2 seconds before status check...")
                                time.sleep(2)
                                
                                status_result = mudrape_service.check_payout_status(reference_id)
                                if status_result.get('success'):
                                    updated_status = status_result.get('status', 'INITIATED')
                                    utr = status_result.get('utr')
                                    
                                    print(f"   📊 Status Check: {updated_status}")
                                    if utr:
                                        print(f"   UTR: {utr}")
                                    
                                    # Update with latest status
                                    if updated_status in ['SUCCESS', 'FAILED']:
                                        cursor.execute("""
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, completed_at = NOW(), updated_at = NOW()
                                            WHERE txn_id = %s
                                        """, (updated_status, utr, txn_id))
                                    else:
                                        cursor.execute("""
                                            UPDATE payout_transactions 
                                            SET status = %s, utr = %s, updated_at = NOW()
                                            WHERE txn_id = %s
                                        """, (updated_status, utr, txn_id))
                                    
                                    conn.commit()
                                    
                                    # Deduct wallet if status changed to SUCCESS
                                    if updated_status == 'SUCCESS' and api_status != 'SUCCESS':
                                        print(f"   💰 Deducting wallet...")
                                        debit_result = wallet_service.debit_merchant_wallet(
                                            merchant_id=merchant_id,
                                            amount=amount,
                                            description=f"Payout: ₹{float(net_amount):.2f} + Charges: ₹{float(charge_amount):.2f}",
                                            reference_id=txn_id
                                        )
                                        
                                        if debit_result['success']:
                                            print(f"   ✅ Wallet debited: ₹{float(debit_result['balance_before']):.2f} → ₹{float(debit_result['balance_after']):.2f}")
                                        else:
                                            print(f"   ⚠️  Wallet deduction failed: {debit_result['message']}")
                            
                            processed_count += 1
                            
                        else:
                            print(f"   ❌ Mudrape API Error: {result.get('message')}")
                            
                            # Update status to FAILED
                            cursor.execute("""
                                UPDATE payout_transactions 
                                SET status = 'FAILED', error_message = %s, completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (result.get('message', 'Mudrape API failed'), txn_id))
                            conn.commit()
                            
                            failed_count += 1
                            
                    except Exception as e:
                        print(f"   ❌ ERROR: {str(e)}")
                        failed_count += 1
                
                print()
                
                # Add delay between requests to avoid rate limiting
                if not dry_run and idx < len(queued_payouts):
                    time.sleep(1)
            
            print(f"{'='*80}")
            print("Summary")
            print(f"{'='*80}")
            print(f"Total Queued Payouts: {len(queued_payouts)}")
            print(f"Processed: {processed_count}")
            print(f"Failed: {failed_count}")
            print(f"Skipped: {skipped_count}")
            
            if dry_run:
                print(f"\n⚠️  DRY RUN MODE - No changes were made")
                print(f"Run with --live flag to process payouts")
            else:
                print(f"\n✅ Payout processing completed")
                
                # Show updated wallet balance
                cursor.execute("""
                    SELECT settled_balance, unsettled_balance 
                    FROM merchant_wallet 
                    WHERE merchant_id = %s
                """, (merchant_id,))
                updated_wallet = cursor.fetchone()
                
                if updated_wallet:
                    print(f"\nUpdated Wallet Balance:")
                    print(f"  Settled: ₹{float(updated_wallet['settled_balance']):.2f}")
                    print(f"  Unsettled: ₹{float(updated_wallet['unsettled_balance']):.2f}")
            
            print(f"{'='*80}\n")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python process_queued_payouts.py <merchant_id> [--live]")
        print("\nExamples:")
        print("  python process_queued_payouts.py 7679022140          # Dry run")
        print("  python process_queued_payouts.py 7679022140 --live   # Process payouts")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    dry_run = '--live' not in sys.argv
    
    if not dry_run:
        print("\n⚠️  WARNING: Running in LIVE mode. Payouts will be processed via Mudrape API.")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    success = process_queued_payouts(merchant_id, dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
