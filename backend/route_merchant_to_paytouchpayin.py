"""
Route a specific merchant to Paytouchpayin
Quick script to update merchant's payin_partner field
"""

import sys
sys.path.append('/var/www/moneyone/moneyone/backend')

from database_pooled import get_db_connection

def route_merchant_to_paytouchpayin(merchant_id):
    """Update merchant's payin_partner to Paytouchpayin"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Helper function to convert cursor results to dict
        def row_to_dict(cursor, row):
            if row is None:
                return None
            return dict(zip([col[0] for col in cursor.description], row))
        
        # Check if merchant exists
        cursor.execute("""
            SELECT merchant_id, name, payin_partner, status
            FROM merchants
            WHERE merchant_id = %s
        """, (merchant_id,))
        
        row = cursor.fetchone()
        merchant = row_to_dict(cursor, row)
        
        if not merchant:
            print(f"❌ Merchant {merchant_id} not found")
            cursor.close()
            conn.close()
            return False
        
        print(f"\n📋 Current Merchant Info:")
        print(f"  Merchant ID: {merchant['merchant_id']}")
        print(f"  Name: {merchant['name']}")
        print(f"  Status: {merchant['status']}")
        print(f"  Current Payin Partner: {merchant['payin_partner'] or 'NOT SET'}")
        
        # Update payin_partner
        cursor.execute("""
            UPDATE merchants
            SET payin_partner = 'Paytouchpayin'
            WHERE merchant_id = %s
        """, (merchant_id,))
        
        conn.commit()
        
        print(f"\n✅ Successfully routed merchant {merchant_id} to Paytouchpayin")
        
        # Verify update
        cursor.execute("""
            SELECT payin_partner
            FROM merchants
            WHERE merchant_id = %s
        """, (merchant_id,))
        
        row = cursor.fetchone()
        updated = row_to_dict(cursor, row)
        print(f"✓ Verified: Payin Partner = {updated['payin_partner']}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        merchant_id = sys.argv[1]
    else:
        print("Usage: python3 route_merchant_to_paytouchpayin.py <merchant_id>")
        print("\nExample:")
        print("  python3 backend/route_merchant_to_paytouchpayin.py 7679022140")
        sys.exit(1)
    
    print(f"Routing merchant {merchant_id} to Paytouchpayin...")
    route_merchant_to_paytouchpayin(merchant_id)
