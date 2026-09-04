from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection
from datetime import datetime

ip_security_bp = Blueprint('ip_security', __name__)

def get_real_ip():
    """Get the real IP address from request, handling proxies and load balancers"""
    xff = request.headers.get('X-Forwarded-For')
    xri = request.headers.get('X-Real-IP')
    cfip = request.headers.get('CF-Connecting-IP')
    
    if xff:
        return xff.split(',')[0].strip()
    if xri:
        return xri.strip()
    if cfip:
        return cfip.strip()
    
    return request.remote_addr

def log_ip_security_event(merchant_id, ip_address, endpoint, action, status):
    """Log IP security events"""
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ip_security_logs 
                    (merchant_id, ip_address, endpoint, action, status, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (merchant_id, ip_address, endpoint, action, status, 
                      request.headers.get('User-Agent', '')))
                conn.commit()
            conn.close()
    except Exception as e:
        print(f"Error logging IP security event: {e}")

def validate_merchant_ip(merchant_id, endpoint):
    """
    Validate if the request IP is whitelisted for the merchant.
    Returns (is_valid, message)
    """
    request_ip = get_real_ip()
    
    conn = get_db_connection()
    if not conn:
        return False, 'Database connection failed'
    
    try:
        with conn.cursor() as cursor:
            # Check if merchant has IP security enabled
            cursor.execute("""
                SELECT COUNT(*) as count FROM merchant_ip_security
                WHERE merchant_id = %s AND is_active = TRUE
            """, (merchant_id,))
            result = cursor.fetchone()
            
            # If no IPs configured, block all requests (security first)
            if result['count'] == 0:
                log_ip_security_event(merchant_id, request_ip, endpoint, 
                                     'NO_IP_CONFIGURED', 'BLOCKED')
                return False, 'No IP addresses configured for this merchant. Please contact admin to whitelist your IP.'
            
            # Check if request IP is whitelisted
            cursor.execute("""
                SELECT id FROM merchant_ip_security
                WHERE merchant_id = %s AND ip_address = %s AND is_active = TRUE
            """, (merchant_id, request_ip))
            ip_record = cursor.fetchone()
            
            if ip_record:
                log_ip_security_event(merchant_id, request_ip, endpoint, 
                                     'IP_VALIDATED', 'ALLOWED')
                return True, 'IP validated successfully'
            else:
                log_ip_security_event(merchant_id, request_ip, endpoint, 
                                     'IP_NOT_WHITELISTED', 'BLOCKED')
                return False, f'IP address {request_ip} is not whitelisted for this merchant'
    
    finally:
        conn.close()

# Admin Routes

