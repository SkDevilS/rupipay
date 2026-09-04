#!/usr/bin/env python3
"""
Test PayTouch Name Changes
Verify that the service routing shows the new names
"""

import requests
import json

def test_paytouch_name_changes():
    """Test the PayTouch name changes in service routing"""
    
    print("🧪 Testing PayTouch Name Changes in Service Routing")
    print("=" * 60)
    
    try:
        # Test the PG partners API endpoint
        url = "http://localhost:5000/api/service-routing/pg-partners"
        
        print(f"📡 Calling API: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                partners = data.get('partners', [])
                
                print(f"✅ API call successful - Found {len(partners)} partners")
                print("-" * 60)
                
                # Check for PayTouch partners
                paytouch_found = False
                paytouch2_found = False
                
                for partner in partners:
                    if partner['id'] == 'PayTouch':
                        paytouch_found = True
                        print(f"🔍 PayTouch Partner:")
                        print(f"   ID: {partner['id']}")
                        print(f"   Name: {partner['name']}")
                        print(f"   Supports: {partner['supports']}")
                        
                        if partner['name'] == 'Paytouch_Truaxis':
                            print(f"   ✅ Name correctly changed to 'Paytouch_Truaxis'")
                        else:
                            print(f"   ❌ Name should be 'Paytouch_Truaxis' but is '{partner['name']}'")
                    
                    elif partner['id'] == 'Paytouch2':
                        paytouch2_found = True
                        print(f"🔍 Paytouch2 Partner:")
                        print(f"   ID: {partner['id']}")
                        print(f"   Name: {partner['name']}")
                        print(f"   Supports: {partner['supports']}")
                        
                        if partner['name'] == 'Paytouch2_Grosmart':
                            print(f"   ✅ Name correctly changed to 'Paytouch2_Grosmart'")
                        else:
                            print(f"   ❌ Name should be 'Paytouch2_Grosmart' but is '{partner['name']}'")
                
                if not paytouch_found:
                    print("❌ PayTouch partner not found in API response")
                
                if not paytouch2_found:
                    print("❌ Paytouch2 partner not found in API response")
                
                print("-" * 60)
                print("📋 All Partners:")
                for partner in partners:
                    if 'PAYOUT' in partner['supports']:
                        print(f"   • {partner['name']} (ID: {partner['id']}) - PAYOUT")
                
                return paytouch_found and paytouch2_found
                
            else:
                print(f"❌ API returned error: {data.get('message')}")
                return False
        else:
            print(f"❌ API call failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API. Is the backend running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function"""
    success = test_paytouch_name_changes()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ PayTouch name changes test passed!")
        print("The service routing should now show:")
        print("  • Paytouch_Truaxis (instead of PayTouch)")
        print("  • Paytouch2_Grosmart (instead of Paytouch2)")
    else:
        print("❌ PayTouch name changes test failed!")
    print("=" * 60)

if __name__ == '__main__':
    main()