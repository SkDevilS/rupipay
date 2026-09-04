#!/usr/bin/env python3
"""
Check server logs for ViyonaPay callback attempts
"""

import subprocess
import sys

def check_logs():
    """Check server logs for ViyonaPay callbacks"""
    print("\n" + "="*80)
    print("  Checking Server Logs for ViyonaPay Callbacks")
    print("="*80)
    
    try:
        # Check for ViyonaPay callback logs using journalctl
        print("\n🔍 Searching for ViyonaPay callback entries...")
        
        cmd = [
            'sudo', 'journalctl', '-u', 'moneyone-api',
            '-n', '500', '--no-pager'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ Error reading logs: {result.stderr}")
            print("\n💡 Try running manually:")
            print("   sudo journalctl -u moneyone-api -n 500 | grep -i viyonapay")
            return
        
        logs = result.stdout
        
        # Filter for ViyonaPay related logs
        viyonapay_lines = []
        for line in logs.split('\n'):
            if 'viyonapay' in line.lower() or 'VIYONAPAY' in line:
                viyonapay_lines.append(line)
        
        if viyonapay_lines:
            print(f"\n✅ Found {len(viyonapay_lines)} ViyonaPay-related log entries:\n")
            for line in viyonapay_lines[-50:]:  # Last 50 entries
                print(line)
        else:
            print("\n❌ No ViyonaPay-related logs found")
            print("\n💡 This could mean:")
            print("   1. ViyonaPay hasn't sent any callbacks yet")
            print("   2. The callback URL is incorrect")
            print("   3. ViyonaPay is blocked by firewall/security")
        
        # Also check for callback endpoint hits
        print("\n" + "="*80)
        print("  Checking for /api/callback/viyonapay/payin hits")
        print("="*80)
        
        callback_lines = []
        for line in logs.split('\n'):
            if '/api/callback/viyonapay/payin' in line:
                callback_lines.append(line)
        
        if callback_lines:
            print(f"\n✅ Found {len(callback_lines)} callback endpoint hits:\n")
            for line in callback_lines[-20:]:  # Last 20 entries
                print(line)
        else:
            print("\n❌ No hits to /api/callback/viyonapay/payin endpoint")
            print("\n📋 Expected callback URL:")
            print("   https://api.moneyone.co.in/api/callback/viyonapay/payin")
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout reading logs")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_logs()
