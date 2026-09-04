import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import os

def generate_random_password(length=12):
    """Generate a random password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

def generate_authorization_key():
    """Generate authorization key (64 characters)"""
    return 'mk_live_' + secrets.token_hex(28)

def generate_module_secret():
    """Generate module secret key (32 characters)"""
    return 'sk_live_' + secrets.token_hex(12)

def generate_aes_iv():
    """Generate AES IV (16 characters)"""
    return secrets.token_urlsafe(12)[:16]

def generate_aes_key():
    """Generate AES encryption key (26 characters)"""
    return secrets.token_hex(13)

def encrypt_aes(data, key, iv):
    """Encrypt data using AES"""
    try:
        # Ensure key and IV are bytes
        key_bytes = key.encode('utf-8') if isinstance(key, str) else key
        iv_bytes = iv.encode('utf-8') if isinstance(iv, str) else iv
        
        # Pad key to 32 bytes (256 bits)
        key_bytes = key_bytes.ljust(32, b'\0')[:32]
        # Pad IV to 16 bytes
        iv_bytes = iv_bytes.ljust(16, b'\0')[:16]
        
        # Create cipher
        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad data
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data.encode('utf-8')) + padder.finalize()
        
        # Encrypt
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return base64 encoded
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        print(f"Encryption error: {e}")
        return None

def decrypt_aes(encrypted_data, key, iv):
    """Decrypt data using AES"""
    try:
        # Ensure key and IV are bytes
        key_bytes = key.encode('utf-8') if isinstance(key, str) else key
        iv_bytes = iv.encode('utf-8') if isinstance(iv, str) else iv
        
        # Pad key to 32 bytes (256 bits)
        key_bytes = key_bytes.ljust(32, b'\0')[:32]
        # Pad IV to 16 bytes
        iv_bytes = iv_bytes.ljust(16, b'\0')[:16]
        
        # Decode base64
        encrypted_bytes = base64.b64decode(encrypted_data)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes), backend=default_backend())
        decryptor = cipher.decryptor()
        
        # Decrypt
        decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()
        
        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def send_email(to_email, subject, body):
    """Send email using SMTP configuration from environment"""
    try:
        from config import Config
        
        # Email configuration from environment
        smtp_server = Config.SMTP_HOST
        smtp_port = Config.SMTP_PORT
        sender_email = Config.SMTP_FROM_EMAIL
        sender_password = Config.SMTP_PASSWORD
        sender_name = Config.SMTP_FROM_NAME
        use_tls = Config.SMTP_USE_TLS
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = to_email
        
        # Create HTML body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #4F46E5; margin: 0;">MoneyOne</h1>
                        <p style="color: #666; margin: 5px 0;">Payment Gateway Solutions</p>
                    </div>
                    {body}
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px;">
                        <p>This is an automated email. Please do not reply.</p>
                        <p>© 2026 MoneyOne. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Attach HTML body
        html_part = MIMEText(html_body, "html")
        message.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
            if Config.SMTP_USERNAME and Config.SMTP_PASSWORD:
                server.login(Config.SMTP_USERNAME, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

def send_merchant_credentials_email(merchant_name, email, merchant_id, password):
    """Send merchant credentials via email"""
    subject = "Welcome to Paysetu - Your Merchant Account Credentials"
    
    body = f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; color: white; margin-bottom: 20px;">
        <h2 style="margin: 0; color: white;">Welcome to Paysetu!</h2>
        <p style="margin: 10px 0 0 0; color: #f0f0f0;">Your merchant account has been successfully created</p>
    </div>
    
    <div style="padding: 20px; background: #f9fafb; border-radius: 10px; margin-bottom: 20px;">
        <p style="margin: 0 0 15px 0;">Dear <strong>{merchant_name}</strong>,</p>
        <p style="margin: 0 0 15px 0;">Your merchant account has been successfully created. Below are your login credentials:</p>
        
        <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #4F46E5;">
            <p style="margin: 0 0 10px 0;"><strong>Merchant ID:</strong> <span style="color: #4F46E5; font-family: monospace; font-size: 16px;">{merchant_id}</span></p>
            <p style="margin: 0;"><strong>Password:</strong> <span style="color: #4F46E5; font-family: monospace; font-size: 16px;">{password}</span></p>
        </div>
    </div>
    
    <div style="background: #FEF3C7; padding: 15px; border-radius: 8px; border-left: 4px solid #F59E0B; margin-bottom: 20px;">
        <p style="margin: 0; color: #92400E;"><strong>⚠️ Security Notice:</strong></p>
        <p style="margin: 10px 0 0 0; color: #92400E;">Please change your password after your first login. Keep your credentials secure and never share them with anyone.</p>
    </div>
    
    <div style="padding: 20px; background: #f9fafb; border-radius: 10px;">
        <h3 style="margin: 0 0 15px 0; color: #4F46E5;">Next Steps:</h3>
        <ol style="margin: 0; padding-left: 20px; color: #666;">
            <li style="margin-bottom: 10px;">Login to your merchant dashboard</li>
            <li style="margin-bottom: 10px;">Complete your profile setup</li>
            <li style="margin-bottom: 10px;">Configure your API credentials in Developer Zone</li>
            <li style="margin-bottom: 10px;">Review your commercial rates</li>
            <li>Start accepting payments!</li>
        </ol>
    </div>
    
    <div style="text-align: center; margin-top: 30px;">
        <a href="http://localhost:5173/login" style="display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">Login to Dashboard</a>
    </div>
    
    <p style="margin-top: 30px; color: #666;">If you have any questions or need assistance, please contact our support team.</p>
    """
    
    return send_email(email, subject, body)

def validate_api_credentials(authorization_key, module_secret, merchant_id):
    """
    Validate merchant API credentials
    Returns (is_valid, error_message, merchant_data)
    """
    from database import get_db_connection
    
    if not authorization_key or not module_secret:
        return False, 'Authorization key and module secret are required', None
    
    # Validate key format
    if not authorization_key.startswith('mk_live_'):
        return False, 'Invalid authorization key format', None
    
    if not module_secret.startswith('sk_live_'):
        return False, 'Invalid module secret format', None
    
    conn = get_db_connection()
    if not conn:
        return False, 'Database connection failed', None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT merchant_id, authorization_key, module_secret, is_active
                FROM merchants
                WHERE merchant_id = %s
            """, (merchant_id,))
            
            merchant = cursor.fetchone()
            
            if not merchant:
                return False, 'Invalid merchant credentials', None
            
            if not merchant['is_active']:
                return False, 'Merchant account is inactive', None
            
            # Verify credentials
            if merchant['authorization_key'] != authorization_key:
                return False, 'Invalid authorization key', None
            
            if merchant['module_secret'] != module_secret:
                return False, 'Invalid module secret', None
            
            return True, None, merchant
            
    except Exception as e:
        print(f"API credentials validation error: {e}")
        return False, 'Internal server error', None
    finally:
        conn.close()

