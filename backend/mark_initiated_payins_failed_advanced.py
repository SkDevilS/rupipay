#!/usr/bin/env python3
"""
Advanced Script to Mark INITIATED Payin Transactions as FAILED and Send Callbacks

This script provides advanced filtering options:
- Filter by date range (start date and end date)
- Filter by specific merchant ID
- Filter by time range (specific hours)
- Preview transactions before marking as failed
- Send callbacks to merchant callback URLs
- Comprehensive logging and error handling

Usage:
    python mark_initiated_payins_failed_advanced.py

Features:
1. Multiple filter options (date, merchant, time range)
2. Preview transactions before processing
3. Automatic callback sending to merchant URLs
4. Detailed logging and reporting
5. Safe execution with confirmations
6. Rollback capability on errors
"""

import sys
import os
from datetime import datetime, time
import json
import requests
from typing import List, Dict, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_pooled import get_db_connection
from config import Config

# Constants
FAILED_STATUS = "FAILED"
FAILED_MESSAGE = "PAYMENT NOT RECEIVED, QR/INTENT EXPIRED"
CALLBACK_TIMEOUT = 10  # seconds


class PayinFailureProcessor:
    """Advanced processor for marking payins as failed and sending callbacks"""
    
    def __init__(self):
        self.processed_count = 0
        self.callback_success_count = 0
        self.callback_failed_count = 0
        self.errors = []
    
    def get_initiated_payins(
        self,
        start_date: datetime,
        end_date: datetime,
        merchant_id: Optional[str] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None
    ) -> Optional[List[Dict]]:
        """
        Get all INITIATED payin transactions based on filters
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            merchant_id: Optional merchant ID filter
            start_time: Optional start time filter (HH:MM:SS)
            end_time: Optional end time filter (HH:MM:SS)
            
        Returns:
            List of transaction dictionaries or None on error
        """
        connection = get_db_connection()
        if not connection:
            print("❌ Failed to connect to database")
            return None
        
        try:
            with connection.cursor() as cursor:
                # Build query dynamically based on filters
                query = """
                    SELECT 
                        pt.id,
                        pt.txn_id,
                        pt.merchant_id,
                        pt.order_id,
                        pt.amount,
                        pt.status,
                        pt.pg_partner,
                        pt.callback_url,
                        pt.created_at,
                        pt.updated_at,
                        m.full_name as merchant_name,
                        m.mobile as merchant_mobile
                    FROM payin_transactions pt
                    LEFT JOIN merchants m ON pt.merchant_id = m.merchant_id
                    WHERE pt.status = 'INITIATED'
                    AND pt.created_at >= %s
                    AND pt.created_at <= %s
                """
                
                params = [start_date, end_date]
                
                # Add merchant filter if provided
                if merchant_id:
                    query += " AND pt.merchant_id = %s"
                    params.append(merchant_id)
                
                # Add time range filter if provided
                if start_time and end_time:
                    query += " AND TIME(pt.created_at) >= %s AND TIME(pt.created_at) <= %s"
                    params.append(start_time)
                    params.append(end_time)
                
                query += " ORDER BY pt.created_at DESC"
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                return results
                
        except Exception as e:
            print(f"❌ Error fetching transactions: {e}")
            self.errors.append(f"Database fetch error: {e}")
            return None
        finally:
            connection.close()
    
    def send_callback(
        self,
        txn_id: str,
        merchant_id: str,
        callback_url: str,
        order_id: str,
        amount: float,
        pg_partner: str
    ) -> Tuple[bool, str]:
        """
        Send failure callback to merchant's callback URL
        
        Args:
            txn_id: Transaction ID
            merchant_id: Merchant ID
            callback_url: Merchant's callback URL
            order_id: Order ID
            amount: Transaction amount
            pg_partner: Payment gateway partner
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not callback_url:
            return False, "No callback URL provided"
        
        # Prepare callback payload
        callback_data = {
            "status": FAILED_STATUS,
            "txn_id": txn_id,
            "order_id": order_id,
            "amount": float(amount),
            "pg_partner": pg_partner,
            "message": FAILED_MESSAGE,
            "timestamp": datetime.now().isoformat(),
            "error_code": "TIMEOUT_EXPIRED"
        }
        
        print(f"  📤 Sending callback to: {callback_url}")
        
        try:
            response = requests.post(
                callback_url,
                json=callback_data,
                headers={'Content-Type': 'application/json'},
                timeout=CALLBACK_TIMEOUT
            )
            
            # Log callback attempt
            self._log_callback(
                merchant_id=merchant_id,
                txn_id=txn_id,
                callback_url=callback_url,
                request_data=callback_data,
                response_code=response.status_code,
                response_data=response.text[:1000]
            )
            
            if response.status_code in [200, 201]:
                return True, f"Success (HTTP {response.status_code})"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
                
        except requests.exceptions.Timeout:
            error_msg = "Callback request timed out"
            self._log_callback(
                merchant_id=merchant_id,
                txn_id=txn_id,
                callback_url=callback_url,
                request_data=callback_data,
                response_code=0,
                response_data=error_msg
            )
            return False, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            self._log_callback(
                merchant_id=merchant_id,
                txn_id=txn_id,
                callback_url=callback_url,
                request_data=callback_data,
                response_code=0,
                response_data=str(e)[:1000]
            )
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            return False, error_msg
    
    def _log_callback(
        self,
        merchant_id: str,
        txn_id: str,
        callback_url: str,
        request_data: dict,
        response_code: int,
        response_data: str
    ):
        """Log callback attempt to database"""
        connection = get_db_connection()
        if not connection:
            return
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO callback_logs 
                    (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    merchant_id,
                    txn_id,
                    callback_url,
                    json.dumps(request_data),
                    response_code,
                    response_data
                ))
                connection.commit()
        except Exception as e:
            print(f"  ⚠️  Failed to log callback: {e}")
        finally:
            connection.close()
    
    def mark_transaction_failed(
        self,
        txn_id: str,
        reason: str = FAILED_MESSAGE
    ) -> bool:
        """
        Mark a single transaction as failed
        
        Args:
            txn_id: Transaction ID
            reason: Failure reason
            
        Returns:
            True if successful, False otherwise
        """
        connection = get_db_connection()
        if not connection:
            return False
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE payin_transactions
                    SET 
                        status = %s,
                        error_message = %s,
                        updated_at = NOW()
                    WHERE txn_id = %s
                    AND status = 'INITIATED'
                """, (FAILED_STATUS, reason, txn_id))
                
                connection.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"  ❌ Error updating transaction {txn_id}: {e}")
            connection.rollback()
            self.errors.append(f"Update error for {txn_id}: {e}")
            return False
        finally:
            connection.close()
    
    def process_transactions(
        self,
        transactions: List[Dict],
        send_callbacks: bool = True
    ) -> Dict:
        """
        Process transactions: mark as failed and send callbacks
        
        Args:
            transactions: List of transaction dictionaries
            send_callbacks: Whether to send callbacks to merchants
            
        Returns:
            Dictionary with processing results
        """
        total = len(transactions)
        print(f"\n⏳ Processing {total} transactions...")
        print("="*80)
        
        for idx, txn in enumerate(transactions, 1):
            txn_id = txn['txn_id']
            merchant_id = txn['merchant_id']
            callback_url = txn.get('callback_url')
            
            print(f"\n[{idx}/{total}] Processing: {txn_id}")
            print(f"  Merchant: {merchant_id} ({txn.get('merchant_name', 'N/A')})")
            print(f"  Amount: ₹{txn['amount']}")
            print(f"  Order ID: {txn.get('order_id', 'N/A')}")
            
            # Mark transaction as failed
            if self.mark_transaction_failed(txn_id):
                print(f"  ✅ Marked as FAILED")
                self.processed_count += 1
                
                # Send callback if enabled and URL exists
                if send_callbacks and callback_url:
                    success, message = self.send_callback(
                        txn_id=txn_id,
                        merchant_id=merchant_id,
                        callback_url=callback_url,
                        order_id=txn.get('order_id', ''),
                        amount=txn['amount'],
                        pg_partner=txn.get('pg_partner', 'UNKNOWN')
                    )
                    
                    if success:
                        print(f"  ✅ Callback sent: {message}")
                        self.callback_success_count += 1
                    else:
                        print(f"  ❌ Callback failed: {message}")
                        self.callback_failed_count += 1
                elif not callback_url:
                    print(f"  ⚠️  No callback URL configured")
                    self.callback_failed_count += 1
            else:
                print(f"  ❌ Failed to mark as FAILED")
        
        print("\n" + "="*80)
        
        return {
            'total': total,
            'processed': self.processed_count,
            'callback_success': self.callback_success_count,
            'callback_failed': self.callback_failed_count,
            'errors': self.errors
        }


