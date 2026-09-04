#!/usr/bin/env python3
"""
Script to identify all places where merchant_wallet is being incorrectly updated with PayIN amounts
"""

import os
import re

def find_wallet_updates():
    """Find all places where merchant_wallet is being updated"""
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    issues_found = []
    
    # Files to check
    files_to_check = [
        'payin_routes.py',
        'mudrape_routes.py',
        'tourquest_routes.py',
        'mudrape_callback_routes.py',
        'mudrape_service.py',
        'tourquest_service.py'
    ]
    
    print("=" * 80)
    print("IDENTIFYING MERCHANT_WALLET UPDATE ISSUES")
    print("=" * 80)
    print()
    
    for filename in files_to_check:
        filepath = os.path.join(backend_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filename}")
            continue
            
        print(f"\n📄 Checking: {filename}")
        print("-" * 80)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        in_merchant_wallet_block = False
        block_start_line = 0
        block_lines = []
        
        for i, line in enumerate(lines, 1):
            # Check for merchant_wallet INSERT/UPDATE
            if 'INSERT INTO merchant_wallet' in line or 'merchant_wallet' in line:
                in_merchant_wallet_block = True
                block_start_line = i
                block_lines = [line]
            elif in_merchant_wallet_block:
                block_lines.append(line)
                
                # Check if block ends
                if ')' in line and ('""")' in line or "''')" in line):
                    # Check if this is in a payin context
                    context_start = max(0, block_start_line - 20)
                    context_lines = lines[context_start:block_start_line]
                    context = ''.join(context_lines).lower()
                    
                    is_payin_context = any(keyword in context for keyword in [
                        'payin', 'payment', 'callback', 'success', 'net_amount',
                        'credit merchant wallet', 'payin credit'
                    ])
                    
                    if is_payin_context:
                        print(f"\n🔴 ISSUE FOUND at line {block_start_line}:")
                        print(f"   Context: PayIN success handler")
                        print(f"   Code block:")
                        for bl in block_lines[:5]:  # Show first 5 lines
                            print(f"      {bl.rstrip()}")
                        
                        issues_found.append({
                            'file': filename,
                            'line': block_start_line,
                            'type': 'merchant_wallet_update_in_payin'
                        })
                    
                    in_merchant_wallet_block = False
                    block_lines = []
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: Found {len(issues_found)} issues")
    print("=" * 80)
    
    if issues_found:
        print("\nIssues to fix:")
        for issue in issues_found:
            print(f"  • {issue['file']}:{issue['line']} - {issue['type']}")
    else:
        print("\n✅ No issues found!")
    
    return issues_found


def check_wallet_balance_calculation():
    """Check if wallet balance calculation is correct"""
    
    print("\n" + "=" * 80)
    print("CHECKING WALLET BALANCE CALCULATION")
    print("=" * 80)
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    wallet_routes_path = os.path.join(backend_dir, 'wallet_routes.py')
    
    if not os.path.exists(wallet_routes_path):
        print("⚠️  wallet_routes.py not found")
        return
    
    with open(wallet_routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if calculation uses fund_requests
    if 'fund_requests' in content and 'total_topup' in content:
        print("✅ Wallet balance calculation uses fund_requests (CORRECT)")
    else:
        print("🔴 Wallet balance calculation might be incorrect")
    
    # Check if it uses merchant_wallet table for balance
    if 'SELECT balance FROM merchant_wallet' in content:
        print("🔴 WARNING: Wallet balance uses merchant_wallet table (INCORRECT)")
    else:
        print("✅ Wallet balance does NOT use merchant_wallet table (CORRECT)")
    
    # Check calculation formula
    if 'total_topup - total_settlements' in content:
        print("✅ Calculation formula includes topup and settlements (CORRECT)")
    else:
        print("⚠️  Check calculation formula")


def main():
    print("\n🔍 WALLET BALANCE FLOW ANALYZER")
    print("=" * 80)
    print("This script identifies issues in the wallet balance flow")
    print("=" * 80)
    
    # Find wallet update issues
    issues = find_wallet_updates()
    
    # Check wallet balance calculation
    check_wallet_balance_calculation()
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. Remove all merchant_wallet updates from PayIN success handlers
2. Keep merchant_wallet_transactions only for fund operations
3. Ensure wallet balance is calculated from fund_requests table
4. PayIN amounts should be for display purposes only

See FIX_WALLET_BALANCE_FLOW.md for detailed fix instructions.
    """)


if __name__ == '__main__':
    main()
