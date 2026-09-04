#!/usr/bin/env python3
"""
Test Rang charge calculation system to ensure it matches Mudrape
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from rang_service import RangService
from mudrape_service import MudrapeService
import json

def test_charge_calculation_comparison():
    """Compare Rang and Mudrape charge calculations"""
    print("=" * 80)
    print("RANG VS MUDRAPE CHARGE CALCULATION COMPARISON")
    print("=" * 80)
    
    # Initialize services
    rang_service = RangService()
    mudrape_service = MudrapeService()
    
    # Test cases with different amounts and schemes
    test_cases = [
        {'amount': 100, 'scheme_id': 1, 'description': '₹100 with scheme 1'},
        {'amount': 500, 'scheme_id': 1, 'description': '₹500 with scheme 1'},
        {'amount': 1000, 'scheme_id': 1, 'description': '₹1000 with scheme 1'},
        {'amount': 50, 'scheme_id': 2, 'description': '₹50 with scheme 2'},
        {'amount': 300, 'scheme_id': 2, 'description': '₹300 with scheme 2'},
    ]
    
    print("📊 CHARGE CALCULATION COMPARISON:")
    print("-" * 80)
    print(f"{'Test Case':<25} {'Rang Charge':<15} {'Mudrape Charge':<15} {'Match':<10}")
    print("-" * 80)
    
    all_match = True
    
    for test in test_cases:
        amount = test['amount']
        scheme_id = test['scheme_id']
        description = test['description']
        
        # Calculate charges with Rang
        try:
            rang_charge, rang_net = rang_service.calculate_charges(amount, scheme_id)
        except Exception as e:
            rang_charge, rang_net = f"Error: {e}", 0
        
        # Calculate charges with Mudrape
        try:
            mudrape_charge, mudrape_net, mudrape_type = mudrape_service.calculate_charges(amount, scheme_id)
            if mudrape_charge is None:
                mudrape_charge = "No config"
        except Exception as e:
            mudrape_charge, mudrape_net = f"Error: {e}", 0
        
        # Check if they match
        match = "✅" if rang_charge == mudrape_charge else "❌"
        if rang_charge != mudrape_charge:
            all_match = False
        
        print(f"{description:<25} {rang_charge:<15} {mudrape_charge:<15} {match:<10}")
    
    print("-" * 80)
    
    if all_match:
        print("✅ All charge calculations match between Rang and Mudrape!")
    else:
        print("❌ Charge calculations don't match - need to investigate")
    
    return all_match

def check_commercial_charges_table():
    """Check commercial_charges table configuration"""
    print("\n" + "=" * 80)
    print("COMMERCIAL CHARGES TABLE ANALYSIS")
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
            print("📋 PAYIN CHARGE CONFIGURATION:")
            print("-" * 80)
            print(f"{'Scheme':<8} {'Product':<15} {'Min':<8} {'Max':<10} {'Value':<8} {'Type':<12}")
            print("-" * 80)
            
            for charge in charges:
                print(f"{charge['scheme_id']:<8} {charge['product_name']:<15} "
                      f"{charge['min_amount']:<8} {charge['max_amount']:<10} "
                      f"{charge['charge_value']:<8} {charge['charge_type']:<12}")
            
            print(f"\nTotal configurations: {len(charges)}")
        else:
            print("❌ No PAYIN charges found in commercial_charges table")
        
        cursor.close()
        conn.close()
        
        return len(charges) > 0
        
    except Exception as e:
        print(f"❌ Error checking commercial_charges table: {e}")
        return False

def test_specific_transaction_charges():
    """Test charges for specific transaction scenarios"""
    print("\n" + "=" * 80)
    print("SPECIFIC TRANSACTION CHARGE TESTING")
    print("=" * 80)
    
    # Test with real merchant data
    merchant_id = "7679022140"  # Test merchant
    
    test_orders = [
        {
            'orderid': 'TEST_CHARGE_001',
            'amount': 100,
            'payee_fname': 'Test User',
            'payee_email': 'test@example.com',
            'payee_mobile': '9876543210',
            'scheme_id': 1
        },
        {
            'orderid': 'TEST_CHARGE_002', 
            'amount': 500,
            'payee_fname': 'Test User',
            'payee_email': 'test@example.com',
            'payee_mobile': '9876543210',
            'scheme_id': 1
        }
    ]
    
    rang_service = RangService()
    
    print("🧪 TESTING ORDER CREATION WITH CHARGES:")
    print("-" * 60)
    
    for i, order in enumerate(test_orders, 1):
        print(f"\nTest {i}: {order['orderid']} - ₹{order['amount']}")
        
        # Calculate charges directly
        charge, net_amount = rang_service.calculate_charges(
            order['amount'], 
            order['scheme_id']
        )
        
        print(f"  Amount: ₹{order['amount']}")
        print(f"  Charge: ₹{charge}")
        print(f"  Net Amount: ₹{net_amount}")
        print(f"  Charge %: {(charge/order['amount']*100):.2f}%" if order['amount'] > 0 else "N/A")
        
        # Test if this would be stored correctly
        if charge > 0:
            print(f"  ✅ Charges will be deducted")
        else:
            print(f"  ⚠️ No charges configured - check commercial_charges table")

def compare_with_recent_transactions():
    """Compare with recent Mudrape transactions to verify consistency"""
    print("\n" + "=" * 80)
    print("RECENT TRANSACTION CHARGE COMPARISON")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get recent Mudrape transactions with charges
        cursor.execute("""
            SELECT amount, charge_amount, charge_type, net_amount
            FROM payin_transactions 
            WHERE pg_partner = 'Mudrape' 
            AND charge_amount > 0
            AND DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAYS)
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        mudrape_txns = cursor.fetchall()
        
        if mudrape_txns:
            print("📊 RECENT MUDRAPE TRANSACTIONS WITH CHARGES:")
            print("-" * 60)
            print(f"{'Amount':<10} {'Charge':<10} {'Net':<10} {'Type':<12} {'Rate %':<8}")
            print("-" * 60)
            
            for txn in mudrape_txns:
                rate = (txn['charge_amount'] / txn['amount'] * 100) if txn['amount'] > 0 else 0
                print(f"₹{txn['amount']:<9} ₹{txn['charge_amount']:<9} ₹{txn['net_amount']:<9} "
                      f"{txn['charge_type']:<12} {rate:.2f}%")
            
            # Test if Rang would calculate the same charges
            print(f"\n🔍 TESTING RANG CALCULATIONS FOR SAME AMOUNTS:")
            print("-" * 60)
            
            rang_service = RangService()
            
            for txn in mudrape_txns:
                rang_charge, rang_net = rang_service.calculate_charges(txn['amount'], 1)  # Assuming scheme 1
                
                match = "✅" if abs(rang_charge - txn['charge_amount']) < 0.01 else "❌"
                print(f"₹{txn['amount']}: Mudrape=₹{txn['charge_amount']}, Rang=₹{rang_charge} {match}")
        
        else:
            print("❌ No recent Mudrape transactions with charges found")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error comparing transactions: {e}")

