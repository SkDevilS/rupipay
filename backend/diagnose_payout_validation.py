#!/usr/bin/env python3
"""
Diagnostic script to check why payout validation is not working
"""

import sys
from database import get_db_connection

def diagnose_merchant_payout(merchant_id):
    """Diagnose merchant payout validation issue"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print(f"\n{'='*80}")
            print(f"DIAGNOSING PAYOUT VALIDATION FOR: {merchant_id}")
            print(f"{'='*80}\n")
            
            # Step 1: Check approved fund requests
            print("STEP 1: Checking Approved Fund Requests")
            print("-" * 80)
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
            """, (merchant_id,))
            fund_requests = cursor.fetchall()
            
            total_approved = 0
            if fund_requests:
                print(f"{'Request ID':<20} {'Amount':>12} {'Status':<12} {'Created':<20} {'Approved'}")
                print("-" * 80)
                for req in fund_requests:
                    amount = float(req['amount'])
                    if req['status'] == 'APPROVED':
                        total_approved += amount
                    print(f"{req['request_id']:<20} ₹{amount:>10.2f} {req['status']:<12} {str(req['created_at']):<20} {str(req['approved_at']) if req['approved_at'] else 'N/A'}")
            else:
                print("No fund requests found")
            
            print(f"\n✓ Total Approved Funds: ₹{total_approved:.2f}\n")
            
            # Step 2: Check all payouts
            print("STEP 2: Checking All Payouts")
            print("-" * 80)
            cursor.execute("""
                SELECT 
                    txn_id,
                    reference_id,
                    order_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    created_at
                FROM payout_transactions
                WHERE merchant_id = %s
                ORDER BY created_at DESC
            """, (merchant_id,))
            payouts = cursor.fetchall()
            
            total_all_payouts = 0
            total_active_payouts = 0
            
            if payouts:
                print(f"{'TXN ID':<15} {'Order ID':<20} {'Amount':>10} {'Charges':>10} {'Net':>10} {'Status':<12} {'Created'}")
                print("-" * 80)
                for payout in payouts:
                    amount = float(payout['amount'])
                    charge = float(payout['charge_amount'])
                    net = float(payout['net_amount'])
                    status = payout['status']
                    
                    total_all_payouts += amount
                    if status in ('SUCCESS', 'QUEUED', 'INITIATED', 'INPROCESS'):
                        total_active_payouts += amount
                    
                    print(f"{payout['txn_id']:<15} {payout['order_id']:<20} ₹{amount:>8.2f} ₹{charge:>8.2f} ₹{net:>8.2f} {status:<12} {payout['created_at']}")
            else:
                print("No payouts found")
            
            print(f"\n✓ Total All Payouts: ₹{total_all_payouts:.2f}")
            print(f"✓ Total Active Payouts (SUCCESS/QUEUED/INITIATED/INPROCESS): ₹{total_active_payouts:.2f}\n")
            
            # Step 3: Calculate available balance
            print("STEP 3: Balance Calculation")
            print("-" * 80)
            available_balance = total_approved - total_active_payouts
            print(f"Approved Funds:        ₹{total_approved:.2f}")
            print(f"Active Payouts:      - ₹{total_active_payouts:.2f}")
            print(f"{'='*40}")
            print(f"Available Balance:     ₹{available_balance:.2f}")
            
            if available_balance < 0:
                print(f"\n⚠️  CRITICAL: NEGATIVE BALANCE DETECTED!")
                print(f"This means payouts were processed without proper validation!\n")
            
            # Step 4: Check the most recent payout
            if payouts:
                print("\nSTEP 4: Analyzing Most Recent Payout")
                print("-" * 80)
                recent = payouts[0]
                recent_amount = float(recent['amount'])
                recent_charge = float(recent['charge_amount'])
                recent_total = recent_amount + recent_charge
                
                print(f"Transaction ID:     {recent['txn_id']}")
                print(f"Order ID:           {recent['order_id']}")
                print(f"Amount:             ₹{recent_amount:.2f}")
                print(f"Charges:            ₹{recent_charge:.2f}")
                print(f"Total Deduction:    ₹{recent_total:.2f}")
                print(f"Status:             {recent['status']}")
                print(f"Created:            {recent['created_at']}")
                
                # Calculate what balance was before this payout
                balance_before_recent = available_balance + recent_amount
                print(f"\nBalance before this payout: ₹{balance_before_recent:.2f}")
                print(f"Required for payout:        ₹{recent_total:.2f}")
                
                if recent_total > balance_before_recent:
                    print(f"\n❌ VALIDATION FAILED!")
                    print(f"This payout should have been REJECTED!")
                    print(f"Shortfall: ₹{recent_total - balance_before_recent:.2f}")
                else:
                    print(f"\n✅ This payout had sufficient balance")
            
            # Step 5: Check backend logs for errors
            print(f"\n{'='*80}")
            print("RECOMMENDATIONS:")
            print("-" * 80)
            print("1. Check if backend service was restarted after deployment")
            print("2. Verify the deployed code matches the local changes")
            print("3. Check backend logs: sudo journalctl -u moneyone-backend -n 100")
            print("4. Test with a small amount to verify validation is working")
            print(f"{'='*80}\n")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_payout_validation.py <merchant_id>")
        print("Example: python diagnose_payout_validation.py MERCHANT001")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    diagnose_merchant_payout(merchant_id)
