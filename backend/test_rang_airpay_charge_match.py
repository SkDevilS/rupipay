#!/usr/bin/env python3
"""
Test Rang charge calculation to ensure it matches Airpay exactly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from rang_service import RangService
from airpay_service import AirpayService
import json

def test_charge_calculation_match():
    """Test that Rang and Airpay calculate charges identically"""
    print("=" * 80)
    print("RANG VS AIRPAY CHARGE CALCULATION VERIFICATION")
    print("=" * 80)
    
    # Initialize services
    rang_service = RangService()
    airpay_service = AirpayService()
    
    # Test with different amounts and schemes
    test_cases = [
        {'amount': 100, 'scheme_id': 1, 'description': '₹100 with scheme 1'},
        {'amount': 500, 'scheme_id': 1, 'description': '₹500 with scheme 1'},
        {'amount': 1000, 'scheme_id': 1, 'description': '₹1000 with scheme 1'},
        {'amount': 50, 'scheme_id': 2, 'description': '₹50 with scheme 2'},
        {'amount': 300, 'scheme_id': 2, 'description': '₹300 with scheme 2'},
    ]
    
    print("📊 CHARGE CALCULATION COMPARISON:")
    print("-" * 90)
    print(f"{'Test Case':<25} {'Rang Charge':<15} {'Airpay Charge':<15} {'Rang Net':<12} {'Airpay Net':<12} {'Match':<8}")
    print("-" * 90)
    
    all_match = True
    
    for test in test_cases:
        amount = test['amount']
        scheme_id = test['scheme_id']
        description = test['description']
        
        # Calculate charges with Rang
        try:
            rang_charge, rang_net, rang_type = rang_service.calculate_charges(amount, scheme_id)
            if rang_charge is None:
                rang_charge, rang_net, rang_type = "No config", 0, "N/A"
        except Exception as e:
            rang_charge, rang_net, rang_type = f"Error: {e}", 0, "N/A"
        
        # Calculate charges with Airpay
        try:
            airpay_charge, airpay_net, airpay_type = airpay_service.calculate_charges(amount, scheme_id)
            if airpay_charge is None:
                airpay_charge, airpay_net, airpay_type = "No config", 0, "N/A"
        except Exception as e:
            airpay_charge, airpay_net, airpay_type = f"Error: {e}", 0, "N/A"
        
        # Check if they match
        charges_match = rang_charge == airpay_charge
        nets_match = rang_net == airpay_net
        match = "✅" if (charges_match and nets_match) else "❌"
        
        if not (charges_match and nets_match):
            all_match = False
        
        print(f"{description:<25} ₹{rang_charge:<14} ₹{airpay_charge:<14} ₹{rang_net:<11} ₹{airpay_net:<11} {match:<8}")
    
    print("-" * 90)
    
    if all_match:
        print("🎉 SUCCESS: All charge calculations match between Rang and Airpay!")
    else:
        print("❌ MISMATCH: Charge calculations don't match - need to investigate")
    
    return all_match

def test_merchant_scheme_lookup():
    """Test that both services get merchant scheme_id correctly"""
    print("\n" + "=" * 80)
    print("MERCHANT SCHEME_ID LOOKUP TEST")
    print("=" * 80)
    
    test_merchant_id = "7679022140"  # Test merchant
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get merchant details
        cursor.execute("""
            SELECT merchant_id, full_name, scheme_id, is_active
            FROM merchants
            WHERE merchant_id = %s
        """, (test_merchant_id,))
        
        merchant = cursor.fetchone()
        
        if merchant:
            print(f"📋 MERCHANT DETAILS:")
            print(f"  Merchant ID: {merchant['merchant_id']}")
            print(f"  Name: {merchant['full_name']}")
            print(f"  Scheme ID: {merchant['scheme_id']}")
            print(f"  Active: {merchant['is_active']}")
            
            # Test charge calculation with this merchant's scheme
            test_amount = 500
            
            rang_service = RangService()
            airpay_service = AirpayService()
            
            rang_charge, rang_net, rang_type = rang_service.calculate_charges(test_amount, merchant['scheme_id'])
            airpay_charge, airpay_net, airpay_type = airpay_service.calculate_charges(test_amount, merchant['scheme_id'])
            
            print(f"\n🧪 CHARGE CALCULATION FOR ₹{test_amount}:")
            print(f"  Rang:   Charge=₹{rang_charge}, Net=₹{rang_net}, Type={rang_type}")
            print(f"  Airpay: Charge=₹{airpay_charge}, Net=₹{airpay_net}, Type={airpay_type}")
            
            if rang_charge == airpay_charge and rang_net == airpay_net:
                print("  ✅ Calculations match perfectly!")
            else:
                print("  ❌ Calculations don't match!")
        else:
            print(f"❌ Merchant {test_merchant_id} not found")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error testing merchant lookup: {e}")

def test_order_creation_flow():
    """Test the complete order creation flow with charge calculation"""
    print("\n" + "=" * 80)
    print("ORDER CREATION FLOW TEST")
    print("=" * 80)
    
    test_merchant_id = "7679022140"
    test_order_data = {
        'orderid': 'TEST_CHARGE_MATCH_001',
        'amount': 300,
        'payee_fname': 'Test User',
        'payee_email': 'test@example.com',
        'payee_mobile': '9876543210'
    }
    
    print(f"🧪 TESTING ORDER CREATION:")
    print(f"  Merchant: {test_merchant_id}")
    print(f"  Order: {test_order_data['orderid']}")
    print(f"  Amount: ₹{test_order_data['amount']}")
    
    try:
        rang_service = RangService()
        
        # Test charge calculation (without actually creating the order)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get merchant scheme_id
        cursor.execute("""
            SELECT scheme_id FROM merchants WHERE merchant_id = %s
        """, (test_merchant_id,))
        
        merchant = cursor.fetchone()
        
        if merchant:
            scheme_id = merchant['scheme_id']
            amount = float(test_order_data['amount'])
            
            # Calculate charges
            charge_amount, net_amount, charge_type = rang_service.calculate_charges(amount, scheme_id)
            
            print(f"\n📊 CHARGE CALCULATION RESULTS:")
            print(f"  Scheme ID: {scheme_id}")
            print(f"  Gross Amount: ₹{amount}")
            print(f"  Charge Amount: ₹{charge_amount}")
            print(f"  Charge Type: {charge_type}")
            print(f"  Net Amount: ₹{net_amount}")
            
            if charge_amount > 0:
                charge_percentage = (charge_amount / amount) * 100
                print(f"  Charge Rate: {charge_percentage:.2f}%")
                print("  ✅ Charges will be deducted correctly!")
            else:
                print("  ⚠️ No charges configured - check commercial_charges table")
        else:
            print(f"❌ Merchant {test_merchant_id} not found")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error testing order creation: {e}")

def check_commercial_charges_configuration():
    """Check commercial_charges table for proper configuration"""
    print("\n" + "=" * 80)
    print("COMMERCIAL CHARGES CONFIGURATION CHECK")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all PAYIN charges
        cursor.execute("""
            SELECT scheme_id, product_name, min_amount, max_amount, 
                   charge_value, charge_type, service_type
            FROM commercial_charges 
            WHERE service_type = 'PAYIN'
            ORDER BY scheme_id, min_amount
        """)
        
        charges = cursor.fetchall()
        
        if charges:
            print("📋 PAYIN CHARGE CONFIGURATIONS:")
            print("-" * 80)
            print(f"{'Scheme':<8} {'Product':<20} {'Min':<8} {'Max':<10} {'Value':<8} {'Type':<12}")
            print("-" * 80)
            
            for charge in charges:
                print(f"{charge['scheme_id']:<8} {charge['product_name']:<20} "
                      f"{charge['min_amount']:<8} {charge['max_amount']:<10} "
                      f"{charge['charge_value']:<8} {charge['charge_type']:<12}")
            
            print(f"\nTotal configurations: {len(charges)}")
            
            # Check if there are configurations for common schemes
            scheme_1_configs = [c for c in charges if c['scheme_id'] == 1]
            scheme_2_configs = [c for c in charges if c['scheme_id'] == 2]
            
            print(f"\n📊 SCHEME COVERAGE:")
            print(f"  Scheme 1 configurations: {len(scheme_1_configs)}")
            print(f"  Scheme 2 configurations: {len(scheme_2_configs)}")
            
            if len(scheme_1_configs) > 0 and len(scheme_2_configs) > 0:
                print("  ✅ Both common schemes have charge configurations")
            else:
                print("  ⚠️ Missing charge configurations for common schemes")
        else:
            print("❌ No PAYIN charges found in commercial_charges table")
            print("   This explains why charges are not being deducted!")
        
        cursor.close()
        conn.close()
        
        return len(charges) > 0
        
    except Exception as e:
        print(f"❌ Error checking commercial_charges: {e}")
        return False

def main():
    """Main execution function"""
    print("🔧 RANG-AIRPAY CHARGE CALCULATION MATCH TEST")
    print("=" * 80)
    print("Purpose: Ensure Rang charge calculation matches Airpay exactly")
    print()
    
    # Step 1: Check commercial_charges configuration
    charges_configured = check_commercial_charges_configuration()
    
    if not charges_configured:
        print("\n❌ CRITICAL: No charge configurations found!")
        print("   Run fix_rang_charge_configuration.py to set up charges")
        return
    
    # Step 2: Test merchant scheme lookup
    test_merchant_scheme_lookup()
    
    # Step 3: Test charge calculations match
    calculations_match = test_charge_calculation_match()
    
    # Step 4: Test order creation flow
    test_order_creation_flow()
    
    print("\n" + "=" * 80)
    print("✅ RANG-AIRPAY CHARGE MATCH TEST COMPLETED")
    print("=" * 80)
    
    if charges_configured and calculations_match:
        print("🎉 SUCCESS: Rang charge system now matches Airpay perfectly!")
        print("\n📋 NEXT STEPS:")
        print("1. Deploy the updated Rang service")
        print("2. Test with a real Rang transaction")
        print("3. Verify charges are deducted correctly")
        print("4. Compare with Airpay transaction charges")
    else:
        print("⚠️ ISSUES FOUND:")
        if not charges_configured:
            print("• No charge configurations in commercial_charges table")
        if not calculations_match:
            print("• Charge calculations don't match between Rang and Airpay")
        print("\n📋 REQUIRED ACTIONS:")
        print("1. Configure commercial_charges table for PAYIN service")
        print("2. Ensure Rang uses merchant scheme_id from database")
        print("3. Test charge calculations again")

if __name__ == "__main__":
    main()