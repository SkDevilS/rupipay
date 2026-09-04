"""
Check Most Recent PayTouchPayin Callback
Simple script to verify callback handling is working
"""

from database_pooled import get_db_connection
from datetime import datetime
import json

def check_recent_paytouchpayin():
    """Check the most recent PayTouchPayin transaction"""
    
    print("\n" + "="*80)
    print("🔍 MOST RECENT PAYTOUCHPAYIN TRANSACTION")
    print("="*80)
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check payin_transactions table first (new structure)
    print("\n📋 Checking payin_transactions table...")
    cursor.execute("""
        SELECT txn_id, merchant_id, order_id, status, amount, 
               charge_amount, pg_txn_id, payment_url, 
               created_at, updated_at
        FROM payin_transactions
        WHERE pg_partner = 'paytouchpayin'
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    txn = cursor.fetchone()
    
    if txn:
        print("\n✅ Found transaction in payin_transactions:")
        print(f"\n  Transaction ID:  {txn[0]}")
        print(f"  Merchant ID:     {txn[1]}")
        print(f"  Order ID:        {txn[2]}")
        print(f"  Status:          {txn[3]}")
        print(f"  Amount:          ₹{txn[4]}")
        print(f"  Charge:          ₹{txn[5]}")
        print(f"  PG TXN ID:       {txn[6]}")
        print(f"  UPI String:      {txn[7][:50] if txn[7] else 'N/A'}...")
        print(f"  Created:         {txn[8]}")
        print(f"  Updated:         {txn[9]}")
        
        # Check if merchant callback was sent
        merchant_id = txn[1]
        txn_id = txn[0]
        
        print(f"\n📞 Checking merchant callback configuration...")
        cursor.execute("""
            SELECT callback_url
            FROM merchants
            WHERE merchant_id = %s
        """, (merchant_id,))
        
        merchant = cursor.fetchone()
        
        if merchant and merchant[0]:
            print(f"  Callback URL:    {merchant[0]}")
            
            # Check if callback was logged
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'callback_logs'
            """)
            
            if cursor.fetchone()[0] > 0:
                cursor.execute("""
                    SELECT id, response_code, created_at
                    FROM callback_logs
                    WHERE txn_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (txn_id,))
                
                callback_log = cursor.fetchone()
                
                if callback_log:
                    print(f"\n  ✅ Callback sent:")
                    print(f"     Log ID:       {callback_log[0]}")
                    print(f"     Response:     {callback_log[1]}")
                    print(f"     Sent At:      {callback_log[2]}")
                else:
                    print(f"\n  ⚠️  No callback log found for this transaction")
            else:
                print(f"\n  ℹ️  callback_logs table does not exist")
        else:
            print(f"  ⚠️  No callback URL configured for merchant")
        
        # Check wallet credit
        print(f"\n💰 Checking wallet credit...")
        cursor.execute("""
            SELECT unsettled_wallet, settled_wallet
            FROM merchants
            WHERE merchant_id = %s
        """, (merchant_id,))
        
        wallet = cursor.fetchone()
        
        if wallet:
            print(f"  Unsettled Wallet: ₹{wallet[0]}")
            print(f"  Settled Wallet:   ₹{wallet[1]}")
        
        # Check transaction log
        cursor.execute("""
            SELECT txn_type, amount, created_at
            FROM transactions
            WHERE merchant_id = %s AND reference_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (merchant_id, txn_id))
        
        txn_log = cursor.fetchone()
        
        if txn_log:
            print(f"\n  ✅ Transaction logged:")
            print(f"     Type:         {txn_log[0]}")
            print(f"     Amount:       ₹{txn_log[1]}")
            print(f"     Created:      {txn_log[2]}")
        else:
            print(f"\n  ⚠️  No transaction log found")
    else:
        print("\n❌ No transactions found in payin_transactions")
        
        # Check payin table (fallback)
        print("\n📋 Checking payin table (fallback)...")
        cursor.execute("""
            SELECT txn_id, merchant_id, status, amount, utr,
                   pg_txn_id, created_at, updated_at
            FROM payin
            WHERE pg_partner = 'paytouchpayin'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        old_txn = cursor.fetchone()
        
        if old_txn:
            print("\n✅ Found transaction in payin table:")
            print(f"\n  Transaction ID:  {old_txn[0]}")
            print(f"  Merchant ID:     {old_txn[1]}")
            print(f"  Status:          {old_txn[2]}")
            print(f"  Amount:          ₹{old_txn[3]}")
            print(f"  UTR:             {old_txn[4]}")
            print(f"  PG TXN ID:       {old_txn[5]}")
            print(f"  Created:         {old_txn[6]}")
            print(f"  Updated:         {old_txn[7]}")
        else:
            print("\n❌ No transactions found in payin table either")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ CHECK COMPLETE")
    print("="*80)
    
    print("\n💡 Next Steps:")
    print("  1. If status is still 'INITIATED' or 'pending', callback not received")
    print("  2. Check server logs: sudo journalctl -u moneyone-backend -f | grep -i paytouchpayin")
    print("  3. Verify callback URL with PayTouch team")
    print("  4. Test with a new transaction")


if __name__ == "__main__":
    try:
        print("Initializing database connection pool...")
        check_recent_paytouchpayin()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
