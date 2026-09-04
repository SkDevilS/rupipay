"""
Fix Missing Oxymoney VPA Usage Records
Backfills VPA usage for successful transactions that are missing VPA records
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime

def find_missing_vpa_records():
    """Find successful Oxymoney transactions without VPA usage records"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return []
        
        with conn.cursor() as cursor:
            print("=" * 80)
            print("FINDING MISSING VPA USAGE RECORDS")
            print("=" * 80)
            
            # Find successful Oxymoney transactions without VPA usage
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.order_id,
                    pt.merchant_id,
                    pt.amount,
                    pt.payment_url,
                    pt.created_at,
                    pt.completed_at
                FROM payin_transactions pt
                LEFT JOIN oxymoney_vpa_usage ovu ON pt.txn_id = ovu.txn_id
                WHERE pt.pg_partner = 'Oxymoney_Grosmart'
                AND pt.status = 'SUCCESS'
                AND ovu.id IS NULL
                ORDER BY pt.created_at DESC
            """)
            
            missing_records = cursor.fetchall()
            
            if missing_records:
                print(f"\n✅ Found {len(missing_records)} transaction(s) with missing VPA usage records:\n")
                for idx, txn in enumerate(missing_records, 1):
                    # Extract VPA from payment_url
                    payment_url = txn.get('payment_url', '')
                    vpa_used = None
                    if '|VPA:' in payment_url:
                        vpa_used = payment_url.split('|VPA:')[1].split('|')[0]
                    
                    print(f"{idx}. Transaction ID: {txn['txn_id']}")
                    print(f"   Order ID: {txn['order_id']}")
                    print(f"   Merchant ID: {txn['merchant_id']}")
                    print(f"   Amount: ₹{txn['amount']}")
                    print(f"   VPA: {vpa_used if vpa_used else '⚠️  NOT FOUND'}")
                    print(f"   Completed At: {txn.get('completed_at', 'N/A')}")
                    print()
            else:
                print("\n✅ No missing VPA usage records found!")
                print("   All successful Oxymoney transactions have VPA usage recorded.")
            
            return missing_records
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            conn.close()

def fix_missing_vpa_records(dry_run=True):
    """
    Backfill missing VPA usage records
    
    Args:
        dry_run: If True, only show what would be done without making changes
    """
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return
        
        with conn.cursor() as cursor:
            print("\n" + "=" * 80)
            if dry_run:
                print("DRY RUN - NO CHANGES WILL BE MADE")
            else:
                print("FIXING MISSING VPA USAGE RECORDS")
            print("=" * 80)
            
            # Find missing records
            cursor.execute("""
                SELECT 
                    pt.txn_id,
                    pt.order_id,
                    pt.merchant_id,
                    pt.amount,
                    pt.payment_url,
                    pt.completed_at
                FROM payin_transactions pt
                LEFT JOIN oxymoney_vpa_usage ovu ON pt.txn_id = ovu.txn_id
                WHERE pt.pg_partner = 'Oxymoney_Grosmart'
                AND pt.status = 'SUCCESS'
                AND ovu.id IS NULL
                ORDER BY pt.created_at ASC
            """)
            
            missing_records = cursor.fetchall()
            
            if not missing_records:
                print("\n✅ No missing VPA usage records found!")
                return
            
            print(f"\nFound {len(missing_records)} transaction(s) to fix\n")
            
            fixed_count = 0
            skipped_count = 0
            
            for txn in missing_records:
                # Extract VPA from payment_url
                payment_url = txn.get('payment_url', '')
                vpa_used = None
                
                if '|VPA:' in payment_url:
                    vpa_used = payment_url.split('|VPA:')[1].split('|')[0]
                else:
                    print(f"⚠️  Skipping {txn['txn_id']} - VPA not found in payment_url")
                    skipped_count += 1
                    continue
                
                # Use completed_at if available, otherwise use current time
                created_at = txn.get('completed_at') or datetime.now()
                
                if dry_run:
                    print(f"Would insert VPA usage:")
                    print(f"  Transaction ID: {txn['txn_id']}")
                    print(f"  VPA: {vpa_used}")
                    print(f"  Amount: ₹{txn['amount']}")
                    print(f"  Merchant ID: {txn['merchant_id']}")
                    print(f"  Created At: {created_at}")
                    print()
                else:
                    # Insert VPA usage record
                    cursor.execute("""
                        INSERT INTO oxymoney_vpa_usage (
                            vpa, amount, txn_id, merchant_id, created_at
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (vpa_used, txn['amount'], txn['txn_id'], txn['merchant_id'], created_at))
                    
                    print(f"✅ Fixed: {txn['txn_id']}")
                    print(f"   VPA: {vpa_used}")
                    print(f"   Amount: ₹{txn['amount']}")
                    print()
                
                fixed_count += 1
            
            if not dry_run:
                conn.commit()
                print("\n" + "=" * 80)
                print(f"✅ BACKFILL COMPLETED")
                print("=" * 80)
                print(f"  Fixed: {fixed_count} record(s)")
                print(f"  Skipped: {skipped_count} record(s)")
                print()
            else:
                print("\n" + "=" * 80)
                print(f"DRY RUN SUMMARY")
                print("=" * 80)
                print(f"  Would fix: {fixed_count} record(s)")
                print(f"  Would skip: {skipped_count} record(s)")
                print(f"\nRun with --execute flag to apply changes")
                print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def show_vpa_usage_summary():
    """Show VPA usage summary after fix"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        
        with conn.cursor() as cursor:
            print("\n" + "=" * 80)
            print("VPA USAGE SUMMARY (TODAY)")
            print("=" * 80)
            
            today = datetime.now().date()
            
            cursor.execute("""
                SELECT 
                    vpa,
                    COUNT(*) as txn_count,
                    SUM(amount) as total_amount
                FROM oxymoney_vpa_usage
                WHERE DATE(created_at) = %s
                GROUP BY vpa
                ORDER BY total_amount DESC
            """, (today,))
            
            usage_records = cursor.fetchall()
            
            if usage_records:
                print(f"\nVPA Usage for {today}:\n")
                for record in usage_records:
                    total = float(record['total_amount'])
                    limit = 960000.00
                    percentage = (total / limit) * 100
                    remaining = limit - total
                    
                    print(f"VPA: {record['vpa']}")
                    print(f"  Transactions: {record['txn_count']}")
                    print(f"  Total Amount: ₹{total:,.2f}")
                    print(f"  Usage: {percentage:.2f}%")
                    print(f"  Remaining: ₹{remaining:,.2f}")
                    print()
            else:
                print(f"\nNo VPA usage recorded for today")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix missing Oxymoney VPA usage records')
    parser.add_argument('--find', action='store_true', help='Find missing VPA records')
    parser.add_argument('--execute', action='store_true', help='Execute the fix (default is dry run)')
    parser.add_argument('--summary', action='store_true', help='Show VPA usage summary')
    
    args = parser.parse_args()
    
    if args.find:
        find_missing_vpa_records()
    elif args.summary:
        show_vpa_usage_summary()
    else:
        # Default: run fix (dry run unless --execute specified)
        fix_missing_vpa_records(dry_run=not args.execute)
        
        if args.execute:
            # Show summary after fix
            show_vpa_usage_summary()
