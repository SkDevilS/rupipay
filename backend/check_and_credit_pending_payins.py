"""
Check pending payins and credit wallet if they're actually successful
This polls Mudrape for status updates instead of waiting for callbacks
"""

import pymysql
from database import get_db_connection
from mudrape_service import MudrapeService
from wallet_service import wallet_service
from datetime import datetime, timedelta

def check_and_credit_pending_payins():
    """Check INITIATED payins and update status + credit wallet if successful"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    
    mudrape_service = MudrapeService()
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("CHECKING PENDING PAYINS FOR STATUS UPDATES")
            print("=" * 80)
            
            # Get INITIATED payins from last 24 hours
            cursor.execute("""
                SELECT 
                    txn_id, merchant_id, order_id, amount, charge_amount, net_amount,
                    status, pg_partner, created_at
                FROM payin_transactions
                WHERE status = 'INITIATED'
                AND pg_partner = 'Mudrape'
                AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY created_at DESC
            """)
            
            pending_payins = cursor.fetchall()
            
            if not pending_payins:
                print("\n✅ No pending payins found")
                return
            
            print(f"\nFound {len(pending_payins)} pending payins\n")
            
            updated_count = 0
            credited_count = 0
            
            for payin in pending_payins:
                print(f"\n{'='*70}")
                print(f"Checking: {payin['txn_id']}")
                print(f"Order ID: {payin['order_id']}")
                print(f"Amount: ₹{payin['amount']}")
                print(f"Created: {payin['created_at']}")
                
                # Check status with Mudrape
                status_result = mudrape_service.check_payment_status(payin['order_id'])
                
                if status_result.get('success'):
                    mudrape_status = status_result.get('status', '').upper()
                    utr = status_result.get('utr')
                    txn_id_from_mudrape = status_result.get('txnId')
                    
                    print(f"Mudrape Status: {mudrape_status}")
                    print(f"UTR: {utr}")
                    
                    if mudrape_status == 'SUCCESS':
                        # Check if wallet already credited
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM merchant_wallet_transactions
                            WHERE reference_id = %s AND txn_type = 'UNSETTLED_CREDIT'
                        """, (payin['txn_id'],))
                        
                        already_credited = cursor.fetchone()['count'] > 0
                        
                        if already_credited:
                            print(f"⚠ Wallet already credited, just updating status")
                            
                            # Update transaction status
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'SUCCESS', bank_ref_no = %s, pg_txn_id = %s,
                                    completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (utr, txn_id_from_mudrape, payin['txn_id']))
                            conn.commit()
                            updated_count += 1
                        else:
                            print(f"✅ Payment successful! Crediting wallet...")
                            
                            # Update transaction status
                            cursor.execute("""
                                UPDATE payin_transactions
                                SET status = 'SUCCESS', bank_ref_no = %s, pg_txn_id = %s,
                                    completed_at = NOW(), updated_at = NOW()
                                WHERE txn_id = %s
                            """, (utr, txn_id_from_mudrape, payin['txn_id']))
                            
                            # Credit merchant unsettled wallet
                            merchant_result = wallet_service.credit_unsettled_wallet(
                                merchant_id=payin['merchant_id'],
                                amount=float(payin['net_amount']),
                                description=f"Payin credited (status poll) - {payin['order_id']}",
                                reference_id=payin['txn_id']
                            )
                            
                            if merchant_result['success']:
                                print(f"✅ Merchant wallet credited: ₹{payin['net_amount']}")
                                
                                # Credit admin unsettled wallet
                                admin_result = wallet_service.credit_admin_unsettled_wallet(
                                    admin_id='admin',
                                    amount=float(payin['charge_amount']),
                                    description=f"Payin charge (status poll) - {payin['order_id']}",
                                    reference_id=payin['txn_id']
                                )
                                
                                if admin_result['success']:
                                    print(f"✅ Admin wallet credited: ₹{payin['charge_amount']}")
                                    conn.commit()
                                    updated_count += 1
                                    credited_count += 1
                                else:
                                    print(f"❌ Admin wallet credit failed: {admin_result.get('message')}")
                                    conn.rollback()
                            else:
                                print(f"❌ Merchant wallet credit failed: {merchant_result.get('message')}")
                                conn.rollback()
                    
                    elif mudrape_status == 'FAILED':
                        print(f"❌ Payment failed")
                        
                        # Update transaction status
                        cursor.execute("""
                            UPDATE payin_transactions
                            SET status = 'FAILED', bank_ref_no = %s, updated_at = NOW()
                            WHERE txn_id = %s
                        """, (utr, payin['txn_id']))
                        conn.commit()
                        updated_count += 1
                    
                    else:
                        print(f"⏳ Still pending...")
                else:
                    print(f"⚠ Could not check status: {status_result.get('message')}")
            
            print(f"\n{'='*80}")
            print(f"SUMMARY")
            print(f"{'='*80}")
            print(f"Total Pending Checked: {len(pending_payins)}")
            print(f"Status Updated: {updated_count}")
            print(f"Wallets Credited: {credited_count}")
            print(f"{'='*80}")
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_and_credit_pending_payins()
