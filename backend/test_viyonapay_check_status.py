"""
Test script for VIYONAPAY check status API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from viyonapay_service import ViyonapayService

def test_check_status():
    """Test VIYONAPAY check payment status"""
    
    service = ViyonapayService()
    
    # Test with a sample order_id (replace with actual order_id from your system)
    order_id = input("Enter order_id to check status: ").strip()
    
    if not order_id:
        print("❌ Order ID is required")
        return
    
    print(f"\n🔍 Checking status for order: {order_id}")
    print("=" * 60)
    
    result = service.check_payment_status(order_id)
    
    print("\n📊 Status Check Result:")
    print("=" * 60)
    
    if result.get('success'):
        print(f"✅ Success: {result.get('success')}")
        print(f"📌 Status: {result.get('status')}")
        print(f"🆔 Transaction ID: {result.get('transaction_id')}")
        print(f"💳 Payment Mode: {result.get('payment_mode')}")
        print(f"📝 Order ID: {result.get('order_id')}")
        print(f"💰 Amount: {result.get('amount')}")
        print(f"🏦 Bank Reference: {result.get('bank_reference_number')}")
        print(f"💬 Message: {result.get('message')}")
    else:
        print(f"❌ Failed: {result.get('message')}")
    
    print("=" * 60)

if __name__ == '__main__':
    test_check_status()
