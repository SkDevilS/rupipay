#!/usr/bin/env python3
"""
Enhanced Airpay callback logging - logs EVERYTHING to a file
Add this to airpay_callback_routes.py to capture raw callback data
"""

import json
from datetime import datetime
import os

def log_raw_callback(request, description=""):
    """
    Log raw callback data to a file for debugging
    """
    try:
        log_dir = '/var/www/moneyone/moneyone/backend/logs'
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'airpay_callbacks_{datetime.now().strftime("%Y%m%d")}.log')
        
        with open(log_file, 'a') as f:
            f.write("\n" + "=" * 100 + "\n")
            f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
            f.write(f"DESCRIPTION: {description}\n")
            f.write("-" * 100 + "\n")
            
            # Log request details
            f.write(f"METHOD: {request.method}\n")
            f.write(f"URL: {request.url}\n")
            f.write(f"PATH: {request.path}\n")
            f.write(f"CONTENT-TYPE: {request.content_type}\n")
            
            # Log headers
            f.write("\nHEADERS:\n")
            for key, value in request.headers.items():
                f.write(f"  {key}: {value}\n")
            
            # Log query parameters
            if request.args:
                f.write("\nQUERY PARAMETERS:\n")
                for key, value in request.args.items():
                    f.write(f"  {key}: {value}\n")
            
            # Log form data
            if request.form:
                f.write("\nFORM DATA:\n")
                for key, value in request.form.items():
                    f.write(f"  {key}: {value}\n")
            
            # Log JSON data
            try:
                if request.is_json:
                    json_data = request.get_json()
                    f.write("\nJSON DATA:\n")
                    f.write(json.dumps(json_data, indent=2))
                    f.write("\n")
            except:
                pass
            
            # Log raw data
            try:
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    f.write("\nRAW DATA:\n")
                    f.write(raw_data)
                    f.write("\n")
            except:
                pass
            
            f.write("=" * 100 + "\n\n")
        
        print(f"✓ Raw callback logged to: {log_file}")
        
    except Exception as e:
        print(f"Error logging raw callback: {e}")

# Instructions to add to airpay_callback_routes.py:
"""
Add this at the top of airpay_payin_callback() function:

from log_airpay_callback_raw import log_raw_callback

@airpay_callback_bp.route('/payin', methods=['POST'])
def airpay_payin_callback():
    # ADD THIS LINE FIRST
    log_raw_callback(request, "Airpay Payin Callback Received")
    
    try:
        print(f"=== Airpay V4 Payin Callback Received ===")
        # ... rest of the code
"""
