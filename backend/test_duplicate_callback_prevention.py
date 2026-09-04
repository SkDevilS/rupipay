#!/usr/bin/env python3
"""
Test script to verify duplicate callback prevention
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

def test_duplicate_prevention(ref_id):
    """Check if duplicate prevention is working for a transaction"""
    
    print("=" * 60)
    print("Testing Duplicate Callback Prevention")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    try:
        with conn.cursor() as cursor:
            # Get transaction details
            cursor.execute("""
                SELECT txn_id, merchant_id, status, amount
                FROM payin_transactions
                WHERE order_id = %s
            """, (ref_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"❌ Transaction not found for ref_id: {ref_id}")
                return
            
            print(f"\n📋 Transaction Details:")
            print(f"   TXN ID: {txn['txn_id']}")
            print(f"   Merchant ID: {txn['merchant_id']}")
            print(f"   Status: {txn['status']}")
            print(f"   Amount: ₹{txn['amount']}")
            
            # Check wallet credits
            cursor.execute("""
                SELECT COUNT(*) as count FROM merchant_wallet_transactions
                WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
            """, (txn['txn_id'],))
            
            wallet_credits = cursor.fetchone()['count']
            
            print(f"\n💰 Wallet Credits:")
            print(f"   Count: {wallet_credits}")
            if wallet_credits == 0:
                print(f"   Status: ⚠ No wallet credit found")
            elif wallet_credits == 1:
                print(f"   Status: ✅ Single credit (correct)")
            else:
                print(f"   Status: ❌ Multiple credits (duplicate issue!)")
            
            # Check callback logs
            cursor.execute("""
                SELECT COUNT(*) as total_callbacks,
                       SUM(CASE WHEN response_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) as success_callbacks
                FROM callback_logs
                WHERE merchant_id = %s AND txn_id = %s
            """, (txn['merchant_id'], txn['txn_id']))
            
            callback_stats = cursor.fetchone()
            
            print(f"\n📞 Callback Logs:")
            print(f"   Total Callbacks: {callback_stats['total_callbacks']}")
            print(f"   Success Callbacks: {callback_stats['success_callbacks']}")
            
            if callback_stats['success_callbacks'] == 0:
                print(f"   Status: ⚠ No successful callback sent")
            elif callback_stats['success_callbacks'] == 1:
                print(f"   Status: ✅ Single callback (correct)")
            else:
                print(f"   Status: ❌ Multiple callbacks (duplicate issue!)")
            
            # Show callback details
            cursor.execute("""
                SELECT created_at, response_code, 
                       LEFT(request_data, 100) as request_preview,
                       LEFT(response_data, 100) as response_preview
                FROM callback_logs
                WHERE merchant_id = %s AND txn_id = %s
                ORDER BY created_at DESC
            """, (txn['merchant_id'], txn['txn_id']))
            
            callbacks = cursor.fetchall()
            
            if callbacks:
                print(f"\n📝 Callback History:")
                for i, cb in enumerate(callbacks, 1):
                    print(f"   {i}. Time: {cb['created_at']}")
                    print(f"      Response Code: {cb['response_code']}")
                    print(f"      Request: {cb['request_preview']}...")
                    print(f"      Response: {cb['response_preview']}...")
            
            print("\n" + "=" * 60)
            
            # Summary
            if wallet_credits == 1 and callback_stats['success_callbacks'] <= 1:
                print("✅ RESULT: No duplicate issue detected")
            else:
                print("❌ RESULT: Duplicate issue detected!")
                print(f"   - Wallet credits: {wallet_credits} (should be 1)")
                print(f"   - Success callbacks: {callback_stats['success_callbacks']} (should be 1)")
            
            print("=" * 60)
            
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_duplicate_callback_prevention.py <ref_id>")
        print("Example: python3 test_duplicate_callback_prevention.py 20260306135756756975")
        sys.exit(1)
    
    ref_id = sys.argv[1]
    test_duplicate_prevention(ref_id)
