#!/usr/bin/env python3
"""
Check PayTouch callbacks received today
Identify missing callbacks and status mismatches
"""

from database import get_db_connection
from paytouch_service import PayTouchService
import json
from datetime import datetime, timedelta

def check_paytouch_callbacks_today():
    """Check PayTouch callbacks and identify issues"""
    
    print("=" * 80)
    print(f"PayTouch Callback Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get today's PayTouch transactions
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, net_amount,
                    status, pg_txn_id, utr, error_message,
                    created_at, updated_at, completed_at
                FROM payout_transactions
                WHERE pg_partner = 'PayTouch'
                  AND DATE(created_at) = CURDATE()
                ORDER BY created_at DESC
            """)
            
            today_txns = cursor.fetchall()
            
            if not today_txns:
                print("❌ No PayTouch transactions found for today")
                return
            
            print(f"📊 Found {len(today_txns)} PayTouch transactions today")
            print("-" * 80)
            
            # Analyze each transaction
            callback_received = 0
            callback_missing = 0
            status_mismatch = 0
            successful_txns = 0
            failed_txns = 0
            pending_txns = 0
            
            paytouch_service = PayTouchService()
            
            for i, txn in enumerate(today_txns, 1):
                print(f"\n{i}. Transaction: {txn['reference_id']}")
                print(f"   TXN ID: {txn['txn_id']}")
                print(f"   PG TXN ID: {txn['pg_txn_id']}")
                print(f"   Status: {txn['status']}")
                print(f"   Amount: ₹{txn['amount']}")
                print(f"   Created: {txn['created_at']}")
                print(f"   UTR: {txn['utr'] or 'None'}")
                
                # Count status
                if txn['status'] == 'SUCCESS':
                    successful_txns += 1
                elif txn['status'] == 'FAILED':
                    failed_txns += 1
                else:
                    pending_txns += 1
                
                # Check if callback was received (look for callback logs)
                cursor.execute("""
                    SELECT 
                        callback_url, request_data, response_code, response_data,
                        created_at
                    FROM callback_logs
                    WHERE txn_id = %s
                      AND callback_url LIKE %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (txn['txn_id'], '%paytouch%'))
                
                callback_log = cursor.fetchone()
                
                if callback_log:
                    print(f"   ✅ Callback received at: {callback_log['created_at']}")
                    callback_received += 1
                else:
                    print(f"   ❌ No callback received")
                    callback_missing += 1
                
                # Check wallet deduction for successful transactions
                if txn['status'] == 'SUCCESS' and txn['merchant_id']:
                    cursor.execute("""
                        SELECT 
                            txn_type, amount, balance_before, balance_after,
                            description, created_at
                        FROM merchant_wallet_transactions
                        WHERE reference_id = %s AND txn_type = 'DEBIT'
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (txn['txn_id'],))
                    
                    wallet_debit = cursor.fetchone()
                    
                    if wallet_debit:
                        print(f"   💰 Wallet debited: ₹{wallet_debit['amount']} at {wallet_debit['created_at']}")
                    else:
                        print(f"   ⚠️  SUCCESS but no wallet debit found!")
                
                # Check PayTouch API status for comparison
                if txn['pg_txn_id'] or txn['reference_id']:
                    try:
                        print(f"   🔍 Checking PayTouch API...")
                        status_result = paytouch_service.check_payout_status(
                            transaction_id=txn['pg_txn_id'],
                            external_ref=txn['reference_id']
                        )
                        
                        if status_result.get('success'):
                            api_status = status_result.get('status')
                            api_utr = status_result.get('utr')
                            
                            print(f"   📡 PayTouch API Status: {api_status}")
                            print(f"   📡 PayTouch API UTR: {api_utr or 'None'}")
                            
                            # Check for status mismatch
                            if api_status != txn['status']:
                                print(f"   🔥 STATUS MISMATCH: DB={txn['status']}, API={api_status}")
                                status_mismatch += 1
                                
                                # If API shows SUCCESS but DB shows FAILED/PENDING
                                if api_status == 'SUCCESS' and txn['status'] in ['FAILED', 'PENDING', 'QUEUED']:
                                    print(f"   💡 CRITICAL: Payment succeeded but not updated in DB!")
                                    print(f"   💡 This indicates callback processing failed")
                            else:
                                print(f"   ✅ Status matches")
                                
                        else:
                            print(f"   ❌ PayTouch API Error: {status_result.get('message')}")
                            
                    except Exception as e:
                        print(f"   ❌ API Check Error: {e}")
                
                print(f"   " + "-" * 60)
            
            # Summary
            print(f"\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Total Transactions: {len(today_txns)}")
            print(f"Successful: {successful_txns}")
            print(f"Failed: {failed_txns}")
            print(f"Pending/Other: {pending_txns}")
            print(f"")
            print(f"Callback Analysis:")
            print(f"  Callbacks Received: {callback_received}")
            print(f"  Callbacks Missing: {callback_missing}")
            print(f"  Status Mismatches: {status_mismatch}")
            
            if callback_missing > 0:
                print(f"\n⚠️  WARNING: {callback_missing} transactions missing callbacks!")
                print(f"   This indicates PayTouch is not sending callbacks properly")
            
            if status_mismatch > 0:
                print(f"\n🔥 CRITICAL: {status_mismatch} transactions have status mismatches!")
                print(f"   These need immediate attention")
            
            # Show recent callback activity
            print(f"\n" + "-" * 80)
            print("RECENT PAYTOUCH CALLBACK ACTIVITY")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    cl.txn_id, pt.reference_id, cl.response_code, 
                    cl.created_at, pt.status
                FROM callback_logs cl
                JOIN payout_transactions pt ON cl.txn_id = pt.txn_id
                WHERE pt.pg_partner = 'PayTouch'
                  AND DATE(cl.created_at) = CURDATE()
                ORDER BY cl.created_at DESC
                LIMIT 10
            """)
            
            recent_callbacks = cursor.fetchall()
            
            if recent_callbacks:
                for cb in recent_callbacks:
                    print(f"  {cb['created_at']}: {cb['reference_id']} → {cb['response_code']} (Status: {cb['status']})")
            else:
                print("  No PayTouch callbacks received today!")
            
            print("=" * 80)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def check_specific_paytouch_transaction(reference_id):
    """Check a specific PayTouch transaction by reference ID"""
    
    print("=" * 80)
    print(f"Checking Specific PayTouch Transaction: {reference_id}")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        print("ERROR: Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Find transaction by reference_id or pg_txn_id
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, charge_amount, net_amount,
                    status, pg_txn_id, utr, error_message,
                    created_at, updated_at, completed_at
                FROM payout_transactions
                WHERE (reference_id = %s OR pg_txn_id = %s)
                  AND pg_partner = 'PayTouch'
                ORDER BY created_at DESC
                LIMIT 1
            """, (reference_id, reference_id))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"❌ Transaction not found: {reference_id}")
                
                # Search in all transactions (maybe not PayTouch)
                cursor.execute("""
                    SELECT 
                        txn_id, reference_id, pg_partner, status, amount,
                        created_at
                    FROM payout_transactions
                    WHERE reference_id = %s OR pg_txn_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (reference_id, reference_id))
                
                all_txns = cursor.fetchall()
                
                if all_txns:
                    print(f"\nFound {len(all_txns)} transaction(s) with this reference:")
                    for t in all_txns:
                        print(f"  - {t['reference_id']} | {t['pg_partner']} | {t['status']} | ₹{t['amount']} | {t['created_at']}")
                
                return
            
            print(f"✅ Transaction found:")
            print(f"   TXN ID: {txn['txn_id']}")
            print(f"   Reference: {txn['reference_id']}")
            print(f"   PG TXN ID: {txn['pg_txn_id']}")
            print(f"   Status: {txn['status']}")
            print(f"   Amount: ₹{txn['amount']}")
            print(f"   Created: {txn['created_at']}")
            print(f"   Updated: {txn['updated_at']}")
            print(f"   UTR: {txn['utr'] or 'None'}")
            
            # Check PayTouch API
            paytouch_service = PayTouchService()
            status_result = paytouch_service.check_payout_status(
                transaction_id=txn['pg_txn_id'],
                external_ref=txn['reference_id']
            )
            
            if status_result.get('success'):
                api_status = status_result.get('status')
                api_utr = status_result.get('utr')
                
                print(f"\n📡 PayTouch API Response:")
                print(f"   Status: {api_status}")
                print(f"   UTR: {api_utr or 'None'}")
                
                if api_status != txn['status']:
                    print(f"\n🔥 STATUS MISMATCH DETECTED!")
                    print(f"   Database: {txn['status']}")
                    print(f"   PayTouch API: {api_status}")
                    
                    if api_status == 'SUCCESS':
                        print(f"\n💡 SOLUTION: Payment was successful but callback failed")
                        print(f"   Run the sync script to update status")
                else:
                    print(f"\n✅ Status matches between DB and PayTouch")
            else:
                print(f"\n❌ PayTouch API Error: {status_result.get('message')}")
            
            # Check callback logs
            cursor.execute("""
                SELECT 
                    callback_url, request_data, response_code, response_data,
                    created_at
                FROM callback_logs
                WHERE txn_id = %s
                ORDER BY created_at DESC
                LIMIT 3
            """, (txn['txn_id'],))
            
            callback_logs = cursor.fetchall()
            
            print(f"\n📞 Callback History:")
            if callback_logs:
                for log in callback_logs:
                    print(f"   {log['created_at']}: {log['response_code']} to {log['callback_url']}")
            else:
                print(f"   No callbacks found")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Check specific transaction
        reference_id = sys.argv[1]
        check_specific_paytouch_transaction(reference_id)
    else:
        # Check all today's transactions
        check_paytouch_callbacks_today()