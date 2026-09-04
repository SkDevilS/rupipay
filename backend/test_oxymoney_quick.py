#!/usr/bin/env python3
"""
Quick Oxymoney Payin Test Script
Fast testing of Oxymoney_Grosmart payin integration

Usage:
    python test_oxymoney_quick.py
    python test_oxymoney_quick.py --amount 500
    python test_oxymoney_quick.py --merchant MERCHANT123
"""

import sys
import os
import argparse
import json
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import get_db_connection
from oxymoney_grosmart_service import oxymoney_grosmart_service

def print_separator():
    print("=" * 80)

def test_quick_payin(merchant_id=None, amount=100.00):
    """Quick payin test"""
    print_separator()
    print("OXYMONEY QUICK PAYIN TEST")
    print_separator()
    
    # Get test merchant if not provided
    if not merchant_id:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT merchant_id, full_name FROM merchants
                    WHERE is_active = 1
                    LIMIT 1
                """)
                merchant = cursor.fetchone()
                
                if merchant:
                    merchant_id = merchant['merchant_id']
                    print(f"✓ Using merchant: {merchant_id} ({merchant['full_name']})")
                else:
                    print("❌ No active merchant found")
                    return False
        finally:
            conn.close()
    
    # Generate order ID
    order_id = f"QUICK_OX_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Prepare order data
    order_data = {
        'amount': amount,
        'orderid': order_id,
        'payee_fname': 'Quick',
        'payee_lname': 'Test',
        'payee_email': 'quicktest@example.com',
        'payee_mobile': '9876543210',
        'note': 'Quick test payment',
        'expiryValue': 1,
        'callback_url': 'https://webhook.site/test-callback'
    }
    
    print(f"\n📦 Order Details:")
    print(f"  Order ID: {order_id}")
    print(f"  Amount: ₹{amount}")
    print(f"  Merchant: {merchant_id}")
    
    # Create payment intent
    print(f"\n🔄 Creating payment intent...")
    result = oxymoney_grosmart_service.create_payin_order(merchant_id, order_data)
    
    print_separator()
    
    if result.get('success'):
        print("✅ PAYMENT INTENT CREATED SUCCESSFULLY")
        print_separator()
        print(f"Transaction ID: {result.get('txn_id')}")
        print(f"Order ID: {result.get('order_id')}")
        print(f"Amount: ₹{result.get('amount')}")
        print(f"Charge: ₹{result.get('charge_amount')}")
        print(f"Net Amount: ₹{result.get('net_amount')}")
        print(f"Payment Intent ID: {result.get('payment_intent_id')}")
        print(f"VPA Used: {result.get('vpa_used')}")
        print(f"Status: {result.get('status')}")
        print(f"\n🔗 Payment URL:")
        print(f"{result.get('payment_url')}")
        print_separator()
        print("\n✓ Test completed successfully!")
        print("\nNext steps:")
        print("1. Use the payment URL to complete the payment")
        print("2. Monitor callback endpoint for status updates")
        print(f"3. Check transaction status using txn_id: {result.get('txn_id')}")
        return True
    else:
        print("❌ PAYMENT INTENT CREATION FAILED")
        print_separator()
        print(f"Error: {result.get('message')}")
        print_separator()
        return False

def test_vpa_status():
    """Check VPA status"""
    print_separator()
    print("OXYMONEY VPA STATUS")
    print_separator()
    
    stats = oxymoney_grosmart_service.get_vpa_usage_stats()
    
    if not stats:
        print("❌ Failed to get VPA stats")
        return False
    
    print(f"\n📊 VPA Usage Summary (Today):")
    print(f"Daily Limit per VPA: ₹{oxymoney_grosmart_service.vpa_daily_limit:,.2f}")
    print(f"Safety Threshold: ₹{oxymoney_grosmart_service.vpa_safety_threshold:,.2f}")
    print()
    
    for stat in stats:
        status_icon = "✓" if stat['status'] == 'AVAILABLE' else "⚠"
        print(f"{status_icon} VPA {stat['vpa_index']}: {stat['vpa']}")
        print(f"   Usage: ₹{stat['total_usage']:,.2f} ({stat['usage_percentage']}%)")
        print(f"   Transactions: {stat['transaction_count']}")
        print(f"   Remaining: ₹{stat['remaining']:,.2f}")
        print(f"   Status: {stat['status']}")
        print()
    
    available_count = sum(1 for s in stats if s['status'] == 'AVAILABLE')
    print(f"Available VPAs: {available_count} / {len(stats)}")
    print_separator()
    
    return True

def test_token():
    """Test token generation"""
    print_separator()
    print("OXYMONEY TOKEN TEST")
    print_separator()
    
    print("\n🔑 Generating access token...")
    token = oxymoney_grosmart_service.generate_access_token(force_refresh=True)
    
    if token:
        print(f"✅ Token generated successfully")
        print(f"Token: {token[:30]}...")
        print(f"Length: {len(token)} characters")
        print_separator()
        return True
    else:
        print("❌ Token generation failed")
        print_separator()
        return False

def test_status(txn_id):
    """Check transaction status"""
    print_separator()
    print("OXYMONEY TRANSACTION STATUS CHECK")
    print_separator()
    
    # Get pg_txn_id from database
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT pg_txn_id, order_id, amount, status
                FROM payin_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            txn = cursor.fetchone()
            
            if not txn:
                print(f"❌ Transaction not found: {txn_id}")
                return False
            
            print(f"\n📋 Transaction Details:")
            print(f"  Transaction ID: {txn_id}")
            print(f"  Order ID: {txn['order_id']}")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Current Status: {txn['status']}")
            print(f"  PG Txn ID: {txn['pg_txn_id']}")
            
            if not txn['pg_txn_id']:
                print("\n⚠️  No PG transaction ID found")
                return False
            
            print(f"\n🔍 Checking status with Oxymoney...")
            result = oxymoney_grosmart_service.check_transaction_status(
                txn_id=txn['pg_txn_id']
            )
            
            print_separator()
            
            if result.get('success'):
                print("✅ STATUS CHECK SUCCESSFUL")
                print_separator()
                print(f"Status: {result.get('status')}")
                print(f"Txn Status: {result.get('txn_status')}")
                print(f"Amount: {result.get('amount')}")
                print(f"RRN: {result.get('rrn')}")
                print(f"Client Ref ID: {result.get('client_ref_id')}")
                print(f"Merchant VPA: {result.get('merchant_vpa')}")
                print(f"Customer VPA: {result.get('customer_vpa')}")
                print_separator()
                return True
            else:
                print("❌ STATUS CHECK FAILED")
                print_separator()
                print(f"Error: {result.get('message')}")
                print_separator()
                return False
    finally:
        conn.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Quick Oxymoney Payin Test')
    parser.add_argument('--amount', type=float, default=100.00, help='Transaction amount')
    parser.add_argument('--merchant', type=str, help='Merchant ID')
    parser.add_argument('--vpa-status', action='store_true', help='Check VPA status only')
    parser.add_argument('--token', action='store_true', help='Test token generation only')
    parser.add_argument('--status', type=str, help='Check status of transaction ID')
    
    args = parser.parse_args()
    
    try:
        if args.vpa_status:
            test_vpa_status()
        elif args.token:
            test_token()
        elif args.status:
            test_status(args.status)
        else:
            test_quick_payin(args.merchant, args.amount)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