@ip_security_bp.route('/api/admin/ip-security/merchants', methods=['GET'])
@jwt_required()
def get_merchants_for_ip_security():
    """Get list of merchants for IP security configuration"""
    try:
        admin_id = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        m.merchant_id,
                        m.full_name,
                        m.email,
                        m.mobile,
                        m.is_active,
                        COUNT(ips.id) as ip_count
                    FROM merchants m
                    LEFT JOIN merchant_ip_security ips ON m.merchant_id = ips.merchant_id AND ips.is_active = TRUE
                    GROUP BY m.merchant_id
                    ORDER BY m.full_name ASC
                """)
                merchants = cursor.fetchall()
                
                return jsonify({
                    'success': True,
                    'merchants': merchants
                }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        print(f"Error fetching merchants: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ip_security_bp.route('/api/admin/ip-security/<merchant_id>', methods=['GET'])
@jwt_required()
def get_merchant_ip_security(merchant_id):
    """Get IP security configuration for a specific merchant"""
    try:
        admin_id = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Get merchant details
                cursor.execute("""
                    SELECT merchant_id, full_name, email, mobile
                    FROM merchants WHERE merchant_id = %s
                """, (merchant_id,))
                merchant = cursor.fetchone()
                
                if not merchant:
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                # Get IP whitelist
                cursor.execute("""
                    SELECT 
                        id,
                        ip_address,
                        description,
                        is_active,
                        created_by,
                        created_at,
                        updated_at
                    FROM merchant_ip_security
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                """, (merchant_id,))
                ip_list = cursor.fetchall()
                
                # Get recent IP security logs
                cursor.execute("""
                    SELECT 
                        ip_address,
                        endpoint,
                        action,
                        status,
                        created_at
                    FROM ip_security_logs
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                    LIMIT 50
                """, (merchant_id,))
                logs = cursor.fetchall()
                
                # Convert timestamps to IST with proper formatting
                import pytz
                ist = pytz.timezone('Asia/Kolkata')
                utc = pytz.utc
                
                for ip in ip_list:
                    if ip.get('created_at'):
                        dt = ip['created_at']
                        # MySQL returns timestamps in IST, just localize them
                        if dt.tzinfo is None:
                            dt = ist.localize(dt)
                        ip['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    if ip.get('updated_at'):
                        dt = ip['updated_at']
                        if dt.tzinfo is None:
                            dt = ist.localize(dt)
                        ip['updated_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                
                for log in logs:
                    if log.get('created_at'):
                        dt = log['created_at']
                        if dt.tzinfo is None:
                            dt = ist.localize(dt)
                        log['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                
                return jsonify({
                    'success': True,
                    'merchant': merchant,
                    'ip_list': ip_list,
                    'logs': logs
                }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        print(f"Error fetching IP security: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ip_security_bp.route('/api/admin/ip-security/<merchant_id>/add', methods=['POST'])
@jwt_required()
def add_merchant_ip(merchant_id):
    """Add IP address to merchant whitelist"""
    try:
        admin_id = get_jwt_identity()
        data = request.get_json()
        
        ip_address = data.get('ip_address', '').strip()
        description = data.get('description', '').strip()
        
        if not ip_address:
            return jsonify({'success': False, 'message': 'IP address is required'}), 400
        
        # Basic IP validation
        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip_address):
            return jsonify({'success': False, 'message': 'Invalid IP address format'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Check if merchant exists
                cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                # Add IP to whitelist
                cursor.execute("""
                    INSERT INTO merchant_ip_security 
                    (merchant_id, ip_address, description, created_by)
                    VALUES (%s, %s, %s, %s)
                """, (merchant_id, ip_address, description, admin_id))
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'IP address added successfully'
                }), 201
        
        finally:
            conn.close()
    
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return jsonify({'success': False, 'message': 'IP address already exists for this merchant'}), 400
        print(f"Error adding IP: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ip_security_bp.route('/api/admin/ip-security/<merchant_id>/update/<int:ip_id>', methods=['PUT'])
@jwt_required()
def update_merchant_ip(merchant_id, ip_id):
    """Update IP address configuration"""
    try:
        admin_id = get_jwt_identity()
        data = request.get_json()
        
        description = data.get('description', '').strip()
        is_active = data.get('is_active', True)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE merchant_ip_security
                    SET description = %s, is_active = %s, updated_at = NOW()
                    WHERE id = %s AND merchant_id = %s
                """, (description, is_active, ip_id, merchant_id))
                conn.commit()
                
                if cursor.rowcount == 0:
                    return jsonify({'success': False, 'message': 'IP configuration not found'}), 404
                
                return jsonify({
                    'success': True,
                    'message': 'IP configuration updated successfully'
                }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        print(f"Error updating IP: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ip_security_bp.route('/api/admin/ip-security/<merchant_id>/delete/<int:ip_id>', methods=['DELETE'])
@jwt_required()
def delete_merchant_ip(merchant_id, ip_id):
    """Delete IP address from whitelist"""
    try:
        admin_id = get_jwt_identity()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM merchant_ip_security
                    WHERE id = %s AND merchant_id = %s
                """, (ip_id, merchant_id))
                conn.commit()
                
                if cursor.rowcount == 0:
                    return jsonify({'success': False, 'message': 'IP configuration not found'}), 404
                
                return jsonify({
                    'success': True,
                    'message': 'IP address removed successfully'
                }), 200
        
        finally:
            conn.close()
    
    except Exception as e:
        print(f"Error deleting IP: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ip_security_bp.route('/api/admin/ip-security/logs', methods=['GET'])
@jwt_required()
def get_ip_security_logs():
    """Get IP security logs with filters and pagination"""
    try:
        import pytz
        admin_id = get_jwt_identity()
        
        merchant_id = request.args.get('merchant_id')
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
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
                # Build count query
                count_query = """
                    SELECT COUNT(*) as total
                    FROM ip_security_logs l
                    WHERE 1=1
                """
                count_params = []
                
                if merchant_id:
                    count_query += " AND l.merchant_id = %s"
                    count_params.append(merchant_id)
                
                if status:
                    count_query += " AND l.status = %s"
                    count_params.append(status)
                
                # Get total count
                cursor.execute(count_query, count_params)
                total_records = cursor.fetchone()['total']
                
                # Build data query
                query = """
                    SELECT 
                        l.merchant_id,
                        m.full_name as merchant_name,
                        l.ip_address,
                        l.endpoint,
                        l.action,
                        l.status,
                        l.user_agent,
                        l.created_at
                    FROM ip_security_logs l
                    LEFT JOIN merchants m ON l.merchant_id = m.merchant_id
                    WHERE 1=1
                """
                params = []
                
                if merchant_id:
                    query += " AND l.merchant_id = %s"
                    params.append(merchant_id)
                
                if status:
                    query += " AND l.status = %s"
                    params.append(status)
                
                query += " ORDER BY l.created_at DESC LIMIT %s OFFSET %s"
                params.extend([per_page, offset])
                
                cursor.execute(query, params)
                logs = cursor.fetchall()
                
                # Convert timestamps to IST format for frontend
                # Note: MySQL returns timestamps in IST (timezone set to +05:30 in connection)
                # So the datetime objects are already in IST, just without timezone info
                import pytz
                ist = pytz.timezone('Asia/Kolkata')
                
                for log in logs:
                    if log.get('created_at'):
                        dt = log['created_at']
                        # The datetime from MySQL is already in IST, just localize it
                        if dt.tzinfo is None:
                            dt = ist.localize(dt)
                        # Format: YYYY-MM-DD HH:MM:SS (24-hour format for frontend parsing)
                        log['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                
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
        print(f"Error fetching logs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
