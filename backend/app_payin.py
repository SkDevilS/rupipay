from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt
from datetime import datetime, timedelta
import pytz
from config import Config
from database_pooled import get_db_connection, init_database
from captcha_generator import CaptchaGenerator
from utils import (
    generate_random_password, generate_authorization_key, generate_module_secret,
    generate_aes_iv, generate_aes_key, send_merchant_credentials_email,
    encrypt_aes, decrypt_aes
)
import secrets
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
app.config['UPLOAD_FOLDER'] = Config.UPLOADS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_UPLOAD_SIZE

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure CORS - Simple and clean configuration
# Flask-CORS will automatically handle preflight requests
CORS(app, 
     origins=Config.CORS_ORIGINS,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     expose_headers=["Content-Type", "Authorization"],
     supports_credentials=Config.CORS_ALLOW_CREDENTIALS,
     max_age=3600)

jwt = JWTManager(app)

# Register blueprints
from payin_routes import payin_bp
from mudrape_routes import mudrape_bp
from mudrape_payout_routes import mudrape_payout_bp
from mudrape_callback_routes import mudrape_callback_bp
from airpay_routes import airpay_bp
from airpay_callback_routes import airpay_callback_bp
from airpay_truaxis_callback_routes import airpay_truaxis_callback_bp
from airpay_coco_callback_routes import airpay_coco_callback_bp
from paytouchpayin_routes import paytouchpayin_bp
from paytouchpayin_callback_routes import paytouchpayin_callback_bp
from paytouch_callback_routes import paytouch_callback_bp
from paytouch2_callback_routes import paytouch2_callback_bp
from tourquest_routes import tourquest_bp
from tourquest_callback_routes import tourquest_callback_bp
from skrillpe_routes import skrillpe_bp
from skrillpe_callback_routes import skrillpe_callback_bp
from rang_routes import rang_bp
from rang_callback_routes import rang_callback_bp
from viyonapay_routes import viyonapay_bp
from viyonapay_callback_routes import viyonapay_callback_bp
from upilnk_coco_callback_routes import upilnk_coco_callback_bp
from payplus_veltrix_callback_routes import payplus_veltrix_callback_bp
from service_routing_routes import routing_bp
from payout_routes import payout_bp
from payu_webhook_routes import payu_webhook_bp
from wallet_routes import wallet_bp
from ip_security_routes import ip_security_bp
from reconciliation_routes import reconciliation_bp

# PAYIN + PAYOUT SERVER CONFIGURATION
# This file is configured to run BOTH payin and payout routes
print("=== Starting MoneyOne PAYIN + PAYOUT API ===")
print("Service Type: PAYIN + PAYOUT")
print("Registering PAYIN and PAYOUT routes...")

# Payin main route
app.register_blueprint(payin_bp)

# Payin service routes
app.register_blueprint(mudrape_bp)
app.register_blueprint(airpay_bp)
app.register_blueprint(paytouchpayin_bp)
app.register_blueprint(tourquest_bp)
app.register_blueprint(skrillpe_bp)
app.register_blueprint(rang_bp)
app.register_blueprint(viyonapay_bp)

# Payin callback routes
app.register_blueprint(mudrape_callback_bp)
app.register_blueprint(airpay_callback_bp)
app.register_blueprint(airpay_truaxis_callback_bp)
app.register_blueprint(airpay_coco_callback_bp)
app.register_blueprint(paytouchpayin_callback_bp)
app.register_blueprint(tourquest_callback_bp)
app.register_blueprint(skrillpe_callback_bp)
app.register_blueprint(rang_callback_bp)
app.register_blueprint(viyonapay_callback_bp)
app.register_blueprint(upilnk_coco_callback_bp)

# Payout routes
app.register_blueprint(payout_bp)
app.register_blueprint(mudrape_payout_bp)
app.register_blueprint(payplus_veltrix_callback_bp)
app.register_blueprint(paytouch_callback_bp)
app.register_blueprint(paytouch2_callback_bp)
app.register_blueprint(payu_webhook_bp)

# Common routes (needed by all services)
app.register_blueprint(routing_bp)
app.register_blueprint(wallet_bp)
app.register_blueprint(ip_security_bp)
app.register_blueprint(reconciliation_bp)

print("=== PAYIN + PAYOUT Routes Registered Successfully ===")
print("All payin and payout routes are now active on this server")
print("="*50)

# Store captcha sessions (in production, use Redis or database)
captcha_sessions = {}

# Initialize captcha generator
captcha_gen = CaptchaGenerator()

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Request/Response logging middleware
@app.before_request
def log_request_info():
    """Log incoming request details"""
    ip = get_real_ip()
    print(f"INFO:app:→ {request.method} {request.path} | IP: {ip} | User-Agent: {request.headers.get('User-Agent', 'N/A')}")
    if request.method in ['POST', 'PUT', 'PATCH'] and request.is_json:
        # Log request body (be careful with sensitive data)
        body = request.get_json()
        # Mask sensitive fields
        if body:
            safe_body = {k: '***' if k in ['password', 'pin', 'tpin', 'secret', 'key'] else v for k, v in body.items()}
            print(f"INFO:app:→ Request Body: {safe_body}")

@app.after_request
def log_response_info(response):
    """Log outgoing response details"""
    ip = get_real_ip()
    print(f"INFO:app:← {request.method} {request.path} | Status: {response.status_code} | IP: {ip}")
    return response

def allowed_file(filename):
    """Check if file extension is allowed based on config"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def convert_to_ist(utc_datetime):
    """Convert UTC datetime to IST"""
    if utc_datetime is None:
        return None
    if isinstance(utc_datetime, str):
        utc_datetime = datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S')
    # Assume the datetime from DB is UTC
    utc_datetime = pytz.utc.localize(utc_datetime)
    ist_datetime = utc_datetime.astimezone(IST)
    return ist_datetime.strftime('%d-%m-%Y %I:%M:%S %p')

def format_datetime_ist(dt):
    """Format datetime to IST string - DB now stores in IST timezone"""
    if dt is None:
        return None
    
    # Handle string datetime
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except:
            return str(dt)
    elif not isinstance(dt, datetime):
        return str(dt)
    
    # Format the datetime (it's already in IST from DB)
    return dt.strftime('%d-%m-%Y %I:%M:%S %p')

def get_real_ip():
    """Get the real IP address from request, handling proxies and load balancers"""
    # Debug: Log all relevant headers
    xff = request.headers.get('X-Forwarded-For')
    xri = request.headers.get('X-Real-IP')
    cfip = request.headers.get('CF-Connecting-IP')
    remote = request.remote_addr
    
    # Check X-Forwarded-For header (used by most proxies and load balancers)
    if xff:
        # X-Forwarded-For can contain multiple IPs, the first one is the real client IP
        # Format: client, proxy1, proxy2
        ip = xff.split(',')[0].strip()
        print(f"DEBUG: Using X-Forwarded-For: {ip} (full: {xff})")
        return ip
    
    # Check X-Real-IP header (used by Nginx)
    if xri:
        print(f"DEBUG: Using X-Real-IP: {xri}")
        return xri.strip()
    
    # Check CF-Connecting-IP (used by Cloudflare)
    if cfip:
        print(f"DEBUG: Using CF-Connecting-IP: {cfip}")
        return cfip.strip()
    
    # Fallback to remote_addr (this will be ALB IP if behind load balancer)
    print(f"DEBUG: No forwarding headers found, using remote_addr: {remote}")
    print(f"DEBUG: Available headers: XFF={xff}, XRI={xri}, CFIP={cfip}")
    return remote

def log_activity(admin_id, action, status, ip_address=None, user_agent=None):
    """Log admin activity"""
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO admin_activity_logs (admin_id, action, status, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s)
                """, (admin_id, action, status, ip_address, user_agent))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Activity log error: {e}")

