#!/usr/bin/env python3
"""
Test Rang API with proper token authentication
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
from database import get_db_connection

def test_token_generation():
    """Test Rang token generation"""
    print("TESTING RANG TOKEN GENERATION")
    print("=" * 50)
    
    try:
        rang_service = RangService()
        
        print(f"Base URL: {rang_service.base_url}")
        print(f"MID: {rang_service.mid}")
        print(f"Email: {rang_service.email}")
        
        # Generate token
        print("\n🔑 Generating authentication token...")
        token_success = rang_service.generate_token()
        
        if token_success:
            print(f"✅ Token generated successfully!")
            print(f"Token: {rang_service.token[:20]}..." if rang_service.token else "None")
            print(f"Expires at: {rang_service.token_expires_at}")
            return rang_service
        else:
            print(f"❌ Token generation failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_status_check_with_token(rang_service):
    """Test status check with authentication token"""
    print("\nTESTING STATUS CHECK WITH TOKEN")
    print("=" * 50)
    
    # Get a recent transaction
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT txn_id, order_id, pg_txn_id, amount, status
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        txn = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not txn:
            print("❌ No Rang transactions found")
            return
        
        print(f"Testing with transaction:")
        print(f"  Order ID: {txn['order_id']}")
        print(f"  PG TXN ID: {txn['pg_txn_id']}")
        print(f"  Status: {txn['status']}")
        
        # Test with Order ID
        print(f"\n🔍 Testing with Order ID: {txn['order_id']}")
        result1 = rang_service.check_payment_status(txn['order_id'])
        
        print(f"Result: {result1}")
        
        if result1['success']:
            print("✅ SUCCESS with Order ID!")
            return True
        
        # Test with PG TXN ID if Order ID failed
        if txn['pg_txn_id']:
            print(f"\n🔍 Testing with PG TXN ID: {txn['pg_txn_id']}")
            result2 = rang_service.check_payment_status(txn['pg_txn_id'])
            
            print(f"Result: {result2}")
            
            if result2['success']:
                print("✅ SUCCESS with PG TXN ID!")
                return True
        
        print("❌ Both Order ID and PG TXN ID failed")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("RANG API TEST WITH TOKEN AUTHENTICATION")
    print("=" * 60)
    
    # Step 1: Generate token
    rang_service = test_token_generation()
    
    if not rang_service:
        print("\n❌ Cannot proceed without token")
        return
    
    # Step 2: Test status check with token
    success = test_status_check_with_token(rang_service)
    
    print(f"\n" + "=" * 60)
    if success:
        print("✅ RANG API WORKING WITH TOKEN AUTHENTICATION!")
    else:
        print("❌ RANG API STILL NOT WORKING")
        print("\nPossible issues:")
        print("1. Wrong RefID format")
        print("2. Transaction doesn't exist on Rang side")
        print("3. Different API endpoint needed")
        print("4. Additional authentication required")
    print("=" * 60)

if __name__ == "__main__":
    main()