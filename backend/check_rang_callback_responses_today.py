#!/usr/bin/env python3
"""
Comprehensive Rang Callback Response Checker
Analyzes what data Rang is sending in their callbacks for today's transactions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime, timedelta
import json
import requests

def check_rang_callback_data_structure():
    """Analyze the structure and content of Rang callback data"""
    print("=" * 80)
    print("RANG CALLBACK DATA ANALYSIS - TODAY'S TRANSACTIONS")
    print("=" * 80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get today's Rang transactions with their callback data
        cursor.execute("""
            SELECT 
                pt.txn_id, pt.order_id, pt.merchant_id, pt.amount, 
                pt.status, pt.bank_ref_no, pt.pg_txn_id, pt.callback_url,
                pt.created_at, pt.updated_at, pt.completed_at,
                cl.request_data, cl.response_code, cl.response_data, cl.created_at as callback_time
            FROM payin_transactions pt
            LEFT JOIN callback_logs cl ON pt.txn_id = cl.txn_id
            WHERE pt.pg_partner = 'Rang' 
            AND DATE(pt.created_at) = CURDATE()
            ORDER BY pt.created_at DESC
        """)
        
        transactions = cursor.fetchall()
        
        if not transactions:
            print("❌ No Rang transactions found for today")
            return []
        
        print(f"📊 Found {len(transactions)} Rang transaction(s) today")
        print()
        
        callback_data_samples = []
        
        for i, txn in enumerate(transactions, 1):
            print(f"🔍 TRANSACTION {i}")
            print("=" * 60)
            print(f"TXN ID: {txn['txn_id']}")
            print(f"Order ID: {txn['order_id']}")
            print(f"Merchant: {txn['merchant_id']}")
            print(f"Amount: ₹{txn['amount']}")
            print(f"Current Status: {txn['status']}")
            print(f"Created: {txn['created_at']}")
            print(f"Updated: {txn['updated_at']}")
            
            # Check if callback was received
            if txn['request_data']:
                print(f"✅ CALLBACK RECEIVED at {txn['callback_time']}")
                print(f"Response Code: {txn['response_code']}")
                
                # Parse and analyze callback data
                try:
                    callback_data = json.loads(txn['request_data'])
                    callback_data_samples.append(callback_data)
                    
                    print("\n📋 CALLBACK DATA STRUCTURE:")
                    print("-" * 40)
                    for key, value in callback_data.items():
                        print(f"  {key}: {value} ({type(value).__name__})")
                    
                    print("\n🔍 RANG SPECIFIC FIELDS:")
                    print("-" * 40)
                    
                    # Analyze Rang-specific fields
                    status_id = callback_data.get('status_id')
                    if status_id:
                        status_mapping = {
                            '1': 'SUCCESS',
                            '2': 'PENDING', 
                            '3': 'FAILED'
                        }
                        mapped_status = status_mapping.get(status_id, 'UNKNOWN')
                        print(f"  Status ID: {status_id} → {mapped_status}")
                    
                    amount = callback_data.get('amount')
                    if amount:
                        print(f"  Amount: {amount}")
                    
                    utr = callback_data.get('utr')
                    if utr:
                        print(f"  UTR: {utr}")
                    else:
                        print(f"  UTR: Not provided")
                    
                    client_id = callback_data.get('client_id')
                    if client_id:
                        print(f"  Client ID: {client_id}")
                    
                    message = callback_data.get('message')
                    if message:
                        print(f"  Message: {message}")
                    
                    # Check for additional fields
                    additional_fields = {}
                    expected_fields = ['status_id', 'amount', 'utr', 'client_id', 'message']
                    for key, value in callback_data.items():
                        if key not in expected_fields:
                            additional_fields[key] = value
                    
                    if additional_fields:
                        print(f"\n🆕 ADDITIONAL FIELDS:")
                        print("-" * 40)
                        for key, value in additional_fields.items():
                            print(f"  {key}: {value}")
                    
                    # Check transaction updates
                    print(f"\n📈 TRANSACTION UPDATES:")
                    print("-" * 40)
                    print(f"  UTR Updated: {txn['bank_ref_no'] or 'No'}")
                    print(f"  PG TXN ID: {txn['pg_txn_id'] or 'No'}")
                    print(f"  Completed At: {txn['completed_at'] or 'No'}")
                    
                except json.JSONDecodeError:
                    print(f"⚠️ Invalid JSON in callback data: {txn['request_data']}")
                except Exception as e:
                    print(f"❌ Error parsing callback data: {e}")
                
                # Show response data
                if txn['response_data']:
                    response_preview = txn['response_data'][:200]
                    if len(txn['response_data']) > 200:
                        response_preview += "..."
                    print(f"\n📤 OUR RESPONSE: {response_preview}")
                
            else:
                print("❌ NO CALLBACK RECEIVED YET")
                
                # Check if transaction is old enough to expect a callback
                time_diff = datetime.now() - txn['created_at']
                if time_diff.total_seconds() > 300:  # 5 minutes
                    print(f"⚠️ Transaction is {int(time_diff.total_seconds()/60)} minutes old - callback expected")
                else:
                    print(f"ℹ️ Transaction is {int(time_diff.total_seconds())} seconds old - may be too recent")
            
            print("\n" + "=" * 60)
            print()
        
        cursor.close()
        conn.close()
        
        return callback_data_samples
        
    except Exception as e:
        print(f"❌ Error analyzing callback data: {str(e)}")
        return []

def analyze_callback_patterns(callback_samples):
    """Analyze patterns in callback data"""
    if not callback_samples:
        print("📊 CALLBACK PATTERN ANALYSIS")
        print("=" * 60)
        print("❌ No callback data available for analysis")
        return
    
    print("📊 CALLBACK PATTERN ANALYSIS")
    print("=" * 60)
    
    # Analyze field consistency
    all_fields = set()
    field_frequency = {}
    
    for sample in callback_samples:
        for field in sample.keys():
            all_fields.add(field)
            field_frequency[field] = field_frequency.get(field, 0) + 1
    
    print(f"Total callback samples: {len(callback_samples)}")
    print(f"Unique fields found: {len(all_fields)}")
    print()
    
    print("🔍 FIELD FREQUENCY:")
    print("-" * 40)
    for field, count in sorted(field_frequency.items()):
        percentage = (count / len(callback_samples)) * 100
        print(f"  {field}: {count}/{len(callback_samples)} ({percentage:.1f}%)")
    
    # Analyze status distribution
    status_distribution = {}
    for sample in callback_samples:
        status = sample.get('status_id', 'unknown')
        status_distribution[status] = status_distribution.get(status, 0) + 1
    
    if status_distribution:
        print(f"\n📈 STATUS DISTRIBUTION:")
        print("-" * 40)
        for status, count in status_distribution.items():
            status_name = {
                '1': 'SUCCESS',
                '2': 'PENDING',
                '3': 'FAILED'
            }.get(status, status)
            print(f"  {status} ({status_name}): {count}")
    
    # Check for UTR presence
    utr_provided = sum(1 for sample in callback_samples if sample.get('utr'))
    print(f"\n💳 UTR ANALYSIS:")
    print("-" * 40)
    print(f"  Callbacks with UTR: {utr_provided}/{len(callback_samples)}")
    print(f"  UTR provision rate: {(utr_provided/len(callback_samples)*100):.1f}%")
    
    # Sample callback structure
    if callback_samples:
        print(f"\n📋 SAMPLE CALLBACK STRUCTURE:")
        print("-" * 40)
        sample = callback_samples[0]
        print(json.dumps(sample, indent=2))

def check_server_logs_for_rang():
    """Check if there are any server-side logs for Rang callbacks"""
    print("\n🔍 SERVER LOG ANALYSIS")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for any Rang-related entries in various log tables
        # This is a general check - actual log table structure may vary
        
        print("Checking for Rang-related log entries...")
        
        # Check callback_logs for any Rang mentions
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM callback_logs 
            WHERE DATE(created_at) = CURDATE()
            AND (
                request_data LIKE '%rang%' 
                OR request_data LIKE '%Rang%'
                OR callback_url LIKE '%rang%'
            )
        """)
        
        rang_log_count = cursor.fetchone()['count']
        print(f"Rang callback logs today: {rang_log_count}")
        
        # Check for recent Rang transactions that got updated
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM payin_transactions 
            WHERE pg_partner = 'Rang'
            AND DATE(created_at) = CURDATE()
            AND updated_at > created_at
        """)
        
        updated_txns = cursor.fetchone()['count']
        print(f"Rang transactions updated today: {updated_txns}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking server logs: {e}")

def test_callback_endpoint():
    """Test the Rang callback endpoint with sample data"""
    print("\n🧪 CALLBACK ENDPOINT TEST")
    print("=" * 60)
    
    test_url = "https://api.moneyone.co.in/test-rang-callback"
    
    # Test with sample Rang callback data
    test_data = {
        'status_id': '1',
        'amount': '100.00',
        'utr': 'TEST123456789',
        'client_id': 'TEST_ORDER_123',
        'message': 'Payment successful'
    }
    
    print(f"Testing endpoint: {test_url}")
    print(f"Test data: {json.dumps(test_data, indent=2)}")
    
    try:
        # Test JSON format
        print("\n📤 Testing JSON format...")
        response = requests.post(
            test_url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        # Test form data format
        print("\n📤 Testing form data format...")
        response = requests.post(
            test_url,
            data=test_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")

def generate_callback_report():
    """Generate a comprehensive report"""
    print("\n📋 COMPREHENSIVE CALLBACK REPORT")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Summary statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN status = 'INITIATED' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN bank_ref_no IS NOT NULL THEN 1 ELSE 0 END) as utr_received,
                SUM(amount) as total_amount
            FROM payin_transactions 
            WHERE pg_partner = 'Rang' 
            AND DATE(created_at) = CURDATE()
        """)
        
        stats = cursor.fetchone()
        
        print(f"📊 TODAY'S RANG STATISTICS:")
        print("-" * 50)
        print(f"Total Transactions: {stats['total_transactions']}")
        print(f"Successful: {stats['success_count']}")
        print(f"Failed: {stats['failed_count']}")
        print(f"Pending: {stats['pending_count']}")
        print(f"UTR Received: {stats['utr_received']}")
        print(f"Total Amount: ₹{stats['total_amount'] or 0}")
        
        # Callback reception rate
        cursor.execute("""
            SELECT COUNT(*) as callbacks_received
            FROM payin_transactions pt
            JOIN callback_logs cl ON pt.txn_id = cl.txn_id
            WHERE pt.pg_partner = 'Rang' 
            AND DATE(pt.created_at) = CURDATE()
        """)
        
        callback_stats = cursor.fetchone()
        callback_rate = 0
        if stats['total_transactions'] > 0:
            callback_rate = (callback_stats['callbacks_received'] / stats['total_transactions']) * 100
        
        print(f"\n📡 CALLBACK STATISTICS:")
        print("-" * 50)
        print(f"Callbacks Received: {callback_stats['callbacks_received']}")
        print(f"Callback Rate: {callback_rate:.1f}%")
        
        # Issues and recommendations
        print(f"\n⚠️ ISSUES & RECOMMENDATIONS:")
        print("-" * 50)
        
        if callback_rate < 100 and stats['total_transactions'] > 0:
            missing_callbacks = stats['total_transactions'] - callback_stats['callbacks_received']
            print(f"• {missing_callbacks} transaction(s) missing callbacks")
            print("• Contact Rang team to verify callback URL configuration")
            print("• Callback URL: https://api.moneyone.co.in/rang-payin-callback")
        
        if stats['utr_received'] < stats['success_count']:
            print(f"• Some successful transactions missing UTR")
            print("• Verify Rang is sending UTR in callback data")
        
        if callback_rate == 100:
            print("✅ All transactions received callbacks - system working properly")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")

def main():
    """Main execution function"""
    print("🔍 RANG CALLBACK RESPONSE ANALYZER")
    print("=" * 80)
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Purpose: Analyze what data Rang is sending in their callbacks")
    print()
    
    # Step 1: Analyze callback data structure
    callback_samples = check_rang_callback_data_structure()
    
    # Step 2: Analyze patterns in callback data
    analyze_callback_patterns(callback_samples)
    
    # Step 3: Check server logs
    check_server_logs_for_rang()
    
    # Step 4: Test callback endpoint
    test_callback_endpoint()
    
    # Step 5: Generate comprehensive report
    generate_callback_report()
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETED")
    print("=" * 80)
    print()
    print("📋 NEXT STEPS:")
    print("1. Review callback data structure above")
    print("2. Verify all expected fields are being sent by Rang")
    print("3. Check if UTR is provided for successful transactions")
    print("4. Contact Rang team if any issues found")
    print("5. Monitor callback reception rate")

if __name__ == "__main__":
    main()