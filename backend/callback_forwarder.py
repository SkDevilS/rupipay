"""
Callback Forwarder Utility
Handles forwarding payout callbacks to merchant-provided callback URLs
"""

import requests
import json
from datetime import datetime
from database import get_db_connection

def forward_payout_callback(txn_id, merchant_id, callback_url, callback_data):
    """
    Forward payout callback to merchant's callback URL
    
    Args:
        txn_id: Transaction ID
        merchant_id: Merchant ID
        callback_url: URL to forward callback to
        callback_data: Callback data to send
        
    Returns:
        dict: Result of callback forwarding
    """
    if not callback_url:
        return {'success': False, 'message': 'No callback URL provided'}
    
    print(f"📤 Forwarding callback to: {callback_url}")
    print(f"Callback data: {json.dumps(callback_data, indent=2)}")
    
    conn = get_db_connection()
    
    try:
        response = requests.post(
            callback_url,
            json=callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"✅ Callback response: {response.status_code}")
        
        # Log callback attempt
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txn_id,
                        callback_url,
                        json.dumps(callback_data),
                        response.status_code,
                        response.text[:1000]
                    ))
                    conn.commit()
            except Exception as log_error:
                print(f"⚠️  Failed to log callback: {log_error}")
        
        return {
            'success': True,
            'status_code': response.status_code,
            'response': response.text[:500]
        }
        
    except requests.exceptions.Timeout:
        error_msg = 'Callback request timed out'
        print(f"❌ {error_msg}")
        
        # Log failed callback
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txn_id,
                        callback_url,
                        json.dumps(callback_data),
                        0,
                        error_msg
                    ))
                    conn.commit()
            except Exception as log_error:
                print(f"⚠️  Failed to log callback: {log_error}")
        
        return {'success': False, 'message': error_msg}
        
    except requests.exceptions.RequestException as e:
        error_msg = f'Callback request failed: {str(e)}'
        print(f"❌ {error_msg}")
        
        # Log failed callback
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txn_id,
                        callback_url,
                        json.dumps(callback_data),
                        0,
                        str(e)[:1000]
                    ))
                    conn.commit()
            except Exception as log_error:
                print(f"⚠️  Failed to log callback: {log_error}")
        
        return {'success': False, 'message': error_msg}
        
    except Exception as e:
        error_msg = f'Unexpected error: {str(e)}'
        print(f"❌ {error_msg}")
        return {'success': False, 'message': error_msg}
        
    finally:
        if conn:
            conn.close()


def forward_payin_callback(txn_id, merchant_id, callback_url, callback_data):
    """
    Forward payin callback to merchant's callback URL
    
    Args:
        txn_id: Transaction ID
        merchant_id: Merchant ID
        callback_url: URL to forward callback to
        callback_data: Callback data to send
        
    Returns:
        dict: Result of callback forwarding
    """
    if not callback_url:
        return {'success': False, 'message': 'No callback URL provided'}
    
    print(f"📤 Forwarding payin callback to: {callback_url}")
    print(f"Callback data: {json.dumps(callback_data, indent=2)}")
    
    conn = get_db_connection()
    
    try:
        response = requests.post(
            callback_url,
            json=callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"✅ Callback response: {response.status_code}")
        print(f"Response body: {response.text[:200]}")
        
        # Log callback attempt
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txn_id,
                        callback_url,
                        json.dumps(callback_data),
                        response.status_code,
                        response.text[:1000]
                    ))
                    conn.commit()
            except Exception as log_error:
                print(f"⚠️  Failed to log callback: {log_error}")
        
        return {
            'success': True,
            'status_code': response.status_code,
            'response': response.text[:500]
        }
        
    except requests.exceptions.Timeout:
        error_msg = 'Callback request timed out'
        print(f"❌ {error_msg}")
        
        # Log failed callback
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txn_id,
                        callback_url,
                        json.dumps(callback_data),
                        0,
                        error_msg
                    ))
                    conn.commit()
            except Exception as log_error:
                print(f"⚠️  Failed to log callback: {log_error}")
        
        return {'success': False, 'message': error_msg}
        
    except requests.exceptions.RequestException as e:
        error_msg = f'Callback request failed: {str(e)}'
        print(f"❌ {error_msg}")
        
        # Log failed callback
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO callback_logs 
                        (merchant_id, txn_id, callback_url, request_data, response_code, response_data, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        merchant_id,
                        txn_id,
                        callback_url,
                        json.dumps(callback_data),
                        0,
                        str(e)[:1000]
                    ))
                    conn.commit()
            except Exception as log_error:
                print(f"⚠️  Failed to log callback: {log_error}")
        
        return {'success': False, 'message': error_msg}
        
    except Exception as e:
        error_msg = f'Unexpected error: {str(e)}'
        print(f"❌ {error_msg}")
        return {'success': False, 'message': error_msg}
        
    finally:
        if conn:
            conn.close()


def get_transaction_callback_url(txn_id):
    """
    Get callback URL for a specific transaction
    
    Args:
        txn_id: Transaction ID
        
    Returns:
        tuple: (callback_url, merchant_id, reference_id) or (None, None, None)
    """
    conn = get_db_connection()
    if not conn:
        return None, None, None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT callback_url, merchant_id, reference_id
                FROM payout_transactions
                WHERE txn_id = %s
            """, (txn_id,))
            
            result = cursor.fetchone()
            
            if result:
                return result['callback_url'], result['merchant_id'], result['reference_id']
            
            return None, None, None
            
    except Exception as e:
        print(f"❌ Error fetching callback URL: {e}")
        return None, None, None
        
    finally:
        conn.close()
