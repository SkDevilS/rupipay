"""
Check if merchant is routed to Paytouchpayin
"""

import sys
sys.path.append('/var/www/moneyone/moneyone/backend')

from database_pooled import get_db_connection

def check_merchant_routing(merchant_id):
    """Check merchant's payin routing"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Helper function to convert cursor results to dict
        def row_to_dict(cursor, row):
            if row is None:
                return None
            return dict(zip([col[0] for col in cursor.description], row))
        
        cursor.execute("""
            SELECT merchant_id, name, payin_partner, payout_partner, status
            FROM merchants
            WHERE merchant_id = %s
        """, (merchant_id,))
        
        row = cursor.fetchone()
        merchant = row_to_dict(cursor, row)
        cursor.close()
        conn.close()
        
        if not merchant:
            print(f"❌ Merchant {merchant_id} not found")
            return False
        
        print(f"\n✅ Merchant Found:")
        print(f"  Merchant ID: {merchant['merchant_id']}")
        print(f"  Name: {merchant['name']}")
        print(f"  Status: {merchant['status']}")
        print(f"  Payin Partner: {merchant['payin_partner'] or 'NOT SET'}")
        print(f"  Payout Partner: {merchant['payout_partner'] or 'NOT SET'}")
        
        if merchant['payin_partner'] and merchant['payin_partner'].upper() == 'PAYTOUCHPAYIN':
            print(f"\n✅ Merchant is routed to PAYTOUCHPAYIN")
            return True
        else:
            print(f"\n⚠️  Merchant is NOT routed to PAYTOUCHPAYIN")
            print(f"\n💡 To route this merchant to Paytouchpayin:")
            print(f"   python3 backend/setup_paytouchpayin_routing.py {merchant_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        merchant_id = sys.argv[1]
    else:
        merchant_id = "7679022140"  # Default test merchant
    
    print(f"Checking routing for merchant: {merchant_id}")
    check_merchant_routing(merchant_id)
