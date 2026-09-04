#!/usr/bin/env python3
"""
Fix Settlement Admin Wallet Update
Updates wallet_service.py to properly debit admin unsettled balance during settlement
"""

import os

def fix_settlement_code():
    """Update wallet_service.py to fix admin unsettled balance update"""
    
    file_path = 'wallet_service.py'
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print("=" * 80)
    print("FIXING SETTLEMENT ADMIN WALLET UPDATE")
    print("=" * 80)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the settlement function and add admin unsettled balance update
    old_code = '''                # CRITICAL: Record admin wallet debit for settlement
                admin_balance_before = admin_balance
                admin_balance_after = admin_balance - float(amount)
                
                admin_txn_id = self.generate_txn_id('AWT')
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions 
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'DEBIT', %s, %s, %s, %s, %s)
                """, (admin_id, admin_txn_id, amount, admin_balance_before, admin_balance_after,
                      f"Settlement for merchant {merchant_id} - {settlement_id}", settlement_id))'''
    
    new_code = '''                # CRITICAL: Update admin unsettled wallet during settlement
                # Get admin unsettled balance
                cursor.execute("""
                    SELECT unsettled_balance FROM admin_wallet WHERE admin_id = %s
                """, (admin_id,))
                admin_wallet = cursor.fetchone()
                admin_unsettled_before = float(admin_wallet['unsettled_balance']) if admin_wallet else 0.00
                admin_unsettled_after = admin_unsettled_before - float(charge_amount)
                
                # Update admin unsettled balance
                cursor.execute("""
                    UPDATE admin_wallet
                    SET unsettled_balance = %s, last_updated = NOW()
                    WHERE admin_id = %s
                """, (admin_unsettled_after, admin_id))
                
                # Record admin wallet transaction for settlement
                admin_txn_id = self.generate_txn_id('AWT')
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions 
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'UNSETTLED_DEBIT', %s, %s, %s, %s, %s)
                """, (admin_id, admin_txn_id, charge_amount, admin_unsettled_before, admin_unsettled_after,
                      f"Settlement charge debit for merchant {merchant_id} - {settlement_id}", settlement_id))
                
                # CRITICAL: Record admin wallet debit for settlement (main balance tracking)
                admin_balance_before = admin_balance
                admin_balance_after = admin_balance - float(amount)
                
                admin_main_txn_id = self.generate_txn_id('AWT')
                cursor.execute("""
                    INSERT INTO admin_wallet_transactions 
                    (admin_id, txn_id, txn_type, amount, balance_before, balance_after, description, reference_id)
                    VALUES (%s, %s, 'DEBIT', %s, %s, %s, %s, %s)
                """, (admin_id, admin_main_txn_id, amount, admin_balance_before, admin_balance_after,
                      f"Settlement for merchant {merchant_id} - {settlement_id}", settlement_id))'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ Successfully updated wallet_service.py")
        print("\nChanges made:")
        print("  1. Added admin unsettled balance retrieval")
        print("  2. Added admin unsettled balance update during settlement")
        print("  3. Added UNSETTLED_DEBIT transaction record")
        print("  4. Kept existing DEBIT transaction for main balance tracking")
        print("\n" + "=" * 80)
        return True
    else:
        print("⚠ Could not find the exact code pattern to replace")
        print("  Manual update may be required")
        print("\n" + "=" * 80)
        return False

if __name__ == '__main__':
    fix_settlement_code()
