"""
Async helpers for background processing
No Redis needed - uses threading for async operations
"""

import threading
import time
from database_pooled import get_db_connection

def call_async(func, *args, **kwargs):
    """
    Execute function in background thread
    
    Usage:
        call_async(my_function, arg1, arg2, kwarg1=value1)
    """
    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Async error in {func.__name__}: {e}")
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    return thread

def update_payin_status(txn_id, status, pg_txn_id=None, payment_url=None, error_message=None):
    """Update payin transaction status in background"""
    conn = get_db_connection()
    if not conn:
        print(f"❌ DB connection failed for txn {txn_id}")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE payin_transactions 
                SET status = %s, 
                    pg_txn_id = %s,
                    payment_url = %s,
                    error_message = %s, 
                    updated_at = NOW()
                WHERE txn_id = %s
            """, (status, pg_txn_id, payment_url, error_message, txn_id))
        conn.commit()
        print(f"✅ Updated payin {txn_id} to {status}")
    except Exception as e:
        print(f"❌ Update error for {txn_id}: {e}")
    finally:
        conn.close()

def update_payout_status(txn_id, status, pg_txn_id=None, utr=None, error_message=None):
    """Update payout transaction status in background"""
    conn = get_db_connection()
    if not conn:
        print(f"❌ DB connection failed for txn {txn_id}")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE payout_transactions 
                SET status = %s, 
                    pg_txn_id = %s,
                    utr = %s,
                    error_message = %s, 
                    updated_at = NOW()
                WHERE txn_id = %s
            """, (status, pg_txn_id, utr, error_message, txn_id))
        conn.commit()
        print(f"✅ Updated payout {txn_id} to {status}")
    except Exception as e:
        print(f"❌ Update error for {txn_id}: {e}")
    finally:
        conn.close()

def call_pg_service_async(pg_partner, service_type, txn_id, amount, data):
    """
    Call payment gateway service in background
    
    Args:
        pg_partner: PG name (MUDRAPE, AIRPAY, etc.)
        service_type: 'PAYIN' or 'PAYOUT'
        txn_id: Transaction ID
        amount: Amount
        data: Request data dict
    """
    def _call():
        try:
            print(f"🔄 Calling {pg_partner} {service_type} for {txn_id}...")
            
            if service_type == 'PAYIN':
                # Import and call payin service
                if pg_partner == 'MUDRAPE':
                    from mudrape_service import MudrapeService
                    service = MudrapeService()
                    response = service.initiate_payin(txn_id, amount, data)
                elif pg_partner == 'AIRPAY':
                    from airpay_service import AirpayService
                    service = AirpayService()
                    response = service.initiate_payin(txn_id, amount, data)
                elif pg_partner == 'VIYONAPAY':
                    from viyonapay_service import ViyonapayService
                    service = ViyonapayService()
                    response = service.initiate_payin(txn_id, amount, data)
                elif pg_partner == 'SKRILLPE':
                    from skrillpe_service import SkrillpeService
                    service = SkrillpeService()
                    response = service.initiate_payin(txn_id, amount, data)
                elif pg_partner == 'RANG':
                    from rang_service import RangService
                    service = RangService()
                    response = service.initiate_payin(txn_id, amount, data)
                else:
                    print(f"❌ Unknown PG partner: {pg_partner}")
                    update_payin_status(txn_id, 'FAILED', None, None, f'Unknown PG: {pg_partner}')
                    return
                
                # Update based on response
                if response.get('success'):
                    update_payin_status(
                        txn_id, 
                        'PENDING',
                        response.get('pg_txn_id'),
                        response.get('payment_url'),
                        None
                    )
                else:
                    update_payin_status(
                        txn_id, 
                        'FAILED',
                        None,
                        None,
                        response.get('message', 'PG call failed')
                    )
            
            elif service_type == 'PAYOUT':
                # Import and call payout service
                if pg_partner == 'PAYTOUCH':
                    from paytouch_service import PaytouchService
                    service = PaytouchService()
                    response = service.initiate_payout(txn_id, amount, data)
                elif pg_partner == 'PAYTOUCH2':
                    from paytouch2_service import Paytouch2Service
                    service = Paytouch2Service()
                    response = service.initiate_payout(txn_id, amount, data)
                elif pg_partner == 'MUDRAPE':
                    from mudrape_service import MudrapeService
                    service = MudrapeService()
                    response = service.initiate_payout(txn_id, amount, data)
                else:
                    print(f"❌ Unknown PG partner: {pg_partner}")
                    update_payout_status(txn_id, 'FAILED', None, None, f'Unknown PG: {pg_partner}')
                    return
                
                # Update based on response
                if response.get('success'):
                    update_payout_status(
                        txn_id, 
                        'INPROCESS',
                        response.get('pg_txn_id'),
                        response.get('utr'),
                        None
                    )
                else:
                    update_payout_status(
                        txn_id, 
                        'FAILED',
                        None,
                        None,
                        response.get('message', 'PG call failed')
                    )
        
        except Exception as e:
            print(f"❌ PG call exception for {txn_id}: {e}")
            if service_type == 'PAYIN':
                update_payin_status(txn_id, 'FAILED', None, None, str(e))
            else:
                update_payout_status(txn_id, 'FAILED', None, None, str(e))
    
    # Start background thread
    thread = threading.Thread(target=_call, daemon=True)
    thread.start()
    print(f"✅ Started async PG call for {txn_id}")
