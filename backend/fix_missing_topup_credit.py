#!/usr/bin/env python3
"""
Fix missing topup credit - manually credit merchant wallet for approved fund request
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime

def fix_missing_topup(request_id):
    """Manually credit merchant wallet for an approved fund request that wasn't credited"""
    print("\n" + "=" * 80)
    print("FIX MISSING TOPUP CREDIT")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get the fund request
            print(f"\n1. Checking fund request: {request_id}")
            cursor.execute("""
                SELECT request_id, merchant_id, amount, status, processed_at
                FROM fund_requests
                WHERE request_id = %s
            """, (request_id,))
            
            fund_req = cursor.fetchone()
            if not fund_req:
                print(f"   ❌ Fund request not found")
                conn.close()
                return False
            
            if fund_req['status'] != 'APPROVED':
                print(f"   ❌ Fund request is not APPROVED (status: {fund_req['status']})")
                conn.close()
                return False
            
            print(f"   ✓ Found APPROVED fund request")
            print(f"   Merchant: {fund_req['merchant_id']}")
            print(f"   Amount: ₹{float(fund_req['amount']):,.2f}")
            print(f"   Processed: {fund_req['processed_at']}")
            
            # Check if wallet transaction already exists
            print(f"\n2. Checking if wallet transaction exists...")
            cursor.execute("""
                SELECT txn_id FROM merchant_wallet_transactions
                WHERE reference_id = %s
            """, (request_id,))
            
            existing = cursor.fetchone()
            if existing:
                print(f"   ⚠️  Wallet transaction already exists: {existing['txn_id']}")
                print(f"   This topup was already credited. No action needed.")
                conn.close()
                return True
            
            print(f"   ✓ No wallet transaction found - needs to be created")
            
            # Get current merchant wallet balance
            print(f"\n3. Getting current merchant wallet balance...")
            cursor.execute("""
                SELECT settled_balance, balance FROM merchant_wallet
                WHERE merchant_id = %s
            """, (fund_req['merchant_id'],))
            
            wallet = cursor.fetchone()
            if not wallet:
                print(f"   Creating new wallet entry...")
                cursor.execute("""
                    INSERT INTO merchant_wallet (merchant_id, balance, settled_balance, unsettled_balance)
                    VALUES (%s, %s, %s, 0.00)
                """, (fund_req['merchant_id'], fund_req['amount'], fund_req['amount']))
                settled_before = 0.00
            else:
                settled_before = float(wallet['settled_balance'])
                print(f"   Current settled balance: ₹{settled_before:,.2f}")
            
            settled_after = settled_before + float(fund_req['amount'])
            
            # Update merchant wallet
            print(f"\n4. Crediting merchant wallet...")
            cursor.execute("""
                UPDATE merchant_wallet
                SET settled_balance = %s, balance = %s, last_updated = NOW()
                WHERE merchant_id = %s
            """, (settled_after, settled_after, fund_req['merchant_id']))
            
            # Create wallet transaction
            txn_id = f"MWT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor.execute("""
                INSERT INTO merchant_wallet_transactions
                (merchant_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id, created_at)
                VALUES (%s, %s, 'CREDIT', %s, %s, %s, %s, %s, NOW())
            """, (
                fund_req['merchant_id'], txn_id, fund_req['amount'],
                settled_before, settled_after,
                f"Fund topup approved - {request_id} (manually fixed)",
                request_id
            ))
            
            print(f"   ✓ Created wallet transaction: {txn_id}")
            
            conn.commit()
            
            print("\n" + "=" * 80)
            print("✅ SUCCESS - Missing topup credit fixed")
            print("=" * 80)
            print(f"\nFund Request: {request_id}")
            print(f"Merchant: {fund_req['merchant_id']}")
            print(f"Amount: ₹{float(fund_req['amount']):,.2f}")
            print(f"\nOld Balance: ₹{settled_before:,.2f}")
            print(f"New Balance: ₹{settled_after:,.2f}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fix_missing_topup_credit.py <request_id>")
        print("Example: python3 fix_missing_topup_credit.py FR4122CE51E772")
        sys.exit(1)
    
    request_id = sys.argv[1]
    
    print(f"\nYou are about to manually credit the merchant wallet")
    print(f"for fund request: {request_id}")
    
    confirm = input("\nProceed? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled")
        sys.exit(0)
    
    success = fix_missing_topup(request_id)
    sys.exit(0 if success else 1)
