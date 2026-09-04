"""
Check if display_name column exists in service_routing table
If not, add it and populate with default values
"""

import pymysql
from database import get_db_connection

def check_and_add_display_name():
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if display_name column exists
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'service_routing' 
                AND COLUMN_NAME = 'display_name'
            """)
            
            column_exists = cursor.fetchone()
            
            if not column_exists:
                print("⚠️  display_name column does not exist. Adding it now...")
                
                # Add display_name column
                cursor.execute("""
                    ALTER TABLE service_routing 
                    ADD COLUMN display_name VARCHAR(100) NULL AFTER pg_partner
                """)
                conn.commit()
                print("✅ display_name column added successfully")
                
                # Populate with default values
                print("📝 Populating display_name with default values...")
                
                updates = [
                    ("PayU", "SERVER DOWN"),
                    ("Paytouch2", "Paytouch2_Grosmart"),
                    ("Airpay", "Airpay_Grosmart"),
                    ("Paytouchpayin", "Paytouchpayin_Grosmart"),
                    ("Rang", "Rang"),
                    ("VIYONAPAY", "Viyonapay_Truaxis"),
                    ("VIYONAPAY_BARRINGER", "Viyonapay_Barringer"),
                    ("Mudrape", "Mudrape"),
                    ("Tourquest", "Tourquest"),
                    ("Vega", "Vega"),
                    ("Skrillpe", "SkrillPe")
                ]
                
                for pg_partner, display_name in updates:
                    cursor.execute("""
                        UPDATE service_routing 
                        SET display_name = %s 
                        WHERE pg_partner = %s
                    """, (display_name, pg_partner))
                
                conn.commit()
                print(f"✅ Updated {len(updates)} API display names")
                
            else:
                print("✅ display_name column already exists")
                
                # Check if any display_name is NULL
                cursor.execute("""
                    SELECT COUNT(*) as null_count
                    FROM service_routing 
                    WHERE display_name IS NULL
                """)
                result = cursor.fetchone()
                
                if result['null_count'] > 0:
                    print(f"⚠️  Found {result['null_count']} rows with NULL display_name")
                    print("📝 Updating NULL values...")
                    
                    # Update NULL values to match pg_partner
                    cursor.execute("""
                        UPDATE service_routing 
                        SET display_name = pg_partner 
                        WHERE display_name IS NULL
                    """)
                    conn.commit()
                    print("✅ Updated NULL display_name values")
            
            # Show current state
            print("\n📊 Current service_routing APIs:")
            cursor.execute("""
                SELECT DISTINCT pg_partner, display_name, service_type
                FROM service_routing
                ORDER BY service_type, pg_partner
            """)
            
            apis = cursor.fetchall()
            current_service = None
            for api in apis:
                if api['service_type'] != current_service:
                    current_service = api['service_type']
                    print(f"\n{current_service}:")
                print(f"  • {api['pg_partner']} → {api['display_name']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Service Routing Display Name Setup")
    print("=" * 60)
    print()
    
    success = check_and_add_display_name()
    
    print()
    print("=" * 60)
    if success:
        print("✅ Setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Restart backend: pkill -f 'python.*app.py' && cd backend && nohup python app.py &")
        print("2. Test API: curl http://localhost:5000/api/api-ledger/apis?service_type=PAYIN")
    else:
        print("❌ Setup failed. Please check the errors above.")
    print("=" * 60)