def main():
    """Main execution function"""
    print("🔧 RANG CHARGE CALCULATION SYSTEM TEST")
    print("=" * 80)
    print("Purpose: Ensure Rang charge calculation matches Mudrape system")
    print()
    
    # Step 1: Check commercial_charges table
    charges_exist = check_commercial_charges_table()
    
    if not charges_exist:
        print("\n❌ CRITICAL: No charge configurations found!")
        print("   This explains why Rang is not deducting charges.")
        print("   Need to configure commercial_charges table for Rang.")
        return
    
    # Step 2: Test charge calculations
    calculations_match = test_charge_calculation_comparison()
    
    # Step 3: Test specific scenarios
    test_specific_transaction_charges()
    
    # Step 4: Compare with recent transactions
    compare_with_recent_transactions()
    
    print("\n" + "=" * 80)
    print("✅ CHARGE CALCULATION TEST COMPLETED")
    print("=" * 80)
    
    if charges_exist and calculations_match:
        print("🎉 SUCCESS: Rang charge system should now match Mudrape!")
        print("\n📋 NEXT STEPS:")
        print("1. Deploy the updated Rang service")
        print("2. Test with a real transaction")
        print("3. Verify charges are deducted correctly")
    else:
        print("⚠️ ISSUES FOUND:")
        if not charges_exist:
            print("• No charge configurations in commercial_charges table")
        if not calculations_match:
            print("• Charge calculations don't match between services")
        print("\n📋 REQUIRED ACTIONS:")
        print("1. Configure commercial_charges table for PAYIN service")
        print("2. Ensure scheme_id mapping is correct")
        print("3. Test charge calculations again")

if __name__ == "__main__":
    main()