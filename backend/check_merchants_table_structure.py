"""
Check merchants table structure to find where callback URL is stored
"""

from database_pooled import get_db_connection

def check_merchants_table():
    """Check merchants table structure"""
    
    print("\n" + "="*80)
    print("🔍 CHECKING MERCHANTS TABLE STRUCTURE")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get table structure
    print("\n📋 Merchants table columns:")
    cursor.execute("DESCRIBE merchants")
    columns = cursor.fetchall()
    
    for col in columns:
        print(f"  - {col['Field']}: {col['Type']}")
    
    # Check merchant_callbacks table
    print("\n📋 Merchant_callbacks table columns:")
    cursor.execute("DESCRIBE merchant_callbacks")
    callback_columns = cursor.fetchall()
    
    for col in callback_columns:
        print(f"  - {col['Field']}: {col['Type']}")
    
    # Check if merchant 7679022140 has callback URL configured
    print("\n📋 Checking merchant 7679022140 callback configuration:")
    
    cursor.execute("""
        SELECT payin_callback_url, payout_callback_url
        FROM merchant_callbacks
        WHERE merchant_id = '7679022140'
    """)
    
    callback_config = cursor.fetchone()
    
    if callback_config:
        print(f"  ✅ Found in merchant_callbacks table:")
        print(f"     PAYIN callback URL: {callback_config['payin_callback_url']}")
        print(f"     PAYOUT callback URL: {callback_config['payout_callback_url']}")
    else:
        print(f"  ❌ No callback configuration found in merchant_callbacks table")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ CHECK COMPLETE")
    print("="*80)
    
    print("\n💡 CONCLUSION:")
    print("  PAYIN callback URLs are stored in: merchant_callbacks.payin_callback_url")
    print("  PAYOUT callback URLs are stored in: merchant_callbacks.payout_callback_url")
    print("  NOT in merchants.callback_url (that column doesn't exist)")


if __name__ == "__main__":
    try:
        check_merchants_table()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
