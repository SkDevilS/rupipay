import json
from database import get_db_connection

def diagnose_balance():
    conn = get_db_connection()
    if not conn:
        print("Database connection failed")
        return
        
    try:
        with conn.cursor() as cursor:
            # Check all merchant wallets
            cursor.execute("""
                SELECT merchant_id, balance, settled_balance, unsettled_balance, last_updated 
                FROM merchant_wallet
            """)
            wallets = cursor.fetchall()
            
            print("="*60)
            print("MERCHANT WALLET BALANCES")
            print("="*60)
            print(f"{'Merchant ID':<15} | {'Settled':<10} | {'Unsettled':<10} | {'Balance':<10}")
            print("-" * 60)
            
            target_merchant = None
            for w in wallets:
                settled = float(w['settled_balance']) if w['settled_balance'] else 0.0
                unsettled = float(w['unsettled_balance']) if w['unsettled_balance'] else 0.0
                balance = float(w['balance']) if w['balance'] else 0.0
                print(f"{w['merchant_id']:<15} | {settled:<10.2f} | {unsettled:<10.2f} | {balance:<10.2f}")
                
                if settled == 99.50 or settled == 201.00:
                    target_merchant = w['merchant_id']
            
            if target_merchant:
                print("\n" + "="*80)
                print(f"RECENT WALLET TRANSACTIONS FOR TARGET MERCHANT: {target_merchant}")
                print("="*80)
                
                cursor.execute("""
                    SELECT txn_id, txn_type, amount, balance_before, balance_after, description, created_at
                    FROM merchant_wallet_transactions
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (target_merchant,))
                
                transactions = cursor.fetchall()
                print(f"{'Time':<20} | {'Type':<8} | {'Amount':<8} | {'Before':<8} | {'After':<8} | {'Description'}")
                print("-" * 80)
                for t in transactions:
                    dt_str = t['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                    print(f"{dt_str:<20} | {t['txn_type']:<8} | {float(t['amount']):<8.2f} | {float(t['balance_before']):<8.2f} | {float(t['balance_after']):<8.2f} | {t['description']}")
            
            print("\n" + "="*80)
            print("RECENT PAYOUT TRANSACTIONS WITH PAYTOUCH5 COCO")
            print("="*80)
            
            cursor.execute("""
                SELECT txn_id, merchant_id, amount, charge_amount, status, error_message, created_at
                FROM payout_transactions
                WHERE pg_partner = 'Paytouch5_Coco'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            payouts = cursor.fetchall()
            print(f"{'Txn ID':<25} | {'Merchant':<15} | {'Amt':<6} | {'Chg':<6} | {'Status':<10} | {'Error'}")
            print("-" * 80)
            for p in payouts:
                dt_str = p['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                error = p['error_message'] or ''
                # Truncate error for display
                if len(error) > 40: error = error[:37] + "..."
                print(f"{p['txn_id']:<25} | {p['merchant_id']:<15} | {float(p['amount']):<6.2f} | {float(p['charge_amount']):<6.2f} | {p['status']:<10} | {error}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    diagnose_balance()
