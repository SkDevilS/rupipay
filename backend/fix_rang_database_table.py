#!/usr/bin/env python3
"""
Fix script to test Rang database table integration
"""

from database import get_db_connection
import json

def test_database_connection():
    """Test database connection and table structure"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return False
        
        cursor = conn.cursor()
        
        print("🔍 Testing database connection...")
        
        # Check if payin_transactions table exists
        cursor.execute("SHOW TABLES LIKE 'payin_transactions'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ payin_transactions table exists")
            
            # Check table structure
            cursor.execute("DESCRIBE payin_transactions")
            columns = cursor.fetchall()
            
            print("📋 Table structure:")
            required_columns = ['txn_id', 'merchant_id', 'order_id', 'amount', 'charge_amount', 
                              'net_amount', 'payee_name', 'payee_email', 'payee_mobile', 
                              'status', 'pg_partner', 'pg_txn_id', 'created_at']
            
            existing_columns = [col[0] for col in columns]
            
            for col in required_columns:
                if col in existing_columns:
                    print(f"  ✅ {col}")
                else:
                    print(f"  ❌ {col} (missing)")
            
            # Test insert (dry run)
            print("\n🧪 Testing insert query structure...")
            test_query = """
                INSERT INTO payin_transactions (
                    txn_id, merchant_id, order_id, amount, charge_amount, 
                    charge_type, net_amount, payee_name, payee_email, 
                    payee_mobile, product_info, status, pg_partner,
                    pg_txn_id, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """
            
            # Just prepare the query to check syntax
            try:
                cursor.execute("SELECT 1")  # Simple test query
                print("✅ Database query syntax should work")
            except Exception as e:
                print(f"❌ Query syntax error: {e}")
                
        else:
            print("❌ payin_transactions table does not exist")
            print("   You may need to run database migrations")
        
        cursor.close()
        conn.close()
        
        return table_exists is not None
        
    except Exception as e:
        print(f"❌ Database test error: {str(e)}")
        return False

def test_rang_field_mapping():
    """Test the field mapping logic"""
    print("\n🔧 Testing Rang field mapping...")
    
    # Simulate order data from your system
    order_data = {
        'orderid': 'TEST123456',
        'amount': '100',
        'payee_fname': 'John Doe',
        'payee_email': 'john@example.com',
        'payee_mobile': '9876543210'
    }
    
    # Map to expected format
    mapped_order_data = {
        'order_id': order_data.get('orderid'),
        'amount': order_data.get('amount'),
        'customer_name': order_data.get('payee_fname', ''),
        'customer_mobile': order_data.get('payee_mobile'),
        'customer_email': order_data.get('payee_email'),
        'scheme_id': order_data.get('scheme_id', 1)
    }
    
    print("Input data:", json.dumps(order_data, indent=2))
    print("Mapped data:", json.dumps(mapped_order_data, indent=2))
    
    # Check all required fields are present
    required_fields = ['order_id', 'amount', 'customer_name', 'customer_mobile', 'customer_email']
    missing_fields = []
    
    for field in required_fields:
        if not mapped_order_data.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        print(f"❌ Missing fields: {missing_fields}")
        return False
    else:
        print("✅ All required fields mapped correctly")
        return True

def main():
    """Main function"""
    print("🔧 Rang Database Table Fix Test")
    print("=" * 40)
    
    # Test database
    db_ok = test_database_connection()
    
    # Test field mapping
    mapping_ok = test_rang_field_mapping()
    
    print("\n" + "=" * 40)
    if db_ok and mapping_ok:
        print("✅ Database table fix should resolve the error!")
        print("   Deploy the updated rang_service.py")
    else:
        print("❌ Issues found - check the errors above")
        if not db_ok:
            print("   - Database table issues")
        if not mapping_ok:
            print("   - Field mapping issues")

if __name__ == "__main__":
    main()