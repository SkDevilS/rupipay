#!/usr/bin/env python3
"""
Script to mark INITIATED payin transactions as FAILED for a specific time range.

Usage:
    python mark_initiated_payins_failed.py

This script will:
1. Show all INITIATED payins in the specified time range
2. Ask for confirmation before updating
3. Mark them as FAILED
4. Show summary of changes
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_pooled import get_db_connection
from config import Config

def get_initiated_payins(start_date, end_date):
    """Get all INITIATED payin transactions in the time range"""
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
                    status,
                    pg_partner,
                    created_at,
                    updated_at
                FROM payin_transactions
                WHERE status = 'INITIATED'
                AND created_at >= %s
                AND created_at <= %s
                ORDER BY created_at DESC
            """
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"❌ Error fetching transactions: {e}")
        return None
    finally:
        connection.close()

def mark_payins_as_failed(start_date, end_date, reason="Marked as failed by admin"):
    """Mark INITIATED payins as FAILED"""
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
                    updated_at = NOW()
                WHERE status = 'INITIATED'
                AND created_at >= %s
                AND created_at <= %s
            """
            cursor.execute(query, (reason, start_date, end_date))
            affected_rows = cursor.rowcount
            connection.commit()
            return affected_rows
    except Exception as e:
        print(f"❌ Error updating transactions: {e}")
        connection.rollback()
        return 0
    finally:
        connection.close()

def display_transactions(transactions):
    """Display transactions in a formatted table"""
    if not transactions:
        print("\n📋 No INITIATED transactions found in this time range.")
        return
    
    print(f"\n📋 Found {len(transactions)} INITIATED transactions:")
    print("\n" + "="*120)
    print(f"{'ID':<6} {'Transaction ID':<25} {'Merchant ID':<15} {'Amount':<10} {'PG Partner':<12} {'Created At':<20}")
    print("="*120)
    
    for txn in transactions:
        print(f"{txn['id']:<6} {txn['txn_id']:<25} {txn['merchant_id']:<15} "
              f"₹{txn['amount']:<9.2f} {txn['pg_partner']:<12} {str(txn['created_at']):<20}")
    
    print("="*120)
    
    # Calculate total amount
    total_amount = sum(float(txn['amount']) for txn in transactions)
    print(f"\n💰 Total Amount: ₹{total_amount:,.2f}")

def main():
    print("="*60)
    print("Mark INITIATED Payin Transactions as FAILED")
    print("="*60)
    
    # Get time range from user
    print("\n📅 Enter the time range for transactions to mark as FAILED:")
    print("   Format: YYYY-MM-DD HH:MM:SS")
    print("   Example: 2026-03-24 00:00:00")
    print()
    
    # Get start date
    while True:
        start_date_str = input("Start Date & Time: ").strip()
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
            break
        except ValueError:
            print("❌ Invalid format. Please use: YYYY-MM-DD HH:MM:SS")
    
    # Get end date
    while True:
        end_date_str = input("End Date & Time: ").strip()
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
            if end_date < start_date:
                print("❌ End date must be after start date")
                continue
            break
        except ValueError:
            print("❌ Invalid format. Please use: YYYY-MM-DD HH:MM:SS")
    
    print(f"\n🔍 Searching for INITIATED transactions between:")
    print(f"   From: {start_date}")
    print(f"   To:   {end_date}")
    
    # Fetch transactions
    transactions = get_initiated_payins(start_date, end_date)
    
    if transactions is None:
        return
    
    if not transactions:
        print("\n✅ No INITIATED transactions found in this time range.")
        return
    
    # Display transactions
    display_transactions(transactions)
    
    # Get custom reason (optional)
    print("\n📝 Enter reason for marking as FAILED (press Enter for default):")
    custom_reason = input("Reason: ").strip()
    if not custom_reason:
        custom_reason = "Marked as failed by admin - timeout/abandoned transaction"
    
    # Confirm action
    print("\n" + "="*60)
    print("⚠️  WARNING: This action will mark all above transactions as FAILED")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"   • Transactions to update: {len(transactions)}")
    print(f"   • Total amount: ₹{sum(float(t['amount']) for t in transactions):,.2f}")
    print(f"   • Reason: {custom_reason}")
    print(f"   • Time range: {start_date} to {end_date}")
    
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
    print("\n⏳ Updating transactions...")
    affected_rows = mark_payins_as_failed(start_date, end_date, custom_reason)
    
    if affected_rows > 0:
        print(f"\n✅ Successfully marked {affected_rows} transactions as FAILED")
        print(f"   Reason: {custom_reason}")
        
        # Show updated transactions
        print("\n📋 Verifying updates...")
        connection = get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM payin_transactions
                        WHERE status = 'FAILED'
                        AND error_message = %s
                        AND updated_at >= NOW() - INTERVAL 1 MINUTE
                    """, (custom_reason,))
                    result = cursor.fetchone()
                    print(f"✅ Verified: {result['count']} transactions now have status FAILED")
            finally:
                connection.close()
    else:
        print("\n❌ No transactions were updated")
    
    print("\n" + "="*60)
    print("Operation completed")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
