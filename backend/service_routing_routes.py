"""
Service Routing API Routes
Manages payment gateway routing for payin/payout
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection

routing_bp = Blueprint('routing', __name__, url_prefix='/api/routing')

@routing_bp.route('/services', methods=['GET'])
@jwt_required()
def get_service_routing():
    """Get all service routing configurations (admin only)"""
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
                
                # Get all routing configurations
                cursor.execute("""
                    SELECT sr.*, m.full_name as merchant_name
                    FROM service_routing sr
                    LEFT JOIN merchants m ON sr.merchant_id = m.merchant_id
                    ORDER BY sr.service_type, sr.routing_type, sr.priority
                """)
                
                routes = cursor.fetchall()
                
                # Format dates
                for route in routes:
                    if route.get('created_at'):
                        route['created_at'] = route['created_at'].isoformat()
                    if route.get('updated_at'):
                        route['updated_at'] = route['updated_at'].isoformat()
                
                return jsonify({
                    'success': True,
                    'routes': routes
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get service routing error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@routing_bp.route('/services', methods=['POST'])
@jwt_required()
def create_service_routing():
    """Create service routing configuration (admin only)"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        merchant_id = data.get('merchantId')  # Optional - null for all users
        service_type = data.get('serviceType')  # PAYIN or PAYOUT
        routing_type = data.get('routingType')  # SINGLE_USER or ALL_USERS
        pg_partner = data.get('pgPartner')  # PayU, Mudrape, etc.
        priority = data.get('priority', 1)
        
        # Validate required fields
        if not all([service_type, routing_type, pg_partner]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Validate routing type
        if routing_type == 'SINGLE_USER' and not merchant_id:
            return jsonify({'success': False, 'message': 'Merchant ID required for single user routing'}), 400
        
        if routing_type == 'ALL_USERS' and merchant_id:
            return jsonify({'success': False, 'message': 'Merchant ID should be null for all users routing'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify admin
                cursor.execute("SELECT admin_id FROM admin_users WHERE admin_id = %s", (current_admin,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Unauthorized'}), 403
                
                # If merchant_id provided, verify merchant exists
                if merchant_id:
                    cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = %s", (merchant_id,))
                    if not cursor.fetchone():
                        return jsonify({'success': False, 'message': 'Merchant not found'}), 404
                
                # IMPORTANT: For both PAYIN and PAYOUT, deactivate all other gateways for this merchant/routing_type
                # A merchant can only use ONE payment gateway at a time per service type
                if routing_type == 'SINGLE_USER' and merchant_id:
                    # Deactivate all other gateways for this specific merchant and service type
                    cursor.execute("""
                        UPDATE service_routing
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE merchant_id = %s 
                        AND service_type = %s
                        AND routing_type = 'SINGLE_USER'
                        AND pg_partner != %s
                    """, (merchant_id, service_type, pg_partner))
                elif routing_type == 'ALL_USERS':
                    # Deactivate all other gateways for ALL_USERS and service type
                    cursor.execute("""
                        UPDATE service_routing
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE merchant_id IS NULL
                        AND service_type = %s
                        AND routing_type = 'ALL_USERS'
                        AND pg_partner != %s
                    """, (service_type, pg_partner))
                
                # Insert or update routing configuration
                cursor.execute("""
                    INSERT INTO service_routing (
                        merchant_id, service_type, routing_type, pg_partner, priority, is_active
                    ) VALUES (%s, %s, %s, %s, %s, TRUE)
                    ON DUPLICATE KEY UPDATE
                    is_active = TRUE,
                    priority = VALUES(priority),
                    updated_at = CURRENT_TIMESTAMP
                """, (merchant_id, service_type, routing_type, pg_partner, priority))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Service routing created successfully. Other gateways for this merchant have been deactivated.'
                }), 201
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Create service routing error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@routing_bp.route('/services/<int:route_id>', methods=['PUT'])
@jwt_required()
def update_service_routing(route_id):
    """Update service routing configuration (admin only)"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        is_active = data.get('isActive')
        priority = data.get('priority')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # Verify admin
                cursor.execute("SELECT admin_id FROM admin_users WHERE admin_id = %s", (current_admin,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Unauthorized'}), 403
                
                # Get route details
                cursor.execute("""
                    SELECT id, merchant_id, service_type, routing_type, pg_partner 
                    FROM service_routing 
                    WHERE id = %s
                """, (route_id,))
                route = cursor.fetchone()
                
                if not route:
                    return jsonify({'success': False, 'message': 'Route not found'}), 404
                
                # If activating a gateway, deactivate all other gateways for this merchant and service type
                if is_active is True:
                    if route['routing_type'] == 'SINGLE_USER' and route['merchant_id']:
                        # Deactivate all other gateways for this specific merchant and service type
                        cursor.execute("""
                            UPDATE service_routing
                            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                            WHERE merchant_id = %s 
                            AND service_type = %s
                            AND routing_type = 'SINGLE_USER'
                            AND id != %s
                        """, (route['merchant_id'], route['service_type'], route_id))
                    elif route['routing_type'] == 'ALL_USERS':
                        # Deactivate all other gateways for ALL_USERS and service type
                        cursor.execute("""
                            UPDATE service_routing
                            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                            WHERE merchant_id IS NULL
                            AND service_type = %s
                            AND routing_type = 'ALL_USERS'
                            AND id != %s
                        """, (route['service_type'], route_id))
                
                # Update route
                update_fields = []
                params = []
                
                if is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(is_active)
                
                if priority is not None:
                    update_fields.append("priority = %s")
                    params.append(priority)
                
                if not update_fields:
                    return jsonify({'success': False, 'message': 'No fields to update'}), 400
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(route_id)
                
                query = f"UPDATE service_routing SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(query, params)
                conn.commit()
                
                message = 'Service routing updated successfully'
                if is_active is True:
                    message += '. Other gateways for this merchant have been deactivated.'
                
                return jsonify({
                    'success': True,
                    'message': message
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Update service routing error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@routing_bp.route('/services/<int:route_id>', methods=['DELETE'])
@jwt_required()
def delete_service_routing(route_id):
    """Delete service routing configuration (admin only)"""
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
                
                # Delete route
                cursor.execute("DELETE FROM service_routing WHERE id = %s", (route_id,))
                
                if cursor.rowcount == 0:
                    return jsonify({'success': False, 'message': 'Route not found'}), 404
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Service routing deleted successfully'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Delete service routing error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@routing_bp.route('/merchants', methods=['GET'])
@jwt_required()
def get_merchants_for_routing():
    """Get list of merchants for routing configuration (admin only)"""
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
                
                # Get active merchants
                cursor.execute("""
                    SELECT merchant_id, full_name, email, merchant_type
                    FROM merchants
                    WHERE is_active = TRUE
                    ORDER BY full_name
                """)
                
                merchants = cursor.fetchall()
                
                return jsonify({
                    'success': True,
                    'merchants': merchants
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get merchants for routing error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@routing_bp.route('/pg-partners', methods=['GET'])
def get_pg_partners():
    """Get list of available payment gateway partners"""
    try:
        # List of supported PG partners - Only Server Down
        pg_partners = [
            {
                'id': 'PayU',
                'name': 'SERVER DOWN',
                'supports': ['PAYIN', 'PAYOUT'],
                'status': 'inactive'
            },
            {
                'id': 'PAYTOUCH5_COCO',
                'name': 'Paytouch5_Coco',
                'supports': ['PAYOUT'],
                'status': 'active'
            },
            {
                'id': 'PAYTOUCH6_VELTRIX',
                'name': 'Paytouch6_Veltrix',
                'supports': ['PAYOUT'],
                'status': 'active'
            },
            {
                'id': 'PAYSTOREPE_VELTRIX',
                'name': 'PayStorePe_Veltrix',
                'supports': ['PAYOUT'],
                'status': 'active'
            },
            {
                'id': 'PAYSTOREPE_COCO',
                'name': 'PayStorePe_Coco',
                'supports': ['PAYOUT'],
                'status': 'active'
            },
            {
                'id': 'BRIDGMONEY_COCO',
                'name': 'Bridgmoney_Coco',
                'supports': ['PAYOUT'],
                'status': 'active'
            },
            {
                'id': 'RMS_COCO',
                'name': 'RMS_Coco',
                'supports': ['PAYIN'],
                'status': 'active'
            },

            {
                'id': 'UPILNK_COCO',
                'name': 'Upilnk_Coco',
                'supports': ['PAYIN'],
                'status': 'active'
            },
            {
                'id': 'TOUCANPAY_VELTRIX',
                'name': 'ToucanPay_Veltrix',
                'supports': ['PAYIN'],
                'status': 'active'
            },
            {
                'id': 'Airpay_Coco',
                'name': 'Airpay_Coco',
                'supports': ['PAYIN'],
                'status': 'active'
            },
            {
                'id': 'PAYPLUS_VELTRIX',
                'name': 'Payplus_Veltrix',
                'supports': ['PAYIN'],
                'status': 'active'
            }
        ]
        
        return jsonify({
            'success': True,
            'partners': pg_partners
        }), 200
        
    except Exception as e:
        print(f"Get PG partners error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@routing_bp.route('/admin/payout-gateways', methods=['GET'])
@jwt_required()
def get_admin_payout_gateways():
    """Get available payout gateways for admin personal payout (hardcoded list)"""
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
                
                # HARDCODED list of PAYOUT gateways only (no payin APIs)
                # This ensures only payout services appear in admin personal payout
                payout_gateways = [
                    {'id': 'PAYTOUCH5_COCO', 'name': 'Paytouch5_Coco', 'priority': 1},
                    {'id': 'PAYTOUCH6_VELTRIX', 'name': 'Paytouch6_Veltrix', 'priority': 1},
                    {'id': 'PAYSTOREPE_VELTRIX', 'name': 'PayStorePe_Veltrix', 'priority': 1},
                    {'id': 'PAYSTOREPE_COCO', 'name': 'PayStorePe_Coco', 'priority': 1},
                    {'id': 'BRIDGMONEY_COCO', 'name': 'Bridgmoney_Coco', 'priority': 1},
                    {'id': 'PAYU', 'name': 'PayU (SERVER DOWN)', 'priority': 3}
                ]
                
                return jsonify({
                    'success': True,
                    'gateways': payout_gateways
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get admin payout gateways error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@routing_bp.route('/merchant/<merchant_id>/gateway', methods=['GET'])
@jwt_required()
def get_merchant_gateway(merchant_id):
    """Get active payment gateway for a merchant"""
    try:
        service_type = request.args.get('service_type', 'PAYIN')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                # First check for single user routing
                cursor.execute("""
                    SELECT pg_partner FROM service_routing
                    WHERE merchant_id = %s 
                    AND service_type = %s 
                    AND routing_type = 'SINGLE_USER'
                    AND is_active = TRUE
                    ORDER BY priority ASC
                    LIMIT 1
                """, (merchant_id, service_type))
                
                route = cursor.fetchone()
                
                if route:
                    return jsonify({
                        'success': True,
                        'gateway': route['pg_partner']
                    }), 200
                
                # If no single user routing, check for all users routing
                cursor.execute("""
                    SELECT pg_partner FROM service_routing
                    WHERE merchant_id IS NULL
                    AND service_type = %s 
                    AND routing_type = 'ALL_USERS'
                    AND is_active = TRUE
                    ORDER BY priority ASC
                    LIMIT 1
                """, (service_type,))
                
                route = cursor.fetchone()
                
                if route:
                    return jsonify({
                        'success': True,
                        'gateway': route['pg_partner']
                    }), 200
                
                # Default to PayU if no routing configured
                return jsonify({
                    'success': True,
                    'gateway': 'PayU'
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Get merchant gateway error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500