#!/usr/bin/env python3
"""
Check raw ViyonaPay callback data from server logs
"""

import subprocess
import json
import re

def check_callback_in_logs():
    """Check server logs for ViyonaPay callback data"""
    print("\n" + "="*80)
    print("  ViyonaPay Callback Raw Data Check")
    print("="*80)
    
    try:
        # Get recent logs from systemd
        print("\n🔍 Searching systemd logs for ViyonaPay callbacks...")
        
        cmd = [
            'sudo', 'journalctl', '-u', 'moneyone-api',
            '-n', '1000', '--no-pager'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            print(f"❌ Error reading logs: {result.stderr}")
            return
        
        logs = result.stdout
        
        # Look for ViyonaPay callback entries
        callback_entries = []
        lines = logs.split('\n')
        
        for i, line in enumerate(lines):
            if 'VIYONAPAY Payin Callback Received' in line:
                # Found callback start, collect next 50 lines
                entry = '\n'.join(lines[i:min(i+50, len(lines))])
                callback_entries.append(entry)
        
        if not callback_entries:
            print("\n❌ No ViyonaPay callback entries found in logs")
            print("\n💡 Checking for any /api/callback/viyonapay/payin hits...")
            
            # Check for endpoint hits
            endpoint_hits = []
            for line in lines:
                if '/api/callback/viyonapay/payin' in line:
                    endpoint_hits.append(line)
            
            if endpoint_hits:
                print(f"\n✅ Found {len(endpoint_hits)} endpoint hits:")
                for hit in endpoint_hits[-10:]:
                    print(hit)
            else:
                print("\n❌ No hits to callback endpoint found")
                print("\n📋 This means ViyonaPay has NOT sent any callbacks yet")
                print("\n🔧 Possible reasons:")
                print("   1. Callback URL not configured with ViyonaPay")
                print("   2. ViyonaPay IP blocked by firewall")
                print("   3. ViyonaPay sends callbacks with delay")
                print("   4. Transaction was not actually completed")
            
            return
        
        print(f"\n✅ Found {len(callback_entries)} ViyonaPay callback(s):\n")
        
        for idx, entry in enumerate(callback_entries, 1):
            print(f"\n{'='*80}")
            print(f"CALLBACK #{idx}")
            print(f"{'='*80}")
            
            # Extract webhook payload
            payload_match = re.search(r'📦 Webhook Payload:\n(.*?)(?=\n\n|\n📋|\nStep|$)', entry, re.DOTALL)
            if payload_match:
                try:
                    payload_text = payload_match.group(1).strip()
                    # Try to parse as JSON
                    payload = json.loads(payload_text)
                    print("\n📦 Webhook Payload:")
                    print(json.dumps(payload, indent=2))
                    
                    # Extract key details
                    print(f"\n💳 Key Details:")
                    print(f"  Order ID: {payload.get('orderId', 'N/A')}")
                    print(f"  Transaction ID: {payload.get('transactionId', 'N/A')}")
                    print(f"  Status: {payload.get('paymentStatus', 'N/A')}")
                    print(f"  Amount: ₹{payload.get('amount', 'N/A')}")
                    print(f"  Bank Ref: {payload.get('bankRefId', 'N/A')}")
                    print(f"  Payment Mode: {payload.get('paymentMode', 'N/A')}")
                    
                except json.JSONDecodeError:
                    print("\n📦 Raw Payload (not JSON):")
                    print(payload_text)
            
            # Show processing result
            if 'Transaction updated successfully' in entry:
                print("\n✅ Transaction was updated successfully")
            elif 'Transaction not found' in entry:
                print("\n❌ Transaction not found in database")
            elif 'Duplicate callback' in entry:
                print("\n⚠️  Duplicate callback (already processed)")
            
            # Show merchant callback status
            if 'Merchant callback sent successfully' in entry:
                print("✅ Merchant callback forwarded successfully")
            elif 'No merchant callback URL configured' in entry:
                print("⚠️  No merchant callback URL configured")
            elif 'Failed to send merchant callback' in entry:
                print("❌ Failed to forward merchant callback")
        
        print(f"\n{'='*80}\n")
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout reading logs")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_callback_in_logs()
