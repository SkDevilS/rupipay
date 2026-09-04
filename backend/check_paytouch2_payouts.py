#!/usr/bin/env python3
"""
Check PayTouch2 Payouts
Check status of PayTouch2 payout transactions and identify issues
"""

from database import get_db_connection
from paytouch2_service import paytouch2_service
from datetime import datetime, timedelta
import json

def check_paytouch2_payouts():
    """Check PayTouch2 payout transactions"""
    
    print("🔍 Checking PayTouch2 Payout Transactions")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get PayTouch2 transaction summary
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(amount) as total_amount,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                GROUP BY status
                ORDER BY count DESC
            """)
            
            status_summary = cursor.fetchall()
            
            if not status_summary:
                print("ℹ️  No PayTouch2 transactions found")
                return
            
            print("📊 PayTouch2 Transaction Summary:")
            print("-" * 60)
            print(f"{'Status':<12} {'Count':<8} {'Total Amount':<15} {'Date Range'}")
            print("-" * 60)
            
            total_transactions = 0
            total_amount = 0
            
            for row in status_summary:
                total_transactions += row['count']
                total_amount += float(row['total_amount'])
                
                oldest = row['oldest'].strftime('%m-%d') if row['oldest'] else 'N/A'
                newest = row['newest'].strftime('%m-%d') if row['newest'] else 'N/A'
                date_range = f"{oldest} to {newest}" if oldest != newest else oldest
                
                print(f"{row['status']:<12} {row['count']:<8} ₹{row['total_amount']:<14.2f} {date_range}")
            
            print("-" * 60)
            print(f"{'TOTAL':<12} {total_transactions:<8} ₹{total_amount:<14.2f}")
            
            # Check pending transactions
            print(f"\n🔄 Pending PayTouch2 Transactions:")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, status, pg_txn_id, created_at,
                    TIMESTAMPDIFF(MINUTE, created_at, NOW()) as age_minutes
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                  AND status IN ('PENDING', 'QUEUED', 'INPROCESS', 'INITIATED')
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            pending_txns = cursor.fetchall()
            
            if pending_txns:
                print(f"{'TXN ID':<15} {'Type':<8} {'Amount':<8} {'Status':<10} {'Age (min)':<10} {'PG TXN ID':<15}")
                print("-" * 80)
                
                for txn in pending_txns:
                    txn_type = "ADMIN" if txn['admin_id'] else "MERCHANT"
                    pg_txn_display = (txn['pg_txn_id'][:15] if txn['pg_txn_id'] else 'N/A')
                    
                    print(f"{txn['txn_id']:<15} {txn_type:<8} ₹{txn['amount']:<7} {txn['status']:<10} {txn['age_minutes']:<10} {pg_txn_display:<15}")
                
                # Check for stuck transactions (older than 30 minutes)
                stuck_count = sum(1 for txn in pending_txns if txn['age_minutes'] > 30)
                if stuck_count > 0:
                    print(f"\n⚠️  {stuck_count} transactions are stuck (>30 minutes old)")
            else:
                print("✅ No pending PayTouch2 transactions")
            
            # Check recent successful transactions
            print(f"\n✅ Recent Successful PayTouch2 Transactions:")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    pt.txn_id, pt.reference_id, pt.merchant_id, pt.admin_id,
                    pt.amount, pt.utr, pt.completed_at,
                    COUNT(mwt.id) as wallet_deductions
                FROM payout_transactions pt
                LEFT JOIN merchant_wallet_transactions mwt ON mwt.reference_id = pt.txn_id AND mwt.txn_type = 'DEBIT'
                WHERE pt.pg_partner = 'Paytouch2'
                  AND pt.status = 'SUCCESS'
                  AND pt.completed_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY pt.txn_id
                ORDER BY pt.completed_at DESC
                LIMIT 10
            """)
            
            success_txns = cursor.fetchall()
            
            if success_txns:
                print(f"{'TXN ID':<15} {'Type':<8} {'Amount':<8} {'UTR':<15} {'Wallet':<8} {'Completed'}")
                print("-" * 80)
                
                for txn in success_txns:
                    txn_type = "ADMIN" if txn['admin_id'] else "MERCHANT"
                    utr_display = (txn['utr'][:15] if txn['utr'] else 'N/A')
                    wallet_status = "✅" if txn['wallet_deductions'] > 0 or txn['admin_id'] else "❌"
                    completed = txn['completed_at'].strftime('%m-%d %H:%M') if txn['completed_at'] else 'N/A'
                    
                    print(f"{txn['txn_id']:<15} {txn_type:<8} ₹{txn['amount']:<7} {utr_display:<15} {wallet_status:<8} {completed}")
            else:
                print("ℹ️  No recent successful PayTouch2 transactions")
            
            # Check failed transactions
            print(f"\n❌ Recent Failed PayTouch2 Transactions:")
            print("-" * 80)
            
            cursor.execute("""
                SELECT 
                    txn_id, reference_id, merchant_id, admin_id,
                    amount, error_message, completed_at
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch2'
                  AND status = 'FAILED'
                  AND completed_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY completed_at DESC
                LIMIT 10
            """)
            
            failed_txns = cursor.fetchall()
            
            if failed_txns:
                print(f"{'TXN ID':<15} {'Type':<8} {'Amount':<8} {'Error':<30} {'Failed'}")
                print("-" * 80)
                
                for txn in failed_txns:
                    txn_type = "ADMIN" if txn['admin_id'] else "MERCHANT"
                    error_display = (txn['error_message'][:30] if txn['error_message'] else 'N/A')
                    failed = txn['completed_at'].strftime('%m-%d %H:%M') if txn['completed_at'] else 'N/A'
                    
                    print(f"{txn['txn_id']:<15} {txn_type:<8} ₹{txn['amount']:<7} {error_display:<30} {failed}")
            else:
                print("✅ No recent failed PayTouch2 transactions")
            
            # Check wallet deduction issues
            print(f"\n💰 Wallet Deduction Issues:")
            print("-" * 60)
            
            cursor.execute("""
                SELECT 
                    pt.txn_id, pt.reference_id, pt.merchant_id,
                    pt.amount, pt.charge_amount, pt.status,
                    COUNT(mwt.id) as wallet_deductions
                FROM payout_transactions pt
                LEFT JOIN merchant_wallet_transactions mwt ON mwt.reference_id = pt.txn_id AND mwt.txn_type = 'DEBIT'
                WHERE pt.pg_partner = 'Paytouch2'
                  AND pt.status = 'SUCCESS'
                  AND pt.merchant_id IS NOT NULL
                GROUP BY pt.txn_id
                HAVING wallet_deductions = 0
                ORDER BY pt.completed_at DESC
                LIMIT 10
            """)
            
            missing_deductions = cursor.fetchall()
            
            if missing_deductions:
                print(f"⚠️  {len(missing_deductions)} SUCCESS transactions missing wallet deductions:")
                print(f"{'TXN ID':<15} {'Merchant':<12} {'Amount':<8} {'Charges':<8}")
                print("-" * 50)
                
                for txn in missing_deductions:
                    print(f"{txn['txn_id']:<15} {txn['merchant_id']:<12} ₹{txn['amount']:<7} ₹{txn['charge_amount']:<7}")
            else:
                print("✅ No missing wallet deductions found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def check_specific_paytouch2_transaction(txn_id):
    """Check specific PayTouch2 transaction"""
    
    print(f"🔍 Checking PayTouch2 Transaction: {txn_id}")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get transaction details
            cursor.execute("""
                SELECT * FROM payout_transactions
                WHERE txn_id = %s AND pg_partner = 'Paytouch2'
            """, (txn_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"❌ Transaction {txn_id} not found or not a PayTouch2 transaction")
                return
            
            print(f"📋 Transaction Details:")
            print(f"   TXN ID: {txn['txn_id']}")
            print(f"   Reference ID: {txn['reference_id']}")
            print(f"   Merchant ID: {txn['merchant_id'] or 'N/A'}")
            print(f"   Admin ID: {txn['admin_id'] or 'N/A'}")
            print(f"   Amount: ₹{txn['amount']}")
            print(f"   Charges: ₹{txn['charge_amount']}")
            print(f"   Status: {txn['status']}")
            print(f"   PG TXN ID: {txn['pg_txn_id'] or 'N/A'}")
            print(f"   UTR: {txn['utr'] or 'N/A'}")
            print(f"   Created: {txn['created_at']}")
            print(f"   Completed: {txn['completed_at'] or 'N/A'}")
            print(f"   Error: {txn['error_message'] or 'N/A'}")
            
            # Check wallet transactions
            if txn['merchant_id']:
                cursor.execute("""
                    SELECT * FROM merchant_wallet_transactions
                    WHERE reference_id = %s
                    ORDER BY created_at DESC
                """, (txn_id,))
                
                wallet_txns = cursor.fetchall()
                
                print(f"\n💰 Wallet Transactions ({len(wallet_txns)}):")
                if wallet_txns:
                    for wt in wallet_txns:
                        print(f"   - {wt['txn_type']}: ₹{wt['amount']} ({wt['created_at']})")
                        print(f"     Description: {wt['description']}")
                else:
                    print("   No wallet transactions found")
            
            # Check status from PayTouch2 API
            print(f"\n🔄 Checking status from PayTouch2 API...")
            
            try:
                status_result = paytouch2_service.check_payout_status(
                    transaction_id=txn['pg_txn_id'],
                    external_ref=txn['reference_id']
                )
                
                if status_result.get('success'):
                    print(f"   API Status: {status_result.get('status')}")
                    print(f"   API UTR: {status_result.get('utr', 'N/A')}")
                    print(f"   API Message: {status_result.get('message', 'N/A')}")
                else:
                    print(f"   ❌ API Error: {status_result.get('message')}")
                    
            except Exception as e:
                print(f"   ❌ API Exception: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        txn_id = sys.argv[1]
        check_specific_paytouch2_transaction(txn_id)
    else:
        check_paytouch2_payouts()

if __name__ == '__main__':
    main()