def display_transactions(transactions: List[Dict]):
    """Display transactions in a formatted table"""
    if not transactions:
        print("\n📋 No INITIATED transactions found with the specified filters.")
        return
    
    print(f"\n📋 Found {len(transactions)} INITIATED transactions:")
    print("\n" + "="*140)
    print(f"{'ID':<6} {'Transaction ID':<25} {'Merchant ID':<15} {'Merchant Name':<20} {'Amount':<10} {'PG':<12} {'Created At':<20}")
    print("="*140)
    
    for txn in transactions:
        merchant_name = txn.get('merchant_name', 'N/A')[:18]
        print(f"{txn['id']:<6} {txn['txn_id']:<25} {txn['merchant_id']:<15} "
              f"{merchant_name:<20} ₹{txn['amount']:<9.2f} {txn.get('pg_partner', 'N/A'):<12} "
              f"{str(txn['created_at']):<20}")
    
    print("="*140)
    
    # Calculate statistics
    total_amount = sum(float(txn['amount']) for txn in transactions)
    merchants = set(txn['merchant_id'] for txn in transactions)
    with_callback = sum(1 for txn in transactions if txn.get('callback_url'))
    
    print(f"\n📊 Statistics:")
    print(f"   • Total Transactions: {len(transactions)}")
    print(f"   • Total Amount: ₹{total_amount:,.2f}")
    print(f"   • Unique Merchants: {len(merchants)}")
    print(f"   • With Callback URL: {with_callback}")
    print(f"   • Without Callback URL: {len(transactions) - with_callback}")


