#!/usr/bin/env python3
"""
Check if Mudrape Payout Callbacks are Being Received
Shows detailed analysis of recent transactions and callback status
"""

import sys
from database import get_db_connection
from datetime import datetime, timedelta

def check_callback_received(reference_id=None, limit=20):
    """
    Check if Mudrape callbacks are being received for recent payout transactions
    
    Args:
        reference_id: Optional specific reference_id to check
        limit: Number of recent transactions to check (default: 20)
    """
    
    print("=" * 80)
    print("MUDRAPE PAYOUT CALLBACK STATUS CHECK")
    print("=" * 80)
    print()
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            if reference_id:
                # Check specific transaction
                print(f"Checking specific transaction: {reference_id}")
                print("-" * 80)
                
                cursor.execute("""
                    SELECT 
                        txn_id,
                        reference_id,
                        merchant_id,
                        amount,
                        net_amount,
                        charge_amount,
                        status,
                        pg_txn_id,
                        utr,
                        created_at,
                        updated_at,
                        completed_at
                    FROM payout_transactions
                    WHERE reference_id = %s AND pg_partner = 'Mudrape'
                """, (reference_id,))
                
                transactions = [cursor.fetchone()]
            else:
                # Check recent transactions
                print(f"Checking last {limit} Mudrape payout transactions...")
                print("-" * 80)
                
                cursor.execute("""
                    SELECT 
                        txn_id,
                        reference_id,
                        merchant_id,
                        amount,
                        net_amount,
                        charge_amount,
                        status,
                        pg_txn_id,
                        utr,
                        created_at,
                        updated_at,
                        completed_at
                    FROM payout_transactions
                    WHERE pg_partner = 'Mudrape'
                    AND created_at >= NOW() - INTERVAL 24 HOUR
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                
                transactions = cursor.fetchall()
            
            if not transactions or not transactions[0]:
                print("No Mudrape payout transactions found")
                conn.close()
                return
            
            print(f"Found {len(transactions)} transactions")
            print()
            
            # Analyze each transaction
            callback_received_count = 0
            callback_not_received_count = 0
            pending_count = 0
            
            for txn in transactions:
                print(f"Transaction: {txn['txn_id']}")
                print(f"  Reference ID: {txn['reference_id']}")
                print(f"  Merchant: {txn['merchant_id']}")
                print(f"  Amount: ₹{txn['amount']:.2f} (Net: ₹{txn['net_amount']:.2f} + Charges: ₹{txn['charge_amount']:.2f})")
                print(f"  Status: {txn['status']}")
                print(f"  PG TXN ID: {txn['pg_txn_id']}")
                print(f"  UTR: {txn['utr']}")
                print(f"  Created: {txn['created_at']}")
                print(f"  Updated: {txn['updated_at']}")
                print(f"  Completed: {txn['completed_at']}")
                
                # Determine if callback was received
                callback_received = False
                callback_status = "❓ Unknown"
                
                # Check 1: Status changed from INITIATED
                if txn['status'] in ['SUCCESS', 'FAILED']:
                    callback_received = True
                    callback_status = "✅ Callback Received (Status updated to final state)"
                    callback_received_count += 1
                elif txn['status'] in ['INITIATED', 'QUEUED', 'INPROCESS']:
                    # Check if updated_at is significantly different from created_at
                    if txn['updated_at'] and txn['created_at']:
                        time_diff = (txn['updated_at'] - txn['created_at']).total_seconds()
                        if time_diff > 5:  # More than 5 seconds difference
                            callback_status = "⚠️  Partial Callback (Status updated but not final)"
                            callback_received = True
                            callback_received_count += 1
                        else:
                            callback_status = "❌ No Callback Received (Status still INITIATED/PENDING)"
                            callback_not_received_count += 1
                    else:
                        callback_status = "❌ No Callback Received (Status still INITIATED/PENDING)"
                        callback_not_received_count += 1
                    
                    pending_count += 1
                
                # Check 2: Check if wallet was deducted (indicates SUCCESS callback)
                cursor.execute("""
                    SELECT txn_id, amount, created_at
                    FROM merchant_wallet_transactions
                    WHERE reference_id = %s AND txn_type = 'DEBIT'
                """, (txn['txn_id'],))
                
                wallet_txn = cursor.fetchone()
                
                if wallet_txn:
                    print(f"  Wallet Deduction: ✅ Yes (₹{wallet_txn['amount']:.2f} at {wallet_txn['created_at']})")
                    if not callback_received:
                        callback_status = "✅ Callback Received (Wallet deducted)"
                        callback_received = True
                        callback_received_count += 1
                else:
                    print(f"  Wallet Deduction: ❌ No")
                
                # Calculate time since creation
                if txn['created_at']:
                    time_since_creation = datetime.now() - txn['created_at']
                    minutes = int(time_since_creation.total_seconds() / 60)
                    print(f"  Time Since Creation: {minutes} minutes ago")
                
                print(f"  Callback Status: {callback_status}")
                print()
            
            # Summary
            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Total Transactions: {len(transactions)}")
            print(f"✅ Callbacks Received: {callback_received_count}")
            print(f"❌ Callbacks NOT Received: {callback_not_received_count}")
            print(f"⏳ Still Pending: {pending_count}")
            print()
            
            # Check backend logs for callback entries
            print("=" * 80)
            print("CHECKING BACKEND LOGS")
            print("=" * 80)
            print()
            print("To check if callbacks are being received by the server, run:")
            print()
            print("  tail -100 /var/www/moneyone/logs/backend.log | grep 'Mudrape Payout Callback'")
            print()
            print("Or for real-time monitoring:")
            print()
            print("  tail -f /var/www/moneyone/logs/backend.log | grep -A 20 'Mudrape Payout Callback'")
            print()
            
            # Recommendations
            print("=" * 80)
            print("TROUBLESHOOTING STEPS")
            print("=" * 80)
            print()
            
            if callback_not_received_count > 0:
                print("⚠️  Some callbacks are NOT being received. Possible causes:")
                print()
                print("1. Callback URL not configured in Mudrape dashboard")
                print("   - Login to Mudrape merchant portal")
                print("   - Check callback URL settings")
                print("   - Expected URL: https://your-domain.com/api/callback/mudrape/payout")
                print()
                print("2. Server not accessible from Mudrape")
                print("   - Check firewall rules")
                print("   - Verify security groups allow incoming HTTPS")
                print("   - Test with: curl -X POST https://your-domain.com/api/callback/mudrape/payout")
                print()
                print("3. Callback route not registered")
                print("   - Check backend/app.py for mudrape_callback_bp registration")
                print("   - Restart backend: sudo systemctl restart moneyone-api")
                print()
                print("4. Mudrape not sending callbacks")
                print("   - Contact Mudrape support")
                print("   - Ask them to check callback delivery logs")
                print("   - Verify your merchant account is configured for callbacks")
                print()
                print("5. Check server logs for errors:")
                print("   - grep -i 'error' /var/www/moneyone/logs/backend.log | tail -50")
                print()
            else:
                print("✅ All recent transactions have received callbacks!")
                print()
                print("If wallet deductions are still missing, the issue is in the")
                print("callback processing logic, not callback delivery.")
                print()
                print("Run the backfill script to fix missing wallet deductions:")
                print("  python3 fix_missing_mudrape_wallet_deductions.py --live")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print()
    print("=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Check Mudrape callback status')
    parser.add_argument('--reference-id', help='Specific reference_id to check')
    parser.add_argument('--limit', type=int, default=20, help='Number of recent transactions to check')
    
    args = parser.parse_args()
    
    check_callback_received(
        reference_id=args.reference_id,
        limit=args.limit
    )
