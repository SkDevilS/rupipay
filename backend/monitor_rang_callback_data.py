#!/usr/bin/env python3
"""
Real-time Rang Callback Data Monitor
Monitors and logs exactly what data Rang is sending in their callbacks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from datetime import datetime, timedelta
import json
import time

def monitor_rang_callbacks_live():
    """Monitor Rang callbacks in real-time"""
    print("🔴 LIVE RANG CALLBACK MONITOR")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Monitoring for new Rang callbacks...")
    print("Press Ctrl+C to stop")
    print()
    
    last_check_time = datetime.now() - timedelta(minutes=5)
    
    try:
        while True:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check for new callback logs since last check
            cursor.execute("""
                SELECT 
                    cl.id, cl.merchant_id, cl.txn_id, cl.callback_url,
                    cl.request_data, cl.response_code, cl.response_data, cl.created_at,
                    pt.order_id, pt.amount, pt.status, pt.pg_partner
                FROM callback_logs cl
                JOIN payin_transactions pt ON cl.txn_id = pt.txn_id
                WHERE pt.pg_partner = 'Rang'
                AND cl.created_at > %s
                ORDER BY cl.created_at DESC
            """, (last_check_time,))
            
            new_callbacks = cursor.fetchall()
            
            if new_callbacks:
                for callback in new_callbacks:
                    print(f"🆕 NEW RANG CALLBACK DETECTED!")
                    print(f"Time: {callback['created_at']}")
                    print(f"TXN ID: {callback['txn_id']}")
                    print(f"Order ID: {callback['order_id']}")
                    print(f"Amount: ₹{callback['amount']}")
                    print(f"Response Code: {callback['response_code']}")
                    
                    # Parse and display callback data
                    try:
                        callback_data = json.loads(callback['request_data'])
                        print("\n📋 RANG SENT THIS DATA:")
                        print("-" * 40)
                        print(json.dumps(callback_data, indent=2))
                        
                        # Highlight key fields
                        print("\n🔍 KEY FIELDS:")
                        print("-" * 40)
                        print(f"Status ID: {callback_data.get('status_id', 'NOT PROVIDED')}")
                        print(f"Amount: {callback_data.get('amount', 'NOT PROVIDED')}")
                        print(f"UTR: {callback_data.get('utr', 'NOT PROVIDED')}")
                        print(f"Client ID: {callback_data.get('client_id', 'NOT PROVIDED')}")
                        print(f"Message: {callback_data.get('message', 'NOT PROVIDED')}")
                        
                    except json.JSONDecodeError:
                        print(f"\n⚠️ RAW DATA (NOT JSON): {callback['request_data']}")
                    
                    print("\n" + "=" * 60)
                    print()
            
            cursor.close()
            conn.close()
            
            last_check_time = datetime.now()
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error in monitoring: {e}")

def show_recent_rang_data():
    """Show recent Rang callback data from last hour"""
    print("📊 RECENT RANG CALLBACK DATA (Last Hour)")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        cursor.execute("""
            SELECT 
                cl.request_data, cl.response_code, cl.created_at,
                pt.order_id, pt.amount, pt.status
            FROM callback_logs cl
            JOIN payin_transactions pt ON cl.txn_id = pt.txn_id
            WHERE pt.pg_partner = 'Rang'
            AND cl.created_at > %s
            ORDER BY cl.created_at DESC
            LIMIT 10
        """, (one_hour_ago,))
        
        recent_callbacks = cursor.fetchall()
        
        if not recent_callbacks:
            print("❌ No Rang callbacks in the last hour")
            return
        
        print(f"Found {len(recent_callbacks)} callback(s) in the last hour:")
        print()
        
        for i, cb in enumerate(recent_callbacks, 1):
            print(f"Callback {i} - {cb['created_at']}")
            print(f"Order: {cb['order_id']} | Amount: ₹{cb['amount']} | Status: {cb['status']}")
            
            try:
                data = json.loads(cb['request_data'])
                print("Data sent by Rang:")
                for key, value in data.items():
                    print(f"  {key}: {value}")
            except:
                print(f"Raw data: {cb['request_data']}")
            
            print("-" * 50)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def check_callback_format_consistency():
    """Check if Rang is sending consistent data format"""
    print("\n🔍 CALLBACK FORMAT CONSISTENCY CHECK")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all Rang callbacks from today
        cursor.execute("""
            SELECT cl.request_data, cl.created_at
            FROM callback_logs cl
            JOIN payin_transactions pt ON cl.txn_id = pt.txn_id
            WHERE pt.pg_partner = 'Rang'
            AND DATE(cl.created_at) = CURDATE()
            ORDER BY cl.created_at DESC
        """)
        
        callbacks = cursor.fetchall()
        
        if not callbacks:
            print("❌ No callbacks found for today")
            return
        
        print(f"Analyzing {len(callbacks)} callback(s) for format consistency...")
        
        field_sets = []
        content_types = []
        
        for cb in callbacks:
            try:
                data = json.loads(cb['request_data'])
                field_sets.append(set(data.keys()))
                content_types.append('JSON')
            except:
                # Not JSON, might be form data
                content_types.append('NON-JSON')
                field_sets.append(set())
        
        # Check field consistency
        if field_sets:
            common_fields = field_sets[0]
            for field_set in field_sets[1:]:
                common_fields = common_fields.intersection(field_set)
            
            all_fields = set()
            for field_set in field_sets:
                all_fields = all_fields.union(field_set)
            
            print(f"\n📋 FIELD ANALYSIS:")
            print(f"Common fields in ALL callbacks: {sorted(common_fields)}")
            print(f"All fields seen: {sorted(all_fields)}")
            
            # Check for missing fields
            inconsistent_callbacks = 0
            for i, field_set in enumerate(field_sets):
                if field_set != field_sets[0]:
                    inconsistent_callbacks += 1
            
            if inconsistent_callbacks > 0:
                print(f"⚠️ {inconsistent_callbacks} callback(s) have different field structure")
            else:
                print("✅ All callbacks have consistent field structure")
        
        # Check content types
        json_count = content_types.count('JSON')
        non_json_count = content_types.count('NON-JSON')
        
        print(f"\n📤 CONTENT TYPE ANALYSIS:")
        print(f"JSON format: {json_count}")
        print(f"Non-JSON format: {non_json_count}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main function with menu options"""
    print("🔍 RANG CALLBACK DATA MONITOR")
    print("=" * 60)
    print("Choose an option:")
    print("1. Show recent callback data (last hour)")
    print("2. Check format consistency (today)")
    print("3. Start live monitoring")
    print("4. Run all checks")
    print()
    
    try:
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == '1':
            show_recent_rang_data()
        elif choice == '2':
            check_callback_format_consistency()
        elif choice == '3':
            monitor_rang_callbacks_live()
        elif choice == '4':
            show_recent_rang_data()
            check_callback_format_consistency()
            print("\nStarting live monitoring in 3 seconds...")
            time.sleep(3)
            monitor_rang_callbacks_live()
        else:
            print("Invalid choice. Running all checks...")
            show_recent_rang_data()
            check_callback_format_consistency()
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()