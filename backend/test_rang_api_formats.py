#!/usr/bin/env python3
"""
Test different RefID formats with Rang API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rang_service import RangService
from database import get_db_connection
import requests
import json

def get_sample_transaction():
    """Get a sample transaction to test with"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT txn_id, order_id, pg_txn_id
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND pg_txn_id IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        txn = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return txn
        
    except Exception as e:
        print(f"Error getting transaction: {e}")
        return None

def test_different_refid_formats(rang_service, base_txn):
    """Test different RefID formats"""
    print("TESTING DIFFERENT REFID FORMATS")
    print("=" * 50)
    
    if not base_txn:
        print("❌ No transaction available for testing")
        return
    
    # Different formats to test
    test_formats = [
        ("Original Order ID", base_txn['order_id']),
        ("TXN ID", base_txn['txn_id']),
        ("PG TXN ID", base_txn['pg_txn_id']),
    ]
    
    # Add some variations if we have the data
    if base_txn['order_id']:
        # Remove ORD prefix if present
        clean_order_id = base_txn['order_id'].replace('ORD', '')
        test_formats.append(("Order ID without ORD", clean_order_id))
    
    url = f"{rang_service.base_url}/api/payin/v1/status-check"
    headers = rang_service.get_headers()
    
    for format_name, ref_id in test_formats:
        if not ref_id:
            continue
            
        print(f"\nTesting {format_name}: {ref_id}")
        
        payload = {
            "RefId": ref_id,
            "Service_Id": "1"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text}")
            
            if response.status_code == 200:
                print(f"  ✅ SUCCESS with format: {format_name}")
                return ref_id
            elif response.status_code != 404:
                print(f"  ⚠️ Different error (not 404) - might be progress")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    return None

def test_with_sample_data():
    """Test with some sample RefIDs that might work"""
    print("\nTESTING WITH SAMPLE DATA")
    print("=" * 50)
    
    rang_service = RangService()
    url = f"{rang_service.base_url}/api/payin/v1/status-check"
    headers = rang_service.get_headers()
    
    # Sample RefIDs to test (these might be from Rang documentation)
    sample_refids = [
        "12345678901234567890",  # 20 digit number
        "TXN123456789",          # TXN prefix
        "PAY123456789",          # PAY prefix
        "1234567890",            # 10 digit number
        "TEST123",               # Simple test
    ]
    
    for ref_id in sample_refids:
        print(f"\nTesting sample RefID: {ref_id}")
        
        payload = {
            "RefId": ref_id,
            "Service_Id": "1"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text}")
            
            if response.status_code == 200:
                print(f"  ✅ SUCCESS with sample: {ref_id}")
                return ref_id
            elif response.status_code != 404:
                print(f"  ⚠️ Different response - check this format")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    return None

def main():
    print("RANG API FORMAT TESTING")
    print("=" * 40)
    
    try:
        rang_service = RangService()
        print(f"Testing with base URL: {rang_service.base_url}")
        
        # Get a sample transaction
        sample_txn = get_sample_transaction()
        
        if sample_txn:
            print(f"\nUsing transaction:")
            print(f"  TXN ID: {sample_txn['txn_id']}")
            print(f"  Order ID: {sample_txn['order_id']}")
            print(f"  PG TXN ID: {sample_txn['pg_txn_id']}")
        
        # Test different formats
        working_format = test_different_refid_formats(rang_service, sample_txn)
        
        if not working_format:
            # Try sample data
            working_sample = test_with_sample_data()
            
            if working_sample:
                print(f"\n✅ Found working sample format: {working_sample}")
            else:
                print(f"\n❌ No working formats found")
                print(f"\nNext steps:")
                print(f"1. Contact Rang team for correct RefID format")
                print(f"2. Ask for API documentation")
                print(f"3. Request sample working RefID for testing")
        else:
            print(f"\n✅ Found working format: {working_format}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()