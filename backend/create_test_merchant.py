"""
Script to create a test merchant for development
"""
import bcrypt
import secrets
from database import get_db_connection

def generate_credentials():
    """Generate API credentials"""
    return {
        'authorization_key': secrets.token_urlsafe(32),
        'module_secret': secrets.token_urlsafe(32),
        'aes_iv': secrets.token_hex(16),
        'aes_key': secrets.token_hex(32)
    }

def create_test_merchant():
    """Create a test merchant"""
    try:
        conn = get_db_connection()
        if not conn:
            print("Database connection failed")
            return False
        
        with conn.cursor() as cursor:
            # Check if test merchant exists
            cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = 'TEST001'")
            if cursor.fetchone():
                print("Test merchant already exists!")
                return True
            
            # Check if default admin exists
            cursor.execute("SELECT admin_id FROM admin_users WHERE admin_id = '6239572985'")
            if not cursor.fetchone():
                print("Default admin not found. Please run app.py first to create admin.")
                return False
            
            # Check if a scheme exists
            cursor.execute("SELECT id FROM commercial_schemes LIMIT 1")
            scheme = cursor.fetchone()
            if not scheme:
                # Create a default scheme
                cursor.execute("""
                    INSERT INTO commercial_schemes (scheme_name, created_by)
                    VALUES ('DEFAULT_SCHEME', '6239572985')
                """)
                conn.commit()
                scheme_id = cursor.lastrowid
                print(f"Created default scheme with ID: {scheme_id}")
            else:
                scheme_id = scheme['id']
                print(f"Using existing scheme ID: {scheme_id}")
            
            # Generate credentials
            creds = generate_credentials()
            
            # Hash password
            password_hash = bcrypt.hashpw('merchant@123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Create merchant
            cursor.execute("""
                INSERT INTO merchants (
                    merchant_id, password_hash, full_name, email, mobile,
                    aadhar_card, pan_no, pincode, state, city, address,
                    merchant_type, account_number, ifsc_code, gst_no,
                    scheme_id, authorization_key, module_secret, aes_iv, aes_key,
                    created_by
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s
                )
            """, (
                'TEST001', password_hash, 'Test Merchant', 'test@merchant.com', '9876543210',
                '123456789012', 'ABCDE1234F', '400001', 'Maharashtra', 'Mumbai', 'Test Address',
                'BOTH', '1234567890', 'SBIN0001234', '27ABCDE1234F1Z5',
                scheme_id, creds['authorization_key'], creds['module_secret'], 
                creds['aes_iv'], creds['aes_key'],
                '6239572985'
            ))
            conn.commit()
            
            print("\n" + "="*60)
            print("Test Merchant Created Successfully!")
            print("="*60)
            print(f"Merchant ID: TEST001")
            print(f"Password: merchant@123")
            print(f"Email: test@merchant.com")
            print(f"Mobile: 9876543210")
            print(f"\nAPI Credentials:")
            print(f"Authorization Key: {creds['authorization_key']}")
            print(f"Module Secret: {creds['module_secret']}")
            print(f"AES IV: {creds['aes_iv']}")
            print(f"AES Key: {creds['aes_key']}")
            print("="*60 + "\n")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error creating test merchant: {e}")
        return False

if __name__ == '__main__':
    create_test_merchant()
