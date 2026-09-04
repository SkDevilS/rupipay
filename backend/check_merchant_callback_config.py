"""
Check Merchant Callback Configuration
Verify which table and column stores the callback URL
"""

from database_pooled import get_db_connection

def check_callback_config():
    """Check callback URL configuration for merchants"""
    
    print("\n" + "="*80)
    print("🔍 CHECKING MERCHANT CALLBACK CONFIGURATION")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check merchants table structure
    print("\n📋 Checking 'merchants' table for callback_url column...")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'merchants'
        AND COLUMN_NAME LIKE '%callback%'
    """)
    
    merchants_columns = cursor.fetchall()
    
    if merchants_columns:
        print("✅ Found callback columns in 'merchants' table:")
        for col in merchants_columns:
            print(f"  - {col[0]} ({col[1]}) - Nullable: {col[2]}")
    else:
        print("❌ No callback columns found in 'merchants' table")
    
    # Check merchant_callbacks table
    print("\n📋 Checking 'merchant_callbacks' table...")
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'merchant_callbacks'
    """)
    
    table_exists = cursor.fetchone()[0] > 0
    
    if table_exists:
        print("✅ 'merchant_callbacks' table exists")
        
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'merchant_callbacks'
            AND COLUMN_NAME LIKE '%callback%'
        """)
        
        callback_columns = cursor.fetchall()
        
        if callback_columns:
            print("  Callback columns:")
            for col in callback_columns:
                print(f"    - {col[0]} ({col[1]}) - Nullable: {col[2]}")
    else:
        print("❌ 'merchant_callbacks' table does NOT exist")
    
    # Check actual merchant data
    print("\n📊 Checking actual merchant callback URLs...")
    
    # Try merchants table first
    cursor.execute("""
        SELECT merchant_id, callback_url
        FROM merchants
        WHERE callback_url IS NOT NULL AND callback_url != ''
        LIMIT 5
    """)
    
    merchants_with_callback = cursor.fetchall()
    
    if merchants_with_callback:
        print(f"\n✅ Found {len(merchants_with_callback)} merchants with callback_url in 'merchants' table:")
        for merchant in merchants_with_callback:
            print(f"  - Merchant: {merchant[0]}")
            print(f"    Callback URL: {merchant[1]}")
    else:
        print("\n⚠️ No merchants found with callback_url in 'merchants' table")
    
    # Try merchant_callbacks table if it exists
    if table_exists:
        cursor.execute("""
            SELECT merchant_id, payout_callback_url
            FROM merchant_callbacks
            WHERE payout_callback_url IS NOT NULL AND payout_callback_url != ''
            AND is_active = TRUE
            LIMIT 5
        """)
        
        merchants_with_payout_callback = cursor.fetchall()
        
        if merchants_with_payout_callback:
            print(f"\n✅ Found {len(merchants_with_payout_callback)} merchants with payout_callback_url in 'merchant_callbacks' table:")
            for merchant in merchants_with_payout_callback:
                print(f"  - Merchant: {merchant[0]}")
                print(f"    Payout Callback URL: {merchant[1]}")
        else:
            print("\n⚠️ No merchants found with payout_callback_url in 'merchant_callbacks' table")
    
    # Check for PayTouchPayin transactions
    print("\n📋 Checking recent PayTouchPayin transactions...")
    cursor.execute("""
        SELECT pt.txn_id, pt.merchant_id, pt.status, m.callback_url
        FROM payin_transactions pt
        JOIN merchants m ON pt.merchant_id = m.merchant_id
        WHERE pt.pg_partner = 'paytouchpayin'
        ORDER BY pt.created_at DESC
        LIMIT 3
    """)
    
    recent_txns = cursor.fetchall()
    
    if recent_txns:
        print(f"\n✅ Found {len(recent_txns)} recent PayTouchPayin transactions:")
        for txn in recent_txns:
            print(f"\n  Transaction: {txn[0]}")
            print(f"    Merchant: {txn[1]}")
            print(f"    Status: {txn[2]}")
            print(f"    Callback URL: {txn[3] if txn[3] else 'NOT CONFIGURED'}")
    else:
        print("\n⚠️ No recent PayTouchPayin transactions found")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ CHECK COMPLETE")
    print("="*80)
    
    print("\n💡 Summary:")
    print("  For PAYIN callbacks:")
    print("    - Use 'merchants.callback_url' column")
    print("  For PAYOUT callbacks:")
    print("    - Use 'merchant_callbacks.payout_callback_url' column (if table exists)")
    print("    - Otherwise use 'merchants.callback_url' column")


if __name__ == "__main__":
    try:
        check_callback_config()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