@app.route('/api/admin/captcha', methods=['GET'])
def get_captcha():
    """Generate and return captcha"""
    try:
        # Generate captcha text
        captcha_text = captcha_gen.generate_captcha_text()
        
        # Create session ID
        session_id = secrets.token_urlsafe(32)
        
        # Store captcha (expires in 5 minutes)
        captcha_sessions[session_id] = {
            'text': captcha_text,
            'expires': datetime.now() + timedelta(minutes=5)
        }
        
        # Generate captcha image
        captcha_image = captcha_gen.get_captcha_base64(captcha_text)
        
        return jsonify({
            'success': True,
            'sessionId': session_id,
            'captchaImage': captcha_image
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """Serve uploaded files"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        return jsonify({'success': False, 'message': 'File not found'}), 404

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login with JWT (captcha validation removed for multi-instance support)"""
    try:
        data = request.get_json()
        admin_id = data.get('adminId')
        password = data.get('password')
        # Accept but ignore captcha fields for backward compatibility
        # captcha_text = data.get('captcha')  # Ignored
        # session_id = data.get('sessionId')  # Ignored
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        # Validate input - only check adminId and password
        if not admin_id or not password:
            log_activity(admin_id or 'unknown', 'login_attempt', 'failed', ip_address, user_agent)
            return jsonify({'success': False, 'message': 'Admin ID and password are required'}), 400
        
        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check if account is locked
                cursor.execute("""
                    SELECT * FROM admin_users 
                    WHERE admin_id = %s
                """, (admin_id,))
                admin = cursor.fetchone()
                
                if not admin:
                    log_activity(admin_id, 'login_attempt', 'failed', ip_address, user_agent)
                    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
                
                # Check if account is locked
                if admin['locked_until'] and datetime.now() < admin['locked_until']:
                    log_activity(admin_id, 'login_attempt', 'locked', ip_address, user_agent)
                    return jsonify({'success': False, 'message': 'Account is temporarily locked. Try again later.'}), 403
                
                # Check if account is active
                if not admin['is_active']:
                    log_activity(admin_id, 'login_attempt', 'inactive', ip_address, user_agent)
                    return jsonify({'success': False, 'message': 'Account is inactive'}), 403
                
                # Verify password
                if not bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
                    # Increment login attempts
                    new_attempts = admin['login_attempts'] + 1
                    locked_until = None
                    
                    # Lock account after 5 failed attempts for 15 minutes
                    if new_attempts >= 5:
                        locked_until = datetime.now() + timedelta(minutes=15)
                    
                    cursor.execute("""
                        UPDATE admin_users 
                        SET login_attempts = %s, locked_until = %s
                        WHERE admin_id = %s
                    """, (new_attempts, locked_until, admin_id))
                    conn.commit()
                    
                    log_activity(admin_id, 'login_attempt', 'failed', ip_address, user_agent)
                    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
                
                # Reset login attempts and update last login
                cursor.execute("""
                    UPDATE admin_users 
                    SET login_attempts = 0, locked_until = NULL, last_login = NOW()
                    WHERE admin_id = %s
                """, (admin_id,))
                conn.commit()
                
                # Create JWT token
                access_token = create_access_token(identity=admin_id)
                
                log_activity(admin_id, 'login', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'token': access_token,
                    'adminId': admin_id
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token and refresh session"""
    try:
        current_admin = get_jwt_identity()
        
        # Generate new token to refresh session
        new_token = create_access_token(identity=current_admin)
        
        return jsonify({
            'success': True,
            'adminId': current_admin,
            'token': new_token,
            'message': 'Token verified and refreshed'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': 'Invalid token'}), 401

@app.route('/api/admin/logout', methods=['POST'])
@jwt_required()
def admin_logout():
    """Admin logout"""
    try:
        current_admin = get_jwt_identity()
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        log_activity(current_admin, 'logout', 'success', ip_address, user_agent)
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/activity-logs', methods=['GET'])
@jwt_required()
def get_activity_logs():
    """Get admin activity logs with pagination and filters"""
    try:
        current_admin = get_jwt_identity()
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        from_date = request.args.get('from_date', '', type=str)
        to_date = request.args.get('to_date', '', type=str)
        status = request.args.get('status', '', type=str)
        action = request.args.get('action', '', type=str)
        
        # Validate pagination
        if per_page > 100:
            per_page = 100
        if page < 1:
            page = 1
            
        offset = (page - 1) * per_page
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Build query with filters
                query = "SELECT * FROM admin_activity_logs WHERE admin_id = %s"
                params = [current_admin]
                
                # Add search filter
                if search:
                    query += " AND (action LIKE %s OR ip_address LIKE %s OR status LIKE %s)"
                    search_param = f"%{search}%"
                    params.extend([search_param, search_param, search_param])
                
                # Add date filters
                if from_date:
                    query += " AND DATE(created_at) >= %s"
                    params.append(from_date)
                
                if to_date:
                    query += " AND DATE(created_at) <= %s"
                    params.append(to_date)
                
                # Add status filter
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                # Add action filter
                if action:
                    query += " AND action = %s"
                    params.append(action)
                
                # Get total count
                count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
                cursor.execute(count_query, params)
                total_records = cursor.fetchone()['total']
                
                # Add ordering and pagination
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([per_page, offset])
                
                cursor.execute(query, params)
                logs = cursor.fetchall()
                
                # Convert timestamps to IST
                ist = pytz.timezone('Asia/Kolkata')
                for log in logs:
                    if log.get('created_at'):
                        # Ensure the datetime is timezone-aware
                        dt = log['created_at']
                        if dt.tzinfo is None:
                            # Assume UTC if no timezone info
                            dt = pytz.utc.localize(dt)
                        # Convert to IST and format as string with IST timezone
                        ist_time = dt.astimezone(ist)
                        log['created_at'] = ist_time.strftime('%Y-%m-%d %H:%M:%S')
                        log['timezone'] = 'IST'
                
                # Calculate pagination info
                total_pages = (total_records + per_page - 1) // per_page
                
                return jsonify({
                    'success': True,
                    'logs': logs,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total_records': total_records,
                        'total_pages': total_pages,
                        'has_next': page < total_pages,
                        'has_prev': page > 1
                    }
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/activity-logs/download', methods=['GET'])
@jwt_required()
def download_activity_logs():
    """Download filtered activity logs as CSV"""
    try:
        current_admin = get_jwt_identity()
        
        # Get query parameters (same as get_activity_logs)
        search = request.args.get('search', '', type=str)
        from_date = request.args.get('from_date', '', type=str)
        to_date = request.args.get('to_date', '', type=str)
        status = request.args.get('status', '', type=str)
        action = request.args.get('action', '', type=str)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Build query with filters (no pagination for download)
                query = "SELECT * FROM admin_activity_logs WHERE admin_id = %s"
                params = [current_admin]
                
                # Add search filter
                if search:
                    query += " AND (action LIKE %s OR ip_address LIKE %s OR status LIKE %s)"
                    search_param = f"%{search}%"
                    params.extend([search_param, search_param, search_param])
                
                # Add date filters
                if from_date:
                    query += " AND DATE(created_at) >= %s"
                    params.append(from_date)
                
                if to_date:
                    query += " AND DATE(created_at) <= %s"
                    params.append(to_date)
                
                # Add status filter
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                # Add action filter
                if action:
                    query += " AND action = %s"
                    params.append(action)
                
                # Add ordering
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                logs = cursor.fetchall()
                
                # Convert timestamps to IST
                ist = pytz.timezone('Asia/Kolkata')
                for log in logs:
                    if log.get('created_at'):
                        dt = log['created_at']
                        if dt.tzinfo is None:
                            dt = pytz.utc.localize(dt)
                        ist_time = dt.astimezone(ist)
                        log['created_at'] = ist_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Create CSV
                import io
                import csv
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow(['ID', 'Admin ID', 'Action', 'Status', 'IP Address', 'User Agent', 'Date & Time (IST)'])
                
                # Write data
                for log in logs:
                    writer.writerow([
                        log.get('id', ''),
                        log.get('admin_id', ''),
                        log.get('action', ''),
                        log.get('status', ''),
                        log.get('ip_address', ''),
                        log.get('user_agent', ''),
                        log.get('created_at', '')
                    ])
                
                # Prepare response
                output.seek(0)
                from flask import make_response
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = f'attachment; filename=activity_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                
                return response
                
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change admin password"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        confirm_password = data.get('confirmPassword')
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        # Validate input
        if not all([current_password, new_password, confirm_password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Check if new passwords match
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'New passwords do not match'}), 400
        
        # Validate password strength
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters long'}), 400
        
        if not any(c.isupper() for c in new_password):
            return jsonify({'success': False, 'message': 'Password must contain at least one uppercase letter'}), 400
        
        if not any(c.islower() for c in new_password):
            return jsonify({'success': False, 'message': 'Password must contain at least one lowercase letter'}), 400
        
        if not any(c.isdigit() for c in new_password):
            return jsonify({'success': False, 'message': 'Password must contain at least one number'}), 400
        
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in new_password):
            return jsonify({'success': False, 'message': 'Password must contain at least one special character'}), 400
        
        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get current admin
                cursor.execute("""
                    SELECT * FROM admin_users 
                    WHERE admin_id = %s
                """, (current_admin,))
                admin = cursor.fetchone()
                
                if not admin:
                    log_activity(current_admin, 'change_password', 'failed', ip_address, user_agent)
                    return jsonify({'success': False, 'message': 'Admin not found'}), 404
                
                # Verify current password
                if not bcrypt.checkpw(current_password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
                    log_activity(current_admin, 'change_password', 'failed', ip_address, user_agent)
                    return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
                
                # Check if new password is same as current
                if bcrypt.checkpw(new_password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'New password must be different from current password'}), 400
                
                # Hash new password
                new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Update password
                cursor.execute("""
                    UPDATE admin_users 
                    SET password_hash = %s, 
                        password_changed_at = NOW(),
                        must_change_password = FALSE
                    WHERE admin_id = %s
                """, (new_password_hash, current_admin))
                conn.commit()
                
                log_activity(current_admin, 'change_password', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'Password changed successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Change password error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/change-pin', methods=['POST'])
@jwt_required()
def change_pin():
    """Change or set admin transaction PIN"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        current_pin = data.get('currentPin')
        new_pin = data.get('newPin')
        confirm_pin = data.get('confirmPin')
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        # Validate new PIN and confirm PIN
        if not new_pin or not confirm_pin:
            return jsonify({'success': False, 'message': 'New PIN and confirmation are required'}), 400
        
        # Check if new PINs match
        if new_pin != confirm_pin:
            return jsonify({'success': False, 'message': 'New PINs do not match'}), 400
        
        # Validate PIN format
        if not new_pin.isdigit() or len(new_pin) != 6:
            return jsonify({'success': False, 'message': 'PIN must be exactly 6 digits'}), 400
        
        # Check for sequential numbers
        if new_pin in ['012345', '123456', '234567', '345678', '456789', '567890']:
            return jsonify({'success': False, 'message': 'PIN cannot be sequential numbers'}), 400
        
        # Check for repeated numbers
        if len(set(new_pin)) == 1:
            return jsonify({'success': False, 'message': 'PIN cannot be all same digits'}), 400
        
        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get current admin
                cursor.execute("""
                    SELECT * FROM admin_users 
                    WHERE admin_id = %s
                """, (current_admin,))
                admin = cursor.fetchone()
                
                if not admin:
                    log_activity(current_admin, 'change_pin', 'failed', ip_address, user_agent)
                    return jsonify({'success': False, 'message': 'Admin not found'}), 404
                
                # Check if PIN is set
                if not admin.get('pin_hash'):
                    # First time setting PIN - no current PIN required
                    pin_hash = bcrypt.hashpw(new_pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    action_message = 'PIN set successfully'
                else:
                    # PIN already exists - verify current PIN
                    if not current_pin:
                        return jsonify({'success': False, 'message': 'Current PIN is required'}), 400
                    
                    if not bcrypt.checkpw(current_pin.encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                        log_activity(current_admin, 'change_pin', 'failed', ip_address, user_agent)
                        return jsonify({'success': False, 'message': 'Current PIN is incorrect'}), 401
                    
                    # Check if new PIN is same as current
                    if bcrypt.checkpw(new_pin.encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                        return jsonify({'success': False, 'message': 'New PIN must be different from current PIN'}), 400
                    
                    # Hash new PIN
                    pin_hash = bcrypt.hashpw(new_pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    action_message = 'PIN changed successfully'
                
                # Update PIN
                cursor.execute("""
                    UPDATE admin_users 
                    SET pin_hash = %s, 
                        pin_changed_at = NOW()
                    WHERE admin_id = %s
                """, (pin_hash, current_admin))
                conn.commit()
                
                log_activity(current_admin, 'set_pin' if not admin.get('pin_hash') else 'change_pin', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': action_message
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Change PIN error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/pin-status', methods=['GET'])
@jwt_required()
def check_pin_status():
    """Check if admin has PIN set"""
    try:
        current_admin = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT pin_hash FROM admin_users 
                    WHERE admin_id = %s
                """, (current_admin,))
                admin = cursor.fetchone()
                
                if not admin:
                    return jsonify({'success': False, 'message': 'Admin not found'}), 404
                
                return jsonify({
                    'success': True,
                    'hasPinSet': admin.get('pin_hash') is not None and admin.get('pin_hash') != ''
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Check PIN status error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/delete-pin', methods=['DELETE'])
@jwt_required()
def delete_pin():
    """Delete admin transaction PIN"""
    try:
        current_admin = get_jwt_identity()
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get current admin
                cursor.execute("""
                    SELECT pin_hash FROM admin_users 
                    WHERE admin_id = %s
                """, (current_admin,))
                admin = cursor.fetchone()
                
                if not admin:
                    return jsonify({'success': False, 'message': 'Admin not found'}), 404
                
                if not admin.get('pin_hash'):
                    return jsonify({'success': False, 'message': 'No PIN set to delete'}), 400
                
                # Delete PIN
                cursor.execute("""
                    UPDATE admin_users 
                    SET pin_hash = NULL, 
                        pin_changed_at = NULL
                    WHERE admin_id = %s
                """, (current_admin,))
                conn.commit()
                
                log_activity(current_admin, 'delete_pin', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'PIN deleted successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Delete PIN error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/commercials/schemes', methods=['GET'])
@jwt_required()
def get_schemes():
    """Get all commercial schemes"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, scheme_name, is_active, created_by, created_at, updated_at
                    FROM commercial_schemes
                    ORDER BY created_at DESC
                """)
                schemes = cursor.fetchall()
                
                return jsonify({
                    'success': True,
                    'schemes': schemes
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get schemes error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/commercials/schemes', methods=['POST'])
@jwt_required()
def create_scheme():
    """Create a new commercial scheme"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        scheme_name = data.get('schemeName', '').strip()
        
        if not scheme_name:
            return jsonify({'success': False, 'message': 'Scheme name is required'}), 400
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check if scheme already exists
                cursor.execute("""
                    SELECT id FROM commercial_schemes WHERE scheme_name = %s
                """, (scheme_name,))
                
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Scheme name already exists'}), 400
                
                # Create scheme
                cursor.execute("""
                    INSERT INTO commercial_schemes (scheme_name, created_by)
                    VALUES (%s, %s)
                """, (scheme_name, current_admin))
                conn.commit()
                
                scheme_id = cursor.lastrowid
                
                log_activity(current_admin, f'create_scheme:{scheme_name}', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'Scheme created successfully',
                    'schemeId': scheme_id
                }), 201
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Create scheme error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/commercials/schemes/<int:scheme_id>/charges', methods=['GET'])
@jwt_required()
def get_scheme_charges(scheme_id):
    """Get all charges for a specific scheme"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get scheme info
                cursor.execute("""
                    SELECT id, scheme_name FROM commercial_schemes WHERE id = %s
                """, (scheme_id,))
                scheme = cursor.fetchone()
                
                if not scheme:
                    return jsonify({'success': False, 'message': 'Scheme not found'}), 404
                
                # Get charges
                cursor.execute("""
                    SELECT id, service_type, product_name, min_amount, max_amount, 
                           charge_value, charge_type, created_at, updated_at
                    FROM commercial_charges
                    WHERE scheme_id = %s
                    ORDER BY service_type, min_amount
                """, (scheme_id,))
                charges = cursor.fetchall()
                
                # Group by service type
                payout_charges = [c for c in charges if c['service_type'] == 'PAYOUT']
                payin_charges = [c for c in charges if c['service_type'] == 'PAYIN']
                
                return jsonify({
                    'success': True,
                    'scheme': scheme,
                    'charges': {
                        'payout': payout_charges,
                        'payin': payin_charges
                    }
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get scheme charges error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/commercials/charges', methods=['POST'])
@jwt_required()
def create_or_update_charges():
    """Create or update charges for a scheme"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        scheme_id = data.get('schemeId')
        charges = data.get('charges', [])
        
        if not scheme_id:
            return jsonify({'success': False, 'message': 'Scheme ID is required'}), 400
        
        if not charges:
            return jsonify({'success': False, 'message': 'Charges data is required'}), 400
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify scheme exists
                cursor.execute("""
                    SELECT scheme_name FROM commercial_schemes WHERE id = %s
                """, (scheme_id,))
                scheme = cursor.fetchone()
                
                if not scheme:
                    return jsonify({'success': False, 'message': 'Scheme not found'}), 404
                
                # Process each charge
                for charge in charges:
                    service_type = charge.get('serviceType')
                    product_name = charge.get('productName')
                    min_amount = charge.get('minAmount')
                    max_amount = charge.get('maxAmount')
                    charge_value = charge.get('chargeValue')
                    charge_type = charge.get('chargeType')
                    
                    # Validate required fields
                    if not all([service_type, product_name, min_amount, max_amount, charge_value, charge_type]):
                        continue
                    
                    # Insert or update charge
                    cursor.execute("""
                        INSERT INTO commercial_charges 
                        (scheme_id, service_type, product_name, min_amount, max_amount, charge_value, charge_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        min_amount = VALUES(min_amount),
                        max_amount = VALUES(max_amount),
                        charge_value = VALUES(charge_value),
                        charge_type = VALUES(charge_type),
                        updated_at = CURRENT_TIMESTAMP
                    """, (scheme_id, service_type, product_name, min_amount, max_amount, charge_value, charge_type))
                
                conn.commit()
                
                log_activity(current_admin, f'update_charges:{scheme["scheme_name"]}', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'Charges updated successfully'
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Create/update charges error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/commercials/schemes/<int:scheme_id>', methods=['DELETE'])
@jwt_required()
def delete_scheme(scheme_id):
    """Delete a commercial scheme"""
    try:
        current_admin = get_jwt_identity()
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get scheme name before deletion
                cursor.execute("""
                    SELECT scheme_name FROM commercial_schemes WHERE id = %s
                """, (scheme_id,))
                scheme = cursor.fetchone()
                
                if not scheme:
                    return jsonify({'success': False, 'message': 'Scheme not found'}), 404
                
                # Delete scheme (charges will be deleted automatically due to CASCADE)
                cursor.execute("""
                    DELETE FROM commercial_schemes WHERE id = %s
                """, (scheme_id,))
                conn.commit()
                
                log_activity(current_admin, f'delete_scheme:{scheme["scheme_name"]}', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'Scheme deleted successfully'
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Delete scheme error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/merchants/onboard', methods=['POST'])
@jwt_required()
def onboard_merchant():
    """Onboard a new merchant"""
    try:
        current_admin = get_jwt_identity()
        
        # Get form data
        data = request.form.to_dict()
        files = request.files
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        # Validate required fields
        required_fields = ['fullName', 'email', 'mobile', 'aadharCard', 'panNo', 'pincode', 
                          'state', 'city', 'address', 'merchantType', 'accountNum', 'ifscCode', 
                          'gstNo', 'schemeId']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Validate files
        required_files = ['aadharFront', 'aadharBack', 'panCard', 'gstCertificate', 
                         'shopPhoto', 'profilePhoto']
        
        for file_key in required_files:
            if file_key not in files:
                return jsonify({'success': False, 'message': f'{file_key} is required'}), 400
            if not allowed_file(files[file_key].filename):
                return jsonify({'success': False, 'message': f'Invalid file type for {file_key}'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check if mobile already exists
                cursor.execute("SELECT merchant_id FROM merchants WHERE mobile = %s", (data['mobile'],))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Mobile number already registered'}), 400
                
                # Check if email already exists
                cursor.execute("SELECT merchant_id FROM merchants WHERE email = %s", (data['email'],))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Email already registered'}), 400
                
                # Verify scheme exists
                cursor.execute("SELECT id FROM commercial_schemes WHERE id = %s", (data['schemeId'],))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Invalid scheme selected'}), 400
                
                # Generate credentials
                merchant_id = data['mobile']  # Merchant ID is mobile number
                password = generate_random_password()
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Generate API credentials
                authorization_key = generate_authorization_key()
                module_secret = generate_module_secret()
                aes_iv = generate_aes_iv()
                aes_key = generate_aes_key()
                
                # Save uploaded files
                file_paths = {}
                for file_key in required_files:
                    file = files[file_key]
                    filename = secure_filename(f"{merchant_id}_{file_key}_{file.filename}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    file_paths[file_key] = file_path
                
                # Insert merchant
                cursor.execute("""
                    INSERT INTO merchants (
                        merchant_id, password_hash, full_name, email, mobile, dob,
                        aadhar_card, pan_no, pincode, state, city, house_number,
                        address, landmark, merchant_type, account_number, ifsc_code,
                        gst_no, scheme_id, authorization_key, module_secret,
                        aes_iv, aes_key, created_by
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    merchant_id, password_hash, data['fullName'], data['email'], data['mobile'],
                    data.get('dob'), data['aadharCard'], data['panNo'], data['pincode'],
                    data['state'], data['city'], data.get('houseNumber'), data['address'],
                    data.get('landmark'), data['merchantType'].upper(), data['accountNum'],
                    data['ifscCode'], data['gstNo'], data['schemeId'], authorization_key,
                    module_secret, aes_iv, aes_key, current_admin
                ))
                
                # Insert documents
                cursor.execute("""
                    INSERT INTO merchant_documents (
                        merchant_id, aadhar_front_path, aadhar_back_path, pan_card_path,
                        gst_certificate_path, shop_photo_path, profile_photo_path
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    merchant_id, file_paths['aadharFront'], file_paths['aadharBack'],
                    file_paths['panCard'], file_paths['gstCertificate'],
                    file_paths['shopPhoto'], file_paths['profilePhoto']
                ))
                
                # Initialize callback URLs
                cursor.execute("""
                    INSERT INTO merchant_callbacks (merchant_id)
                    VALUES (%s)
                """, (merchant_id,))
                
                conn.commit()
                
                # Send credentials email
                email_sent = send_merchant_credentials_email(
                    data['fullName'], data['email'], merchant_id, password
                )
                
                log_activity(current_admin, f'onboard_merchant:{merchant_id}', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'Merchant onboarded successfully',
                    'merchantId': merchant_id,
                    'emailSent': email_sent
                }), 201
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Merchant onboarding error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/captcha', methods=['GET'])
def get_merchant_captcha():
    """Generate and return captcha for merchant login"""
    try:
        # Generate captcha text
        captcha_text = captcha_gen.generate_captcha_text()
        
        # Create session ID
        session_id = secrets.token_urlsafe(32)
        
        # Store captcha (expires in 5 minutes)
        captcha_sessions[session_id] = {
            'text': captcha_text,
            'expires': datetime.now() + timedelta(minutes=5)
        }
        
        # Generate captcha image
        captcha_image = captcha_gen.get_captcha_base64(captcha_text)
        
        return jsonify({
            'success': True,
            'sessionId': session_id,
            'captchaImage': captcha_image
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/merchant/login', methods=['POST'])
def merchant_login():
    """Merchant login"""
    try:
        data = request.get_json()
        merchant_id = data.get('merchantId')
        password = data.get('password')
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        # Validate input
        if not all([merchant_id, password]):
            return jsonify({'success': False, 'message': 'Merchant ID and password are required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM merchants WHERE merchant_id = %s
                """, (merchant_id,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
                
                if not merchant['is_active']:
                    return jsonify({'success': False, 'message': 'Account is inactive'}), 403
                
                # Verify password
                if not bcrypt.checkpw(password.encode('utf-8'), merchant['password_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
                
                # Create JWT token
                access_token = create_access_token(identity=merchant_id)
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'token': access_token,
                    'merchantId': merchant_id,
                    'merchantName': merchant['full_name'],
                    'email': merchant['email']
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Merchant login error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/verify', methods=['GET'])
@jwt_required()
def verify_merchant_token():
    """Verify merchant JWT token"""
    try:
        current_merchant = get_jwt_identity()
        new_token = create_access_token(identity=current_merchant)
        
        return jsonify({
            'success': True,
            'merchantId': current_merchant,
            'token': new_token
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': 'Invalid token'}), 401

@app.route('/api/merchant/credentials', methods=['GET'])
@jwt_required()
def get_merchant_credentials():
    """Get merchant API credentials"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get merchant credentials
                cursor.execute("""
                    SELECT merchant_id, authorization_key, module_secret, aes_iv, aes_key
                    FROM merchants WHERE merchant_id = %s
                """, (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                # Get IP whitelist
                cursor.execute("""
                    SELECT ip_address as ip, created_at FROM merchant_ip_whitelist
                    WHERE merchant_id = %s ORDER BY created_at DESC
                """, (current_merchant,))
                ip_whitelist = cursor.fetchall()
                
                # Get callback URLs
                cursor.execute("""
                    SELECT payin_callback_url, payout_callback_url
                    FROM merchant_callbacks WHERE merchant_id = %s
                """, (current_merchant,))
                callbacks = cursor.fetchone()
                
                return jsonify({
                    'success': True,
                    'credentials': {
                        'merchant_id': merchant['merchant_id'],
                        'authorization_key': merchant['authorization_key'],
                        'module_secret': merchant['module_secret'],
                        'aes_iv': merchant['aes_iv'],
                        'aes_key': merchant['aes_key'],
                        'environment': 'PRODUCTION',
                        'base_url': 'https://api.rupipay.shop'
                    },
                    'ipWhitelist': ip_whitelist,
                    'callbacks': callbacks if callbacks else {
                        'payin_callback_url': '',
                        'payout_callback_url': ''
                    }
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get credentials error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/ip-whitelist', methods=['POST'])
@jwt_required()
def add_ip_whitelist():
    """Add IP to whitelist"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        ip_address = data.get('ipAddress')
        
        if not ip_address:
            return jsonify({'success': False, 'message': 'IP address is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check count
                cursor.execute("""
                    SELECT COUNT(*) as count FROM merchant_ip_whitelist
                    WHERE merchant_id = %s
                """, (current_merchant,))
                result = cursor.fetchone()
                
                if result['count'] >= 2:
                    return jsonify({'success': False, 'message': 'Maximum 2 IP addresses allowed'}), 400
                
                # Add IP
                cursor.execute("""
                    INSERT INTO merchant_ip_whitelist (merchant_id, ip_address)
                    VALUES (%s, %s)
                """, (current_merchant, ip_address))
                conn.commit()
                
                return jsonify({'success': True, 'message': 'IP address added successfully'}), 201
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Add IP whitelist error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/ip-whitelist/<ip_address>', methods=['DELETE'])
@jwt_required()
def remove_ip_whitelist(ip_address):
    """Remove IP from whitelist"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM merchant_ip_whitelist
                    WHERE merchant_id = %s AND ip_address = %s
                """, (current_merchant, ip_address))
                conn.commit()
                
                return jsonify({'success': True, 'message': 'IP address removed successfully'}), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Remove IP whitelist error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/callbacks', methods=['PUT'])
@jwt_required()
def update_callbacks():
    """Update callback URLs"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        payin_url = data.get('payinCallbackUrl', '')
        payout_url = data.get('payoutCallbackUrl', '')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Insert or update callbacks
                cursor.execute("""
                    INSERT INTO merchant_callbacks (merchant_id, payin_callback_url, payout_callback_url)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    payin_callback_url = VALUES(payin_callback_url),
                    payout_callback_url = VALUES(payout_callback_url),
                    updated_at = CURRENT_TIMESTAMP
                """, (current_merchant, payin_url, payout_url))
                conn.commit()
                
                return jsonify({'success': True, 'message': 'Callback URLs updated successfully'}), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Update callbacks error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/commercials', methods=['GET'])
@jwt_required()
def get_merchant_commercials():
    """Get merchant's commercial rates"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get merchant's scheme_id first
                cursor.execute("""
                    SELECT scheme_id FROM merchants WHERE merchant_id = %s
                """, (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant or not merchant['scheme_id']:
                    return jsonify({
                        'success': False, 
                        'message': 'No scheme assigned',
                        'detail': 'Please contact administrator to assign a commercial scheme'
                    }), 404
                
                # Get scheme details
                cursor.execute("""
                    SELECT id as scheme_id, scheme_name
                    FROM commercial_schemes
                    WHERE id = %s
                """, (merchant['scheme_id'],))
                scheme = cursor.fetchone()
                
                if not scheme:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid scheme',
                        'detail': 'The assigned scheme does not exist'
                    }), 404
                
                # Get charges
                cursor.execute("""
                    SELECT service_type, product_name, min_amount, max_amount,
                           charge_value, charge_type
                    FROM commercial_charges
                    WHERE scheme_id = %s
                    ORDER BY service_type, min_amount
                """, (scheme['scheme_id'],))
                charges = cursor.fetchall()
                
                # Group by service type
                payout_charges = [c for c in charges if c['service_type'] == 'PAYOUT']
                payin_charges = [c for c in charges if c['service_type'] == 'PAYIN']
                
                return jsonify({
                    'success': True,
                    'scheme': scheme,
                    'charges': {
                        'payout': payout_charges,
                        'payin': payin_charges
                    }
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get merchant commercials error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/change-password', methods=['POST'])
@jwt_required()
def merchant_change_password():
    """Change merchant password"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        confirm_password = data.get('confirmPassword')
        
        if not all([current_password, new_password, confirm_password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'New passwords do not match'}), 400
        
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password_hash FROM merchants WHERE merchant_id = %s", (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                if not bcrypt.checkpw(current_password.encode('utf-8'), merchant['password_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
                
                if bcrypt.checkpw(new_password.encode('utf-8'), merchant['password_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'New password must be different'}), 400
                
                new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                cursor.execute("""
                    UPDATE merchants 
                    SET password_hash = %s, password_changed_at = NOW()
                    WHERE merchant_id = %s
                """, (new_password_hash, current_merchant))
                conn.commit()
                
                return jsonify({'success': True, 'message': 'Password changed successfully'}), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Change password error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/pin-status', methods=['GET'])
@jwt_required()
def merchant_pin_status():
    """Check if merchant has PIN set"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT pin_hash FROM merchants WHERE merchant_id = %s", (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                return jsonify({
                    'success': True,
                    'hasPinSet': merchant.get('pin_hash') is not None and merchant.get('pin_hash') != ''
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Check PIN status error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/change-pin', methods=['POST'])
@jwt_required()
def merchant_change_pin():
    """Change or set merchant PIN"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        current_pin = data.get('currentPin')
        new_pin = data.get('newPin')
        confirm_pin = data.get('confirmPin')
        
        if not new_pin or not confirm_pin:
            return jsonify({'success': False, 'message': 'New PIN and confirmation are required'}), 400
        
        if new_pin != confirm_pin:
            return jsonify({'success': False, 'message': 'New PINs do not match'}), 400
        
        if not new_pin.isdigit() or len(new_pin) != 6:
            return jsonify({'success': False, 'message': 'PIN must be exactly 6 digits'}), 400
        
        if new_pin in ['012345', '123456', '234567', '345678', '456789', '567890']:
            return jsonify({'success': False, 'message': 'PIN cannot be sequential'}), 400
        
        if len(set(new_pin)) == 1:
            return jsonify({'success': False, 'message': 'PIN cannot be all same digits'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT pin_hash FROM merchants WHERE merchant_id = %s", (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                if not merchant.get('pin_hash'):
                    # First time setting PIN
                    pin_hash = bcrypt.hashpw(new_pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    action_message = 'PIN set successfully'
                else:
                    # PIN already exists - verify current PIN
                    if not current_pin:
                        return jsonify({'success': False, 'message': 'Current PIN is required'}), 400
                    
                    if not bcrypt.checkpw(current_pin.encode('utf-8'), merchant['pin_hash'].encode('utf-8')):
                        return jsonify({'success': False, 'message': 'Current PIN is incorrect'}), 401
                    
                    if bcrypt.checkpw(new_pin.encode('utf-8'), merchant['pin_hash'].encode('utf-8')):
                        return jsonify({'success': False, 'message': 'New PIN must be different'}), 400
                    
                    pin_hash = bcrypt.hashpw(new_pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    action_message = 'PIN changed successfully'
                
                cursor.execute("""
                    UPDATE merchants 
                    SET pin_hash = %s, pin_changed_at = NOW()
                    WHERE merchant_id = %s
                """, (pin_hash, current_merchant))
                conn.commit()
                
                return jsonify({'success': True, 'message': action_message}), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Change PIN error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/verify-pin', methods=['POST'])
@jwt_required()
def merchant_verify_pin():
    """Verify merchant PIN"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        pin = data.get('pin')
        
        if not pin:
            return jsonify({'success': False, 'message': 'PIN is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT pin_hash FROM merchants WHERE merchant_id = %s", (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                if not merchant.get('pin_hash'):
                    return jsonify({'success': False, 'message': 'PIN not set'}), 400
                
                if not bcrypt.checkpw(pin.encode('utf-8'), merchant['pin_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Incorrect PIN'}), 401
                
                return jsonify({'success': True, 'message': 'PIN verified'}), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Verify PIN error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/delete-pin', methods=['DELETE'])
@jwt_required()
def merchant_delete_pin():
    """Delete merchant transaction PIN"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT pin_hash FROM merchants WHERE merchant_id = %s", (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                if not merchant.get('pin_hash'):
                    return jsonify({'success': False, 'message': 'No PIN set to delete'}), 400
                
                # Delete PIN (no verification required for merchant)
                cursor.execute("""
                    UPDATE merchants 
                    SET pin_hash = NULL, pin_changed_at = NULL
                    WHERE merchant_id = %s
                """, (current_merchant,))
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Transaction PIN deleted successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Delete PIN error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    """Get all merchants/users"""
    try:
        current_admin = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        m.id, m.merchant_id, m.full_name, m.email, m.mobile,
                        m.merchant_type, m.is_active, m.created_at,
                        m.account_number, m.ifsc_code, m.gst_no,
                        m.address, m.city, m.state, m.pincode,
                        m.pan_no, m.aadhar_card, m.dob,
                        cs.scheme_name
                    FROM merchants m
                    LEFT JOIN commercial_schemes cs ON m.scheme_id = cs.id
                    ORDER BY m.created_at DESC
                """)
                users = cursor.fetchall()
                
                # Format created_at to IST
                for user in users:
                    if user.get('created_at'):
                        user['created_at_ist'] = format_datetime_ist(user['created_at'])
                
                return jsonify({
                    'success': True,
                    'users': users
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/users/<merchant_id>', methods=['GET'])
@jwt_required()
def get_user_details(merchant_id):
    """Get detailed user information"""
    try:
        current_admin = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get merchant details
                cursor.execute("""
                    SELECT 
                        m.*, cs.scheme_name,
                        md.aadhar_front_path, md.aadhar_back_path,
                        md.pan_card_path, md.gst_certificate_path,
                        md.cancelled_cheque_path, md.shop_photo_path,
                        md.profile_photo_path
                    FROM merchants m
                    LEFT JOIN commercial_schemes cs ON m.scheme_id = cs.id
                    LEFT JOIN merchant_documents md ON m.merchant_id = md.merchant_id
                    WHERE m.merchant_id = %s
                """, (merchant_id,))
                user = cursor.fetchone()
                
                if not user:
                    return jsonify({'success': False, 'message': 'User not found'}), 404
                
                # Format created_at to IST
                if user.get('created_at'):
                    user['created_at_ist'] = format_datetime_ist(user['created_at'])
                
                return jsonify({
                    'success': True,
                    'user': user
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get user details error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/users/<merchant_id>', methods=['PUT'])
@jwt_required()
def update_user(merchant_id):
    """Update user information"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check if user exists
                cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'User not found'}), 404
                
                # Update user
                cursor.execute("""
                    UPDATE merchants SET
                        full_name = %s,
                        email = %s,
                        mobile = %s,
                        merchant_type = %s,
                        scheme_id = %s,
                        account_number = %s,
                        ifsc_code = %s,
                        gst_no = %s,
                        address = %s,
                        city = %s,
                        state = %s,
                        pincode = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE merchant_id = %s
                """, (
                    data.get('full_name'),
                    data.get('email'),
                    data.get('mobile'),
                    data.get('merchant_type'),
                    data.get('scheme_id'),
                    data.get('account_number'),
                    data.get('ifsc_code'),
                    data.get('gst_no'),
                    data.get('address'),
                    data.get('city'),
                    data.get('state'),
                    data.get('pincode'),
                    merchant_id
                ))
                conn.commit()
                
                log_activity(current_admin, f'update_user:{merchant_id}', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'User updated successfully'
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Update user error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/users/<merchant_id>/toggle-status', methods=['PUT'])
@jwt_required()
def toggle_user_status(merchant_id):
    """Activate or deactivate user"""
    try:
        current_admin = get_jwt_identity()
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get current status
                cursor.execute("SELECT is_active FROM merchants WHERE merchant_id = %s", (merchant_id,))
                user = cursor.fetchone()
                
                if not user:
                    return jsonify({'success': False, 'message': 'User not found'}), 404
                
                # Toggle status
                new_status = not user['is_active']
                cursor.execute("""
                    UPDATE merchants SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE merchant_id = %s
                """, (new_status, merchant_id))
                conn.commit()
                
                action = 'activate_user' if new_status else 'deactivate_user'
                log_activity(current_admin, f'{action}:{merchant_id}', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': f'User {"activated" if new_status else "deactivated"} successfully',
                    'is_active': new_status
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Toggle user status error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/users/<merchant_id>/reset-password', methods=['POST'])
@jwt_required()
def reset_user_password(merchant_id):
    """Reset user password"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        new_password = data.get('newPassword')
        
        if not new_password:
            return jsonify({'success': False, 'message': 'New password is required'}), 400
        
        # Validate password strength
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters long'}), 400
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check if user exists
                cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'User not found'}), 404
                
                # Hash new password
                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Update password
                cursor.execute("""
                    UPDATE merchants SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE merchant_id = %s
                """, (password_hash, merchant_id))
                conn.commit()
                
                log_activity(current_admin, f'reset_password:{merchant_id}', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'Password reset successfully'
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/users/<merchant_id>', methods=['DELETE'])
@jwt_required()
def delete_user(merchant_id):
    """Delete user"""
    try:
        current_admin = get_jwt_identity()
        
        # Get client info
        ip_address = get_real_ip()
        user_agent = request.headers.get('User-Agent')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check if user exists
                cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'User not found'}), 404
                
                # Delete user (cascade will handle related records)
                cursor.execute("DELETE FROM merchants WHERE merchant_id = %s", (merchant_id,))
                conn.commit()
                
                log_activity(current_admin, f'delete_user:{merchant_id}', 'success', ip_address, user_agent)
                
                return jsonify({
                    'success': True,
                    'message': 'User deleted successfully'
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Delete user error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/users/<merchant_id>/documents/<doc_type>', methods=['GET'])
@jwt_required()
def download_document(merchant_id, doc_type):
    """Download user document"""
    try:
        current_admin = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get document path
                cursor.execute("""
                    SELECT * FROM merchant_documents WHERE merchant_id = %s
                """, (merchant_id,))
                docs = cursor.fetchone()
                
                if not docs:
                    return jsonify({'success': False, 'message': 'Documents not found'}), 404
                
                # Map doc_type to column name
                doc_mapping = {
                    'aadhar_front': 'aadhar_front_path',
                    'aadhar_back': 'aadhar_back_path',
                    'pan_card': 'pan_card_path',
                    'gst_certificate': 'gst_certificate_path',
                    'cancelled_cheque': 'cancelled_cheque_path',
                    'shop_photo': 'shop_photo_path',
                    'profile_photo': 'profile_photo_path'
                }
                
                if doc_type not in doc_mapping:
                    return jsonify({'success': False, 'message': 'Invalid document type'}), 400
                
                doc_path = docs.get(doc_mapping[doc_type])
                
                if not doc_path:
                    return jsonify({'success': False, 'message': 'Document not available'}), 404
                
                # Convert relative path to full URL using config
                base_url = Config.UPLOADS_BASE_URL.rstrip('/')
                document_url = f"{base_url}/{doc_path}" if not doc_path.startswith('http') else doc_path
                
                return jsonify({
                    'success': True,
                    'document_url': document_url,
                    'document_path': doc_path,
                    'document_type': doc_type
                }), 200
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Download document error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/decrypt', methods=['POST'])
@jwt_required()
def decrypt_data():
    """Decrypt AES encrypted data"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        encrypted_text = data.get('encryptedText')
        
        if not encrypted_text:
            return jsonify({'success': False, 'message': 'Encrypted text is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get merchant's AES credentials
                cursor.execute("""
                    SELECT aes_iv, aes_key FROM merchants WHERE merchant_id = %s
                """, (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                # Decrypt the data
                decrypted_text = decrypt_aes(encrypted_text, merchant['aes_key'], merchant['aes_iv'])
                
                if decrypted_text is None:
                    return jsonify({'success': False, 'message': 'Decryption failed. Please check your encrypted text.'}), 400
                
                return jsonify({
                    'success': True,
                    'decryptedText': decrypted_text
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Decrypt error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/encrypt', methods=['POST'])
@jwt_required()
def encrypt_data():
    """Encrypt data using AES"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        plain_text = data.get('plainText')
        
        if not plain_text:
            return jsonify({'success': False, 'message': 'Plain text is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get merchant's AES credentials
                cursor.execute("""
                    SELECT aes_iv, aes_key FROM merchants WHERE merchant_id = %s
                """, (current_merchant,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                # Encrypt the data
                encrypted_text = encrypt_aes(plain_text, merchant['aes_key'], merchant['aes_iv'])
                
                if encrypted_text is None:
                    return jsonify({'success': False, 'message': 'Encryption failed'}), 400
                
                return jsonify({
                    'success': True,
                    'encryptedText': encrypted_text
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Encrypt error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/wallet/overview', methods=['GET'])
@jwt_required()
def get_wallet_overview():
    """Get merchant wallet overview - balance, total payin, total payout"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify merchant exists and is active
                cursor.execute("""
                    SELECT merchant_id, is_active 
                    FROM merchants 
                    WHERE merchant_id = %s
                """, (current_merchant,))
                
                merchant = cursor.fetchone()
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                if not merchant['is_active']:
                    return jsonify({'success': False, 'message': 'Merchant account is inactive'}), 403
                
                # Get wallet balance
                cursor.execute("""
                    SELECT balance FROM merchant_wallet WHERE merchant_id = %s
                """, (current_merchant,))
                wallet = cursor.fetchone()
                balance = float(wallet['balance']) if wallet else 0.00
                
                # Get total successful payin amount
                cursor.execute("""
                    SELECT COALESCE(SUM(net_amount), 0) as total_payin
                    FROM payin_transactions
                    WHERE merchant_id = %s AND status = 'SUCCESS'
                """, (current_merchant,))
                payin_result = cursor.fetchone()
                total_payin = float(payin_result['total_payin']) if payin_result else 0.00
                
                # Get total successful payout amount (when payout is implemented)
                # For now, set to 0
                total_payout = 0.00
                
                return jsonify({
                    'success': True,
                    'balance': balance,
                    'totalPayin': total_payin,
                    'totalPayout': total_payout,
                    'merchantId': current_merchant
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get wallet overview error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/wallet/overview/<merchant_id>', methods=['GET'])
@jwt_required()
def admin_get_wallet_overview(merchant_id):
    """Get merchant wallet overview - admin only"""
    try:
        current_admin = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify admin
                cursor.execute("SELECT admin_id FROM admin_users WHERE admin_id = %s", (current_admin,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Unauthorized'}), 403
                
                # Verify merchant exists
                cursor.execute("""
                    SELECT merchant_id, full_name, is_active 
                    FROM merchants 
                    WHERE merchant_id = %s
                """, (merchant_id,))
                
                merchant = cursor.fetchone()
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                # Get wallet balance
                cursor.execute("""
                    SELECT balance FROM merchant_wallet WHERE merchant_id = %s
                """, (merchant_id,))
                wallet = cursor.fetchone()
                balance = float(wallet['balance']) if wallet else 0.00
                
                # Get total successful payin amount
                cursor.execute("""
                    SELECT COALESCE(SUM(net_amount), 0) as total_payin
                    FROM payin_transactions
                    WHERE merchant_id = %s AND status = 'SUCCESS'
                """, (merchant_id,))
                payin_result = cursor.fetchone()
                total_payin = float(payin_result['total_payin']) if payin_result else 0.00
                
                # Get total successful payout amount (when payout is implemented)
                total_payout = 0.00
                
                return jsonify({
                    'success': True,
                    'balance': balance,
                    'totalPayin': total_payin,
                    'totalPayout': total_payout,
                    'merchantId': merchant_id,
                    'merchantName': merchant['full_name'],
                    'isActive': merchant['is_active']
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Admin get wallet overview error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/banks', methods=['GET'])
@jwt_required()
def get_merchant_banks():
    """Get all banks for the merchant"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, bank_name, account_number, ifsc_code, branch_name,
                           account_holder_name, is_active, created_at
                    FROM merchant_banks
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                """, (current_merchant,))
                
                banks = cursor.fetchall()
                
                # Format dates
                for bank in banks:
                    if bank.get('created_at'):
                        bank['created_at_ist'] = format_datetime_ist(bank['created_at'])
                
                return jsonify({
                    'success': True,
                    'banks': banks
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get merchant banks error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/banks', methods=['POST'])
@jwt_required()
def add_merchant_bank():
    """Add a new bank for the merchant"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['bankName', 'accountNumber', 'reAccountNumber', 'ifscCode', 
                          'branchName', 'accountHolderName', 'tpin']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Verify account numbers match
        if data['accountNumber'] != data['reAccountNumber']:
            return jsonify({'success': False, 'message': 'Account numbers do not match'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify merchant's TPIN
                cursor.execute("""
                    SELECT pin_hash FROM merchants WHERE merchant_id = %s
                """, (current_merchant,))
                
                merchant = cursor.fetchone()
                if not merchant or not merchant['pin_hash']:
                    return jsonify({'success': False, 'message': 'Please set your TPIN first'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), merchant['pin_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 401
                
                # Check bank limit (max 5 banks)
                cursor.execute("""
                    SELECT COUNT(*) as count FROM merchant_banks WHERE merchant_id = %s
                """, (current_merchant,))
                
                count_result = cursor.fetchone()
                if count_result['count'] >= 5:
                    return jsonify({'success': False, 'message': 'Maximum 5 banks allowed'}), 400
                
                # Check for duplicate account number
                cursor.execute("""
                    SELECT id FROM merchant_banks 
                    WHERE merchant_id = %s AND account_number = %s
                """, (current_merchant, data['accountNumber']))
                
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Bank account already exists'}), 400
                
                # Hash TPIN for bank record
                tpin_hash = bcrypt.hashpw(data['tpin'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Insert bank
                cursor.execute("""
                    INSERT INTO merchant_banks 
                    (merchant_id, bank_name, account_number, ifsc_code, branch_name, 
                     account_holder_name, tpin_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (current_merchant, data['bankName'], data['accountNumber'], 
                      data['ifscCode'], data['branchName'], data['accountHolderName'], tpin_hash))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Bank added successfully'
                }), 201
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Add merchant bank error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/banks/<int:bank_id>', methods=['PUT'])
@jwt_required()
def update_merchant_bank(bank_id):
    """Update merchant bank details"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify bank belongs to merchant
                cursor.execute("""
                    SELECT id FROM merchant_banks 
                    WHERE id = %s AND merchant_id = %s
                """, (bank_id, current_merchant))
                
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Bank not found'}), 404
                
                # Update bank details
                cursor.execute("""
                    UPDATE merchant_banks 
                    SET bank_name = %s, ifsc_code = %s, branch_name = %s, 
                        account_holder_name = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND merchant_id = %s
                """, (data.get('bankName'), data.get('ifscCode'), data.get('branchName'),
                      data.get('accountHolderName'), bank_id, current_merchant))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Bank updated successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Update merchant bank error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/banks/<int:bank_id>', methods=['DELETE'])
@jwt_required()
def delete_merchant_bank(bank_id):
    """Delete merchant bank"""
    try:
        current_merchant = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('tpin'):
            return jsonify({'success': False, 'message': 'TPIN is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify merchant's TPIN
                cursor.execute("""
                    SELECT pin_hash FROM merchants WHERE merchant_id = %s
                """, (current_merchant,))
                
                merchant = cursor.fetchone()
                if not merchant or not merchant['pin_hash']:
                    return jsonify({'success': False, 'message': 'TPIN not set'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), merchant['pin_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 401
                
                # Verify bank belongs to merchant
                cursor.execute("""
                    SELECT id FROM merchant_banks 
                    WHERE id = %s AND merchant_id = %s
                """, (bank_id, current_merchant))
                
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Bank not found'}), 404
                
                # Delete bank
                cursor.execute("""
                    DELETE FROM merchant_banks 
                    WHERE id = %s AND merchant_id = %s
                """, (bank_id, current_merchant))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Bank deleted successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Delete merchant bank error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/merchant/banks/<int:bank_id>/toggle-status', methods=['PUT'])
@jwt_required()
def toggle_merchant_bank_status(bank_id):
    """Toggle merchant bank active status"""
    try:
        current_merchant = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get current status
                cursor.execute("""
                    SELECT is_active FROM merchant_banks 
                    WHERE id = %s AND merchant_id = %s
                """, (bank_id, current_merchant))
                
                bank = cursor.fetchone()
                if not bank:
                    return jsonify({'success': False, 'message': 'Bank not found'}), 404
                
                new_status = not bank['is_active']
                
                # Update status
                cursor.execute("""
                    UPDATE merchant_banks 
                    SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND merchant_id = %s
                """, (new_status, bank_id, current_merchant))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Bank {"activated" if new_status else "deactivated"} successfully',
                    'isActive': new_status
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Toggle merchant bank status error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/banks', methods=['GET'])
@jwt_required()
def get_admin_banks():
    """Get admin's own banks"""
    try:
        current_admin = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, bank_name, account_number, ifsc_code, branch_name,
                           account_holder_name, is_active, created_at
                    FROM admin_banks
                    WHERE admin_id = %s
                    ORDER BY created_at DESC
                """, (current_admin,))
                
                banks = cursor.fetchall()
                
                # Format dates
                for bank in banks:
                    if bank.get('created_at'):
                        bank['created_at_ist'] = format_datetime_ist(bank['created_at'])
                
                return jsonify({
                    'success': True,
                    'banks': banks
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get admin banks error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/banks', methods=['POST'])
@jwt_required()
def add_admin_bank():
    """Add a new bank for admin"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['bankName', 'accountNumber', 'reAccountNumber', 'ifscCode', 
                          'branchName', 'accountHolderName', 'tpin']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Verify account numbers match
        if data['accountNumber'] != data['reAccountNumber']:
            return jsonify({'success': False, 'message': 'Account numbers do not match'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify admin's TPIN
                cursor.execute("""
                    SELECT pin_hash FROM admin_users WHERE admin_id = %s
                """, (current_admin,))
                
                admin = cursor.fetchone()
                if not admin or not admin['pin_hash']:
                    return jsonify({'success': False, 'message': 'Please set your TPIN first'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 401
                
                # Check for duplicate account number
                cursor.execute("""
                    SELECT id FROM admin_banks 
                    WHERE admin_id = %s AND account_number = %s
                """, (current_admin, data['accountNumber']))
                
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Bank account already exists'}), 400
                
                # Hash TPIN for bank record
                tpin_hash = bcrypt.hashpw(data['tpin'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Insert bank
                cursor.execute("""
                    INSERT INTO admin_banks 
                    (admin_id, bank_name, account_number, ifsc_code, branch_name, 
                     account_holder_name, tpin_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (current_admin, data['bankName'], data['accountNumber'], 
                      data['ifscCode'], data['branchName'], data['accountHolderName'], tpin_hash))
                
                conn.commit()
                
                # Log activity
                log_activity(current_admin, 'Bank account added', 'SUCCESS')
                
                return jsonify({
                    'success': True,
                    'message': 'Bank added successfully'
                }), 201
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Add admin bank error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/banks/<int:bank_id>', methods=['DELETE'])
@jwt_required()
def delete_admin_bank(bank_id):
    """Delete admin bank"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('tpin'):
            return jsonify({'success': False, 'message': 'TPIN is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify admin's TPIN
                cursor.execute("""
                    SELECT pin_hash FROM admin_users WHERE admin_id = %s
                """, (current_admin,))
                
                admin = cursor.fetchone()
                if not admin or not admin['pin_hash']:
                    return jsonify({'success': False, 'message': 'TPIN not set'}), 400
                
                if not bcrypt.checkpw(data['tpin'].encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 401
                
                # Verify bank belongs to admin
                cursor.execute("""
                    SELECT id FROM admin_banks 
                    WHERE id = %s AND admin_id = %s
                """, (bank_id, current_admin))
                
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Bank not found'}), 404
                
                # Delete bank
                cursor.execute("""
                    DELETE FROM admin_banks 
                    WHERE id = %s AND admin_id = %s
                """, (bank_id, current_admin))
                
                conn.commit()
                
                # Log activity
                log_activity(current_admin, 'Bank account deleted', 'SUCCESS')
                
                return jsonify({
                    'success': True,
                    'message': 'Bank deleted successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Delete admin bank error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/banks/<int:bank_id>/toggle-status', methods=['PUT'])
@jwt_required()
def toggle_admin_bank_status(bank_id):
    """Toggle admin bank active status"""
    try:
        current_admin = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get current status
                cursor.execute("""
                    SELECT is_active FROM admin_banks 
                    WHERE id = %s AND admin_id = %s
                """, (bank_id, current_admin))
                
                bank = cursor.fetchone()
                if not bank:
                    return jsonify({'success': False, 'message': 'Bank not found'}), 404
                
                new_status = not bank['is_active']
                
                # Update status
                cursor.execute("""
                    UPDATE admin_banks 
                    SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND admin_id = %s
                """, (new_status, bank_id, current_admin))
                
                conn.commit()
                
                # Log activity
                log_activity(
                    current_admin,
                    f"Bank {'activated' if new_status else 'deactivated'}",
                    'SUCCESS'
                )
                
                return jsonify({
                    'success': True,
                    'message': f'Bank {"activated" if new_status else "deactivated"} successfully',
                    'isActive': new_status
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Toggle admin bank status error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/api/admin/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'moneyone-admin-api'}), 200

@app.route('/health', methods=['GET'])
def health():
    """Simple health check endpoint for load balancer"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    # Initialize database
    print("Initializing database...")
    init_database()
    
    # Create default admin user
    print("Creating default admin user...")
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                # Check if admin exists
                cursor.execute("SELECT * FROM admin_users WHERE admin_id = '6239572985'")
                if not cursor.fetchone():
                    # Hash password
                    password_hash = bcrypt.hashpw('admin@123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Insert admin
                    cursor.execute("""
                        INSERT INTO admin_users (admin_id, password_hash, is_active)
                        VALUES (%s, %s, %s)
                    """, ('6239572985', password_hash, True))
                    conn.commit()
                    print("Default admin user created successfully!")
                else:
                    print("Default admin user already exists.")
            conn.close()
    except Exception as e:
        print(f"Error creating default admin: {e}")
    
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
