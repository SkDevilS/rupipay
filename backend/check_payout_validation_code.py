#!/usr/bin/env python3
"""
Check the actual payout validation code that's deployed
"""

import re

def check_validation_code():
    """Check what validation code is in payout_routes.py"""
    
    with open('payout_routes.py', 'r') as f:
        content = f.read()
    
    # Find the client_direct_payout function
    pattern = r'def client_direct_payout\(\):.*?(?=\ndef |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("❌ Could not find client_direct_payout function")
        return
    
    function_code = match.group(0)
    
    # Check for validation sections
    print("=" * 80)
    print("CHECKING PAYOUT VALIDATION CODE")
    print("=" * 80)
    
    # Check for old validation (Approved Topup calculation)
    if 'Approved Topup' in function_code or 'Total Payouts (Active)' in function_code:
        print("\n❌ FOUND OLD VALIDATION CODE!")
        print("The function still uses the old 'Approved Topup' calculation")
        
        # Extract the validation section
        old_validation_pattern = r'# Get approved fund requests.*?(?=# Debit merchant wallet|# Get PG partner)'
        old_match = re.search(old_validation_pattern, function_code, re.DOTALL)
        if old_match:
            print("\nOLD VALIDATION CODE:")
            print("-" * 80)
            print(old_match.group(0)[:500])
            print("-" * 80)
    
    # Check for new validation (merchant_wallet table)
    if 'SELECT balance FROM merchant_wallet' in function_code:
        print("\n✅ FOUND NEW VALIDATION CODE!")
        print("The function uses merchant_wallet.balance table")
        
        # Extract the validation section
        new_validation_pattern = r'# Get actual wallet balance.*?(?=# Debit merchant wallet|print\(f"✅ VALIDATION)'
        new_match = re.search(new_validation_pattern, function_code, re.DOTALL)
        if new_match:
            print("\nNEW VALIDATION CODE:")
            print("-" * 80)
            print(new_match.group(0)[:500])
            print("-" * 80)
    
    # Check which validation comes first
    old_pos = function_code.find('Approved Topup')
    new_pos = function_code.find('SELECT balance FROM merchant_wallet')
    
    if old_pos != -1 and new_pos != -1:
        if old_pos < new_pos:
            print("\n⚠️  WARNING: OLD validation code comes BEFORE new validation!")
            print("This means the old validation will reject payouts before the new validation runs")
        else:
            print("\n✅ New validation comes before old validation (if old exists)")
    elif old_pos != -1:
        print("\n❌ CRITICAL: Only OLD validation exists!")
    elif new_pos != -1:
        print("\n✅ Only NEW validation exists")
    else:
        print("\n❓ Could not find any validation code")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_validation_code()