def get_user_filters() -> Dict:
    """Get filter parameters from user"""
    print("="*80)
    print("Advanced Payin Failure Processor")
    print("="*80)
    
    filters = {}
    
    # Date range
    print("\n📅 STEP 1: Date Range (Required)")
    print("   Format: YYYY-MM-DD")
    print("   Example: 2026-03-30")
    
    while True:
        start_date_str = input("\nStart Date: ").strip()
        try:
            filters['start_date'] = datetime.strptime(start_date_str, "%Y-%m-%d")
            break
        except ValueError:
            print("❌ Invalid format. Please use: YYYY-MM-DD")
    
    while True:
        end_date_str = input("End Date: ").strip()
        try:
            filters['end_date'] = datetime.strptime(end_date_str + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            if filters['end_date'] < filters['start_date']:
                print("❌ End date must be after start date")
                continue
            break
        except ValueError:
            print("❌ Invalid format. Please use: YYYY-MM-DD")
    
    # Merchant ID filter
    print("\n👤 STEP 2: Merchant Filter (Optional)")
    print("   Press Enter to skip (process all merchants)")
    merchant_id = input("\nMerchant ID: ").strip()
    filters['merchant_id'] = merchant_id if merchant_id else None
    
    # Time range filter
    print("\n⏰ STEP 3: Time Range Filter (Optional)")
    print("   Filter by specific hours of the day")
    print("   Format: HH:MM:SS")
    print("   Example: 09:00:00 to 18:00:00")
    print("   Press Enter to skip (process all times)")
    
    time_filter = input("\nApply time filter? (y/n): ").strip().lower()
    
    if time_filter == 'y':
        while True:
            start_time_str = input("Start Time (HH:MM:SS): ").strip()
            try:
                filters['start_time'] = datetime.strptime(start_time_str, "%H:%M:%S").time()
                break
            except ValueError:
                print("❌ Invalid format. Please use: HH:MM:SS")
        
        while True:
            end_time_str = input("End Time (HH:MM:SS): ").strip()
            try:
                filters['end_time'] = datetime.strptime(end_time_str, "%H:%M:%S").time()
                break
            except ValueError:
                print("❌ Invalid format. Please use: HH:MM:SS")
    else:
        filters['start_time'] = None
        filters['end_time'] = None
    
    # Callback option
    print("\n📤 STEP 4: Callback Configuration")
    send_callbacks = input("\nSend callbacks to merchants? (y/n): ").strip().lower()
    filters['send_callbacks'] = send_callbacks == 'y'
    
    return filters


def main():
    """Main execution function"""
    try:
        # Get filters from user
        filters = get_user_filters()
        
        # Display filter summary
        print("\n" + "="*80)
        print("📋 Filter Summary")
        print("="*80)
        print(f"Date Range: {filters['start_date'].strftime('%Y-%m-%d')} to {filters['end_date'].strftime('%Y-%m-%d')}")
        if filters['merchant_id']:
            print(f"Merchant ID: {filters['merchant_id']}")
        else:
            print(f"Merchant ID: All merchants")
        
        if filters['start_time'] and filters['end_time']:
            print(f"Time Range: {filters['start_time']} to {filters['end_time']}")
        else:
            print(f"Time Range: All times")
        
        print(f"Send Callbacks: {'Yes' if filters['send_callbacks'] else 'No'}")
        
        # Initialize processor
        processor = PayinFailureProcessor()
        
        # Fetch transactions
        print("\n🔍 Fetching transactions...")
        transactions = processor.get_initiated_payins(
            start_date=filters['start_date'],
            end_date=filters['end_date'],
            merchant_id=filters['merchant_id'],
            start_time=filters['start_time'],
            end_time=filters['end_time']
        )
        
        if transactions is None:
            print("❌ Failed to fetch transactions")
            return
        
        if not transactions:
            print("\n✅ No INITIATED transactions found with the specified filters.")
            return
        
        # Display transactions
        display_transactions(transactions)
        
        # Confirmation
        print("\n" + "="*80)
        print("⚠️  WARNING: This action will:")
        print("   1. Mark all above transactions as FAILED")
        print(f"   2. Set error message: '{FAILED_MESSAGE}'")
        if filters['send_callbacks']:
            print("   3. Send failure callbacks to merchant URLs")
        print("="*80)
        
        confirm = input("\n❓ Proceed with processing? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("\n❌ Operation cancelled.")
            return
        
        # Double confirmation
        confirm2 = input("❓ Type 'CONFIRM' to proceed: ").strip()
        
        if confirm2 != 'CONFIRM':
            print("\n❌ Operation cancelled.")
            return
        
        # Process transactions
        results = processor.process_transactions(
            transactions=transactions,
            send_callbacks=filters['send_callbacks']
        )
        
        # Display results
        print("\n" + "="*80)
        print("📊 Processing Complete")
        print("="*80)
        print(f"✅ Transactions Processed: {results['processed']}/{results['total']}")
        
        if filters['send_callbacks']:
            print(f"✅ Callbacks Successful: {results['callback_success']}")
            print(f"❌ Callbacks Failed: {results['callback_failed']}")
        
        if results['errors']:
            print(f"\n⚠️  Errors encountered: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(results['errors']) > 5:
                print(f"   ... and {len(results['errors']) - 5} more")
        
        print("\n" + "="*80)
        print("✅ Operation completed successfully")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
