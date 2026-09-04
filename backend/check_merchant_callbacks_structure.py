#!/usr/bin/env python3
"""
Check merchant_callbacks table structure and data
"""

from database import get_db_connection

def check_structure():
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed!")
        return
    
    try:
        with conn.cursor() as cursor:
            print("=" * 80)
            print("MERCHANT_CALLBACKS TABLE STRUCTURE")
            print("=" * 80)
            
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'merchant_callbacks'")
            if not cursor.fetchone():
                print("❌ merchant_callbacks table does NOT exist!")
                print("\nYou need to create it:")
                print("""
CREATE TABLE merchant_callbacks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    merchant_id VARCHAR(50) NOT NULL UNIQUE,
    payin_callback_url VARCHAR(500),
    payout_callback_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_merchant_id (merchant_id)
);
                """)
                return
            
            print("✓ Table exists\n")
            
            # Show structure
            print("Columns:")
            cursor.execute("SHOW COLUMNS FROM merchant_callbacks")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']} {col['Null']} {col['Key']} {col['Default']}")
            
            print("\n" + "=" * 80)
            print("MERCHANT CALLBACK CONFIGURATIONS")
            print("=" * 80)
            
            # Show all merchants
            cursor.execute("""
                SELECT merchant_id, payin_callback_url, payout_callback_url, 
                       created_at, updated_at
                FROM merchant_callbacks
            """)
            merchants = cursor.fetchall()
            
            if merchants:
                print(f"\nFound {len(merchants)} merchant(s) in table:\n")
                for m in merchants:
                    print(f"Merchant: {m['merchant_id']}")
                    print(f"  Payin Callback:  {m['payin_callback_url'] or 'NOT SET'}")
                    print(f"  Payout Callback: {m['payout_callback_url'] or 'NOT SET'}")
                    print(f"  Created: {m['created_at']}")
                    print(f"  Updated: {m['updated_at']}")
                    print()
            else:
                print("\n⚠ No merchants configured in merchant_callbacks table")
                print("\nTo add a merchant callback URL:")
                print("""
INSERT INTO merchant_callbacks (merchant_id, payin_callback_url)
VALUES ('YOUR_MERCHANT_ID', 'https://merchant-domain.com/callback')
ON DUPLICATE KEY UPDATE 
    payin_callback_url = 'https://merchant-domain.com/callback';
                """)
            
            print("=" * 80)
            print("RECENT PAYIN TRANSACTIONS WITH CALLBACK URLs")
            print("=" * 80)
            
            cursor.execute("""
                SELECT txn_id, merchant_id, order_id, status, callback_url, 
                       pg_partner, created_at
                FROM payin_transactions
                WHERE pg_partner = 'Mudrape'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            txns = cursor.fetchall()
            
            if txns:
                print(f"\nFound {len(txns)} recent Mudrape transaction(s):\n")
                for t in txns:
                    print(f"TXN: {t['txn_id']}")
                    print(f"  Merchant: {t['merchant_id']}")
                    print(f"  Order ID: {t['order_id']}")
                    print(f"  Status: {t['status']}")
                    print(f"  Callback URL: {t['callback_url'] or '❌ NOT SET'}")
                    print(f"  Created: {t['created_at']}")
                    print()
                
                # Count how many have callback URLs
                with_callback = sum(1 for t in txns if t['callback_url'])
                without_callback = len(txns) - with_callback
                
                print(f"Summary: {with_callback} with callback URL, {without_callback} without")
                
                if without_callback > 0:
                    print("\n⚠ WARNING: Some transactions don't have callback URLs!")
                    print("   This means callbacks won't be forwarded to merchants.")
            else:
                print("\n⚠ No Mudrape payin transactions found")
            
    finally:
        conn.close()

if __name__ == '__main__':
    check_structure()
