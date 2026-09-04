"""
Setup SkrillPe Service Routing
Adds SkrillPe as a PG partner option in the database
"""

from database import get_db_connection

def setup_skrillpe_routing():
    """Add SkrillPe to pg_partners table"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Check if SkrillPe already exists
            cursor.execute("""
                SELECT COUNT(*) as count FROM pg_partners WHERE partner_name = 'SkrillPe'
            """)
            
            exists = cursor.fetchone()['count'] > 0
            
            if exists:
                print("✓ SkrillPe already exists in pg_partners")
            else:
                # Insert SkrillPe
                cursor.execute("""
                    INSERT INTO pg_partners (partner_name, service_type, is_active, created_at)
                    VALUES ('SkrillPe', 'PAYIN', TRUE, NOW())
                """)
                conn.commit()
                print("✓ Added SkrillPe to pg_partners table")
            
            # Show current PG partners
            cursor.execute("""
                SELECT partner_name, service_type, is_active 
                FROM pg_partners 
                ORDER BY partner_name
            """)
            
            partners = cursor.fetchall()
            print("\n📋 Current PG Partners:")
            print("-" * 50)
            for partner in partners:
                status = "✓ Active" if partner['is_active'] else "✗ Inactive"
                print(f"{partner['partner_name']:15} | {partner['service_type']:10} | {status}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("=" * 50)
    print("Setting up SkrillPe Service Routing")
    print("=" * 50)
    setup_skrillpe_routing()
    print("\n✓ Setup complete!")
    print("\nNext steps:")
    print("1. Go to Admin Dashboard > Service Routing")
    print("2. Create a new routing rule for SkrillPe")
    print("3. Select 'SkrillPe' as the PG Partner")
    print("4. Choose routing type (ALL_USERS or SINGLE_USER)")
    print("5. Set priority and activate the routing")
