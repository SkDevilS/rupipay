#!/usr/bin/env python3
"""
Test Payin CSV Download Endpoint
Diagnoses the CSV download issue
"""

import requests
import sys

# Test the CSV download endpoint
def test_csv_download():
    print("=" * 60)
    print("TESTING PAYIN CSV DOWNLOAD ENDPOINT")
    print("=" * 60)
    print()
    
    # You need to replace this with a valid admin token
    token = input("Enter admin JWT token (from browser localStorage): ").strip()
    
    if not token:
        print("❌ Token required")
        sys.exit(1)
    
    # Test endpoint
    url = "http://localhost:5000/api/payin/admin/transactions/download-csv"
    
    print(f"Testing: {url}")
    print()
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    try:
        print("Sending request...")
        response = requests.get(url, headers=headers, stream=True)
        
        print(f"Status Code: {response.status_code}")
        print()
        print("Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print()
        
        if response.status_code == 200:
            # Read first 500 bytes
            content = b''
            for chunk in response.iter_content(chunk_size=500):
                content += chunk
                break
            
            print("First 500 bytes of response:")
            print("-" * 60)
            print(content.decode('utf-8', errors='ignore'))
            print("-" * 60)
            print()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            content_disposition = response.headers.get('Content-Disposition', '')
            
            print("✅ Endpoint is responding")
            print()
            print("Diagnosis:")
            if 'text/csv' in content_type:
                print("  ✅ Content-Type is correct (text/csv)")
            else:
                print(f"  ❌ Content-Type is wrong: {content_type}")
                print("     Should be: text/csv")
            
            if 'attachment' in content_disposition:
                print("  ✅ Content-Disposition has 'attachment'")
            else:
                print(f"  ❌ Content-Disposition is wrong: {content_disposition}")
                print("     Should contain: attachment; filename=...")
            
            if content.startswith(b'Transaction ID'):
                print("  ✅ CSV content looks correct")
            else:
                print("  ❌ CSV content doesn't start with expected header")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_csv_download()
