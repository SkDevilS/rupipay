"""
Set merchant callback URL for PayTouchPayin
"""

from database_pooled import get_db_connection

def set_callback_url(merchant_id, payin_url=None, payout_url=None):
    """Set callback URLs for a merchant"""
    
    print("\n" + "="*80)
    print("🔧 SETTING MERCHANT CALLBACK URL")
    print("="*80)
    print(f"Merchant ID: {merchant_id}")
    print(f"PAYIN URL: {payin_url or 'Not changing'}")
    print(f"PAYOUT URL: {payout_url or 'Not changing'}")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if merchant exists
    cursor.execute("SELECT merchant_id, full_name FROM merchants WHERE merchant_id = %s", (merchant_id,))
    merchant = cursor.fetchone()
    
    if not merchant:
        print(f"\n❌ Merchant {merchant_id} not found!")
        cursor.close()
        conn.close()
        return False
    
    print(f"\n✅ Found merchant: {merchant['full_name']}")
    
    # Check if entry exists in merchant_callbacks
    cursor.execute("SELECT * FROM merchant_callbacks WHERE merchant_id = %s", (merchant_id,))
    existing = cursor.fetchone()
    
    if existing:
        print(f"\n📋 Existing callback configuration:")
        print(f"  PAYIN URL: {existing['payin_callback_url']}")
        print(f"  PAYOUT URL: {existing['payout_callback_url']}")
        
        # Update existing entry
        if payin_url and payout_url:
            cursor.execute("""
                UPDATE merchant_callbacks
                SET payin_callback_url = %s, payout_callback_url = %s
                WHERE merchant_id = %s
            """, (payin_url, payout_url, merchant_id))
        elif payin_url:
            cursor.execute("""
                UPDATE merchant_callbacks
                SET payin_callback_url = %s
                WHERE merchant_id = %s
            """, (payin_url, merchant_id))
        elif payout_url:
            cursor.execute("""
                UPDATE merchant_callbacks
                SET payout_callback_url = %s
                WHERE merchant_id = %s
            """, (payout_url, merchant_id))
        
        conn.commit()
        print(f"\n✅ Updated callback URLs")
    else:
        print(f"\n📋 No existing callback configuration found")
        
        # Insert new entry
        cursor.execute("""
            INSERT INTO merchant_callbacks (merchant_id, payin_callback_url, payout_callback_url)
            VALUES (%s, %s, %s)
        """, (merchant_id, payin_url, payout_url))
        
        conn.commit()
        print(f"\n✅ Created new callback configuration")
    
    # Verify the change
    cursor.execute("SELECT * FROM merchant_callbacks WHERE merchant_id = %s", (merchant_id,))
    updated = cursor.fetchone()
    
    print(f"\n📋 New callback configuration:")
    print(f"  PAYIN URL: {updated['payin_callback_url']}")
    print(f"  PAYOUT URL: {updated['payout_callback_url']}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ CALLBACK URL SET SUCCESSFULLY")
    print("="*80)
    
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("\nUsage:")
        print("  python3 set_merchant_callback_url.py <merchant_id> <payin_url> [payout_url]")
        print("\nExample:")
        print("  python3 set_merchant_callback_url.py 7679022140 https://merchant.com/callback/payin")
        print("  python3 set_merchant_callback_url.py 7679022140 https://merchant.com/callback/payin https://merchant.com/callback/payout")
        sys.exit(1)
    
    merchant_id = sys.argv[1]
    payin_url = sys.argv[2] if len(sys.argv) > 2 else None
    payout_url = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        set_callback_url(merchant_id, payin_url, payout_url)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
