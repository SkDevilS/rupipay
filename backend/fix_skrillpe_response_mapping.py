#!/usr/bin/env python3
"""
Fix SkrillPe Response Mapping
Analyzes and fixes the response handling in SkrillPe service
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json

def analyze_skrillpe_service():
    """Analyze current SkrillPe service implementation"""
    print("🔍 Analyzing SkrillPe Service Implementation")
    print("=" * 60)
    
    try:
        with open('skrillpe_service.py', 'r') as f:
            content = f.read()
        
        # Check for key patterns
        patterns = [
            ("API endpoint", "/api/skrill/upi/qr/send/intent/WL"),
            ("Success detection", "is_successful"),
            ("Intent URL extraction", "intentUrl"),
            ("Response return", "return {"),
        ]
        
        print("Code Analysis:")
        for pattern_name, pattern in patterns:
            if pattern in content:
                print(f"  ✅ {pattern_name}: Found")
            else:
                print(f"  ❌ {pattern_name}: Missing")
        
        # Extract the response handling section
        if "if response.status_code == 200:" in content:
            start = content.find("if response.status_code == 200:")
            end = content.find("except Exception as e:", start)
            if end == -1:
                end = content.find("finally:", start)
            
            response_section = content[start:end] if end != -1 else content[start:start+1000]
            print(f"\n📋 Current Response Handling:")
            print("-" * 40)
            print(response_section[:800] + "..." if len(response_section) > 800 else response_section)
        
    except FileNotFoundError:
        print("❌ skrillpe_service.py not found")

def create_fixed_response_handler():
    """Create a fixed response handler"""
    print("\n🔧 Creating Fixed Response Handler")
    print("=" * 60)
    
    fixed_handler = '''
                if response.status_code == 200:
                    data = response.json()
                    
                    print(f"🔍 SkrillPe API Response Debug:")
                    print(f"   Raw response: {json.dumps(data, indent=2)}")
                    
                    # Check multiple success conditions
                    message = data.get('message', '')
                    success_indicators = [
                        'Successful' in message,
                        'successful' in message.lower(),
                        data.get('intentUrl'),
                        data.get('code'),
                        data.get('tinyUrl')
                    ]
                    
                    is_successful = any(success_indicators)
                    
                    print(f"   Success indicators: {success_indicators}")
                    print(f"   Is successful: {is_successful}")
                    
                    if is_successful:
                        # Extract all possible URL fields
                        intent_url = data.get('intentUrl', '')
                        tiny_url = data.get('tinyUrl', '')
                        code = data.get('code', '')
                        reason = data.get('reason', '')
                        
                        print(f"   Intent URL: '{intent_url}'")
                        print(f"   Tiny URL: '{tiny_url}'")
                        print(f"   Code: '{code}'")
                        print(f"   Reason: '{reason}'")
                        
                        # Determine the best UPI string to use
                        qr_string = intent_url or tiny_url or message
                        
                        print(f"   Final QR String: '{qr_string}'")
                        
                        # Insert transaction into database
                        cursor.execute("""
                            INSERT INTO payin_transactions (
                                txn_id, merchant_id, order_id, amount, charge_amount, 
                                net_amount, charge_type, status, pg_partner, pg_txn_id,
                                payee_name, payee_mobile, payee_email,
                                remarks, created_at, updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                            )
                        """, (
                            txn_id,
                            merchant_id,
                            order_data.get('orderid'),
                            amount,
                            charge_amount,
                            net_amount,
                            charge_type,
                            'INITIATED',
                            'SkrillPe',
                            code or txn_id,  # Use code if available, otherwise txn_id
                            customer_name,
                            customer_mobile,
                            order_data.get('payee_email', ''),
                            json.dumps(data)  # Store full response for debugging
                        ))
                        
                        conn.commit()
                        
                        return {
                            'success': True,
                            'message': message or 'UPI intent generated successfully',
                            'txn_id': txn_id,
                            'order_id': order_data.get('orderid'),
                            'amount': amount,
                            'charge_amount': charge_amount,
                            'net_amount': net_amount,
                            'qr_string': qr_string,
                            'upi_link': qr_string,  # Same as qr_string for compatibility
                            'intent_url': intent_url,
                            'tiny_url': tiny_url,
                            'pg_txn_id': code or txn_id,
                            'status': 'INITIATED',
                            'raw_response': data  # Include raw response for debugging
                        }
                    else:
                        error_message = data.get('reason') or message or 'UPI intent generation failed'
                        print(f"   Error: {error_message}")
                        
                        return {
                            'success': False,
                            'message': error_message,
                            'raw_response': data
                        }
    '''
    
    print("Fixed Response Handler:")
    print(fixed_handler)
    
    return fixed_handler

def show_debugging_tips():
    """Show debugging tips"""
    print("\n💡 Debugging Tips")
    print("=" * 60)
    
    tips = [
        "1. Check server logs for SkrillPe API response details",
        "2. Verify that intentUrl field is present in API response",
        "3. Ensure success detection logic matches actual API behavior",
        "4. Test with different payload values to see response variations",
        "5. Check if API credentials have proper permissions",
        "6. Verify network connectivity to SkrillPe servers",
        "7. Test API directly using curl or Postman first"
    ]
    
    for tip in tips:
        print(f"  {tip}")

def main():
    """Main function"""
    print("🔧 SkrillPe Response Mapping Fix")
    print("=" * 80)
    
    # Analyze current implementation
    analyze_skrillpe_service()
    
    # Create fixed handler
    create_fixed_response_handler()
    
    # Show debugging tips
    show_debugging_tips()
    
    print("\n📋 Next Steps:")
    print("1. Run: python3 test_skrillpe_payin_complete.py")
    print("2. Check the debug output for API response details")
    print("3. If intentUrl is missing, contact SkrillPe team")
    print("4. If success detection fails, update the logic")
    print("5. Deploy the fix using the deployment script")

if __name__ == "__main__":
    main()