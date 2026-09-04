#!/usr/bin/env python3
"""
Test script to verify payout balance validation
"""

import sys
from database import get_db_connection

def check_merchant_balance(merchant_id):
    """Check merchant wallet balance and payout history"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print(f"\n{'='*60}")
            print(f"Checking balance for merchant: {merchant_id}")
            print(f"{'='*60}\n")
            
            # Get wallet balance from approved fund requests
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as wallet_balance
                FROM fund_requests
                WHERE merchant_id = %s AND status = 'APPROVED'
            """, (merchant_id,))
            wallet_balance = float(cursor.fetchone()['wallet_balance'])
            print(f"✓ Approved Fund Requests: ₹{wallet_balance:.2f}")
            
            # Get total payouts by status
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    COALESCE(SUM(amount), 0) as total_amount
                FROM payout_transactions
                WHERE merchant_id = %s
                GROUP BY status
                ORDER BY status
            """, (merchant_id,))
            payouts_by_status = cursor.fetchall()
            
            print(f"\n📊 Payouts by Status:")
            total_all_payouts = 0
            for row in payouts_by_status:
                print(f"   {row['status']:15} : Count={row['count']:3}, Amount=₹{float(row['total_amount']):.2f}")
                total_all_payouts += float(row['total_amount'])
            
            # Get total payouts (SUCCESS, QUEUED, INITIATED, INPROCESS)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_payouts
                FROM payout_transactions
                WHERE merchant_id = %s AND status IN ('SUCCESS', 'QUEUED', 'INITIATED', 'INPROCESS')
            """, (merchant_id,))
            total_payouts = float(cursor.fetchone()['total_payouts'])
            print(f"\n✓ Total Payouts (SUCCESS/QUEUED/INITIATED/INPROCESS): ₹{total_payouts:.2f}")
            
            # Calculate available balance
            available_balance = wallet_balance - total_payouts
            print(f"\n{'='*60}")
            print(f"💰 Available Balance: ₹{available_balance:.2f}")
            print(f"{'='*60}\n")
            
            # Show recent payouts
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    order_id,
                    amount,
                    charge_amount,
                    status,
                    created_at
                FROM payout_transactions
                WHERE merchant_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (merchant_id,))
            recent_payouts = cursor.fetchall()
            
            if recent_payouts:
                print("📋 Recent Payouts (Last 10):")
                print(f"{'TXN ID':<15} {'Order ID':<20} {'Amount':>10} {'Charges':>10} {'Status':<12} {'Created At'}")
                print("-" * 100)
                for payout in recent_payouts:
                    print(f"{payout['txn_id']:<15} {payout['order_id']:<20} ₹{float(payout['amount']):>8.2f} ₹{float(payout['charge_amount']):>8.2f} {payout['status']:<12} {payout['created_at']}")
            
            # Show fund requests
            cursor.execute("""
                SELECT 
                    request_id,
                    amount,
                    status,
                    created_at,
                    approved_at
                FROM fund_requests
                WHERE merchant_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (merchant_id,))
            fund_requests = cursor.fetchall()
            
            if fund_requests:
                print(f"\n💵 Recent Fund Requests (Last 5):")
                print(f"{'Request ID':<20} {'Amount':>10} {'Status':<12} {'Created At':<20} {'Approved At'}")
                print("-" * 100)
                for req in fund_requests:
                    approved = req['approved_at'] if req['approved_at'] else 'N/A'
                    print(f"{req['request_id']:<20} ₹{float(req['amount']):>8.2f} {req['status']:<12} {str(req['created_at']):<20} {str(approved)}")
            
            print(f"\n{'='*60}")
            print(f"Summary:")
            print(f"  Wallet Balance (Approved Funds): ₹{wallet_balance:.2f}")
            print(f"  Total Payouts (Active):          ₹{total_payouts:.2f}")
            print(f"  Available Balance:                ₹{available_balance:.2f}")
            print(f"{'='*60}\n")
            
            if available_balance < 0:
                print("⚠️  WARNING: Negative balance detected!")
            elif available_balance == 0:
                print("⚠️  WARNING: Zero balance - no payouts can be processed")
            else:
                print(f"✅ Balance is positive - can process payouts up to ₹{available_balance:.2f}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_payout_balance_validation.py <merchant_id>")
        print("Example: python test_payout_balance_validation.py MERCHANT001")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    check_merchant_balance(merchant_id)
