"""
Setup script to configure Sabpaisa Grosmart routing for merchants
"""

from database import get_db_connection


def setup_sabpaisa_grosmart_routing(merchant_id=None):
    """
    Configure Sabpaisa Grosmart as payin gateway for merchant(s)
    
    Args:
        merchant_id: Specific merchant ID, or None for ALL_USERS routing
    """
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            if merchant_id:
                # Check if merchant exists
                cursor.execute("SELECT merchant_id, full_name FROM merchants WHERE merchant_id = %s", (merchant_id,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    print(f"❌ Merchant not found: {merchant_id}")
                    return False
                
                print(f"📝 Setting up Sabpaisa Grosmart routing for merchant: {merchant['full_name']} ({merchant_id})")
                
                # Check if routing already exists
                cursor.execute("""
                    SELECT id FROM service_routing
                    WHERE merchant_id = %s AND service_type = 'PAYIN' AND routing_type = 'SINGLE_USER'
                """, (merchant_id,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing routing
                    cursor.execute("""
                        UPDATE service_routing
                        SET pg_partner = 'SABPAISA_GROSMART',
                            is_active = TRUE,
                            priority = 1,
                            updated_at = NOW()
                        WHERE merchant_id = %s AND service_type = 'PAYIN' AND routing_type = 'SINGLE_USER'
                    """, (merchant_id,))
                    print(f"✅ Updated existing routing to Sabpaisa Grosmart")
                else:
                    # Insert new routing
                    cursor.execute("""
                        INSERT INTO service_routing (
                            merchant_id, service_type, routing_type, pg_partner,
                            is_active, priority, created_at, updated_at
                        ) VALUES (
                            %s, 'PAYIN', 'SINGLE_USER', 'SABPAISA_GROSMART',
                            TRUE, 1, NOW(), NOW()
                        )
                    """, (merchant_id,))
                    print(f"✅ Created new routing to Sabpaisa Grosmart")
            else:
                # Setup ALL_USERS routing
                print(f"📝 Setting up Sabpaisa Grosmart routing for ALL USERS")
                
                # Check if ALL_USERS routing exists
                cursor.execute("""
                    SELECT id FROM service_routing
                    WHERE merchant_id IS NULL AND service_type = 'PAYIN' AND routing_type = 'ALL_USERS'
                """)
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing routing
                    cursor.execute("""
                        UPDATE service_routing
                        SET pg_partner = 'SABPAISA_GROSMART',
                            is_active = TRUE,
                            priority = 1,
                            updated_at = NOW()
                        WHERE merchant_id IS NULL AND service_type = 'PAYIN' AND routing_type = 'ALL_USERS'
                    """)
                    print(f"✅ Updated ALL_USERS routing to Sabpaisa Grosmart")
                else:
                    # Insert new routing
                    cursor.execute("""
                        INSERT INTO service_routing (
                            merchant_id, service_type, routing_type, pg_partner,
                            is_active, priority, created_at, updated_at
                        ) VALUES (
                            NULL, 'PAYIN', 'ALL_USERS', 'SABPAISA_GROSMART',
                            TRUE, 1, NOW(), NOW()
                        )
                    """)
                    print(f"✅ Created ALL_USERS routing to Sabpaisa Grosmart")
            
            conn.commit()
            print(f"✅ Sabpaisa Grosmart routing configured successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error setting up routing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        merchant_id = sys.argv[1]
        print(f"Setting up Sabpaisa Grosmart for merchant: {merchant_id}")
        setup_sabpaisa_grosmart_routing(merchant_id)
    else:
        print("Usage:")
        print("  python setup_sabpaisa_grosmart_routing.py <merchant_id>  # For specific merchant")
        print("  python setup_sabpaisa_grosmart_routing.py ALL            # For all users")
        print()
        choice = input("Setup for ALL users? (y/n): ")
        if choice.lower() == 'y':
            setup_sabpaisa_grosmart_routing(None)
        else:
            merchant_id = input("Enter merchant ID: ")
            setup_sabpaisa_grosmart_routing(merchant_id)
