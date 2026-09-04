#!/usr/bin/env python3
"""
Script to manually mark a payin transaction as FAILED using transaction ID.

Usage:
    python mark_payin_failed_by_txn_id.py <transaction_id>
    
Example:
    python mark_payin_failed_by_txn_id.py TXN1234567890
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_pooled import get_db_connection

def get_transaction_details(txn_id):
    """Get transaction details by transaction ID"""
    connection = get_db_connection()
    if not connection:
        print("❌ Failed to connect to database")
        return None
    
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    id,
                    txn_id,
                    merchant_id,
                    order_id,
                    amount,
                    charge_amount,
                    net_amount,
                    status,
                    pg_partner,
                    pg_txn_id,
                    bank_ref_no,
                    payment_mode,
                    created_at,
                    updated_at,
                    completed_at,
                    error_message
                FROM payin_transactions
                WHERE txn_id = %s
            """
            cursor.execute(query, (txn_id,))
            result = cursor.fetchone()
            return result
    except Exception as e:
        print(f"❌ Error fetching transaction: {e}")
        return None
    finally:
        connection.close()

def mark_transaction_failed(txn_id, reason="Manually marked as failed by admin"):
    """Mark a specific transaction as FAILED"""
    connection = get_db_connection()
    if not connection:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with connection.cursor() as cursor:
            query = """
                UPDATE payin_transactions
                SET 
                    status = 'FAILED',
                    error_message = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE txn_id = %s
            """
            cursor.execute(query, (reason, txn_id))
            affected_rows = cursor.rowcount
            connection.commit()
            return affected_rows > 0
    except Exception as e:
        print(f"❌ Error updating transaction: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()

def display_transaction(txn):
    """Display transaction details in a formatted way"""
    print("\n" + "="*80)
    print("TRANSACTION DETAILS")
    print("="*80)
    print(f"Transaction ID:    {txn['txn_id']}")
    print(f"Order ID:          {txn['order_id']}")
    print(f"Merchant ID:       {txn['merchant_id']}")
    print(f"Amount:            ₹{txn['amount']:.2f}")
    print(f"Charge Amount:     ₹{txn['charge_amount']:.2f}")
    print(f"Net Amount:        ₹{txn['net_amount']:.2f}")
    print(f"Status:            {txn['status']}")
    print(f"PG Partner:        {txn['pg_partner']}")
    print(f"PG Transaction ID: {txn['pg_txn_id'] or 'N/A'}")
    print(f"Bank Ref No (UTR): {txn['bank_ref_no'] or 'N/A'}")
    print(f"Payment Mode:      {txn['payment_mode'] or 'N/A'}")
    print(f"Created At:        {txn['created_at']}")
    print(f"Updated At:        {txn['updated_at']}")
    print(f"Completed At:      {txn['completed_at'] or 'N/A'}")
    if txn['error_message']:
        print(f"Error Message:     {txn['error_message']}")
    print("="*80)

def main():
    print("="*80)
    print("Mark Payin Transaction as FAILED")
    print("="*80)
    
    # Get transaction ID from command line or prompt
    if len(sys.argv) > 1:
        txn_id = sys.argv[1].strip()
    else:
        txn_id = input("\n📝 Enter Transaction ID: ").strip()
    
    if not txn_id:
        print("❌ Transaction ID is required")
        sys.exit(1)
    
    print(f"\n🔍 Searching for transaction: {txn_id}")
    
    # Fetch transaction details
    transaction = get_transaction_details(txn_id)
    
    if not transaction:
        print(f"\n❌ Transaction not found: {txn_id}")
        sys.exit(1)
    
    # Display transaction details
    display_transaction(transaction)
    
    # Check if already failed
    if transaction['status'] == 'FAILED':
        print("\n⚠️  This transaction is already marked as FAILED")
        confirm = input("❓ Do you want to update it anyway? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("\n❌ Operation cancelled.")
            return
    
    # Check if transaction is successful
    if transaction['status'] == 'SUCCESS':
        print("\n⚠️  WARNING: This transaction is marked as SUCCESS")
        print("   Marking a successful transaction as failed may cause accounting issues!")
        confirm = input("❓ Are you absolutely sure you want to proceed? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("\n❌ Operation cancelled.")
            return
    
    # Get custom reason (optional)
    print("\n📝 Enter reason for marking as FAILED (press Enter for default):")
    custom_reason = input("Reason: ").strip()
    if not custom_reason:
        custom_reason = "Manually marked as failed by admin"
    
    # Confirm action
    print("\n" + "="*80)
    print("⚠️  WARNING: This action will mark the transaction as FAILED")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   • Transaction ID: {txn_id}")
    print(f"   • Current Status: {transaction['status']}")
    print(f"   • New Status: FAILED")
    print(f"   • Reason: {custom_reason}")
    print(f"   • Amount: ₹{transaction['amount']:.2f}")
    
    confirm = input("\n❓ Are you sure you want to proceed? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("\n❌ Operation cancelled.")
        return
    
    # Double confirmation for safety
    confirm2 = input("❓ Type 'CONFIRM' to proceed: ").strip()
    
    if confirm2 != 'CONFIRM':
        print("\n❌ Operation cancelled.")
        return
    
    # Perform update
    print("\n⏳ Updating transaction...")
    success = mark_transaction_failed(txn_id, custom_reason)
    
    if success:
        print(f"\n✅ Successfully marked transaction as FAILED")
        print(f"   Transaction ID: {txn_id}")
        print(f"   Reason: {custom_reason}")
        
        # Show updated transaction
        print("\n📋 Verifying update...")
        updated_txn = get_transaction_details(txn_id)
        if updated_txn:
            display_transaction(updated_txn)
            print("\n✅ Transaction successfully updated to FAILED status")
    else:
        print("\n❌ Failed to update transaction")
    
    print("\n" + "="*80)
    print("Operation completed")
    print("="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
