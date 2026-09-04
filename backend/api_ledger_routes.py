"""
API Ledger Routes - Simple version with Viyonapay prefix filtering
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection

api_ledger_bp = Blueprint('api_ledger', __name__, url_prefix='/api/api-ledger')

@api_ledger_bp.route('/apis', methods=['GET'])
@jwt_required()
def get_apis():
    """Get list of APIs from service routing"""
    try:
        service_type = request.args.get('service_type', 'PAYIN')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get unique PG partners for the service type
        cursor.execute("""
            SELECT DISTINCT pg_partner
            FROM service_routing
            WHERE service_type = %s
            ORDER BY pg_partner
        """, (service_type,))
        
        apis = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Filter and rename APIs based on service type
        api_list = []
        for api in apis:
            pg_partner = api['pg_partner']
            
            if service_type == 'PAYIN':
                # Remove: Mudrape, vega, skrillpe, tourquest, rang, paytouchpayin, airpay, airpay_grosmart2, sabpaisa_grosmart, oxymoney_grosmart
                if pg_partner.lower() in ['mudrape', 'vega', 'skrillpe', 'tourquest', 'rang', 'paytouchpayin', 'airpay', 'airpay_grosmart2', 'sabpaisa_grosmart', 'oxymoney_grosmart']:
                    continue
                
                # Rename: viyonapay -> Viyonapay_Truaxis
                if pg_partner.lower() == 'viyonapay':
                    api_list.append({'id': 'Viyonapay_Truaxis', 'name': 'Viyonapay_Truaxis'})
                elif pg_partner.lower() == 'oxymoney_truaxis':
                    api_list.append({'id': 'Oxymoney_Truaxis', 'name': 'Oxymoney_Truaxis'})
                elif pg_partner.lower() == 'oxymoney_barringer':
                    api_list.append({'id': 'Oxymoney_Barringer', 'name': 'Oxymoney_Barringer'})
                elif pg_partner.lower() == 'rms_jss':
                    api_list.append({'id': 'RMS_JSS', 'name': 'RMS_JSS'})
                elif pg_partner.lower() == 'rms_hamster':
                    api_list.append({'id': 'RMS_HAMSTER', 'name': 'RMS_HAMSTER'})
                elif pg_partner.lower() == 'rms_megacart':
                    api_list.append({'id': 'RMS_MEGACART', 'name': 'RMS_MEGACART'})
                elif pg_partner.lower() == 'rms_coco':
                    api_list.append({'id': 'RMS_COCO', 'name': 'RMS_Coco'})
                elif pg_partner.lower() == 'upilnk_coco':
                    api_list.append({'id': 'UPILNK_COCO', 'name': 'Upilnk_Coco'})
                elif pg_partner.lower() == 'toucanpay_veltrix':
                    api_list.append({'id': 'TOUCANPAY_VELTRIX', 'name': 'ToucanPay_Veltrix'})
                elif pg_partner.lower() == 'airpay_coco':
                    api_list.append({'id': 'Airpay_Coco', 'name': 'Airpay_Coco'})
                elif pg_partner.lower() == 'payplus_veltrix':
                    api_list.append({'id': 'Payplus_Veltrix', 'name': 'Payplus_Veltrix'})
                elif pg_partner.lower() == 'hdfcpaytouch_barringer':
                    api_list.append({'id': 'HDFCPaytouch_Barringer', 'name': 'HDFCPaytouch_Barringer'})
                else:
                    api_list.append({'id': pg_partner, 'name': pg_partner})
                    
            elif service_type == 'PAYOUT':
                # Remove: paytouch, mudrape, paytouch2, paytouch3_trendora
                if pg_partner.lower() in ['paytouch', 'mudrape', 'paytouch2', 'paytouch3_trendora']:
                    continue
                
                # Rename: paytouch4_barringer -> Paytouch4_Barringer
                if pg_partner.lower() == 'paytouch4_barringer':
                    api_list.append({'id': 'Paytouch4_Barringer', 'name': 'Paytouch4_Barringer'})
                elif pg_partner.lower() == 'paytouch5_coco':
                    api_list.append({'id': 'Paytouch5_Coco', 'name': 'Paytouch5_Coco'})
                elif pg_partner.lower() == 'paytouch6_veltrix':
                    api_list.append({'id': 'Paytouch6_Veltrix', 'name': 'Paytouch6_Veltrix'})
                elif pg_partner.lower() == 'paystorepe_veltrix':
                    api_list.append({'id': 'PayStorePe_Veltrix', 'name': 'PayStorePe_Veltrix'})
                elif pg_partner.lower() == 'paystorepe_coco':
                    api_list.append({'id': 'PayStorePe_Coco', 'name': 'PayStorePe_Coco'})
                elif pg_partner.lower() == 'bridgmoney_coco':
                    api_list.append({'id': 'Bridgmoney_Coco', 'name': 'Bridgmoney_Coco'})
                else:
                    api_list.append({'id': pg_partner, 'name': pg_partner})
            else:
                # For other service types, keep as is
                api_list.append({'id': pg_partner, 'name': pg_partner})
        
        return jsonify({'success': True, 'apis': api_list}), 200
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_ledger_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_api_stats():
    """Get transaction statistics for a specific API"""
    try:
        api_name = request.args.get('api_name')
        service_type = request.args.get('service_type', 'PAYIN')
        period = request.args.get('period', 'today')
        
        if not api_name:
            return jsonify({'success': False, 'message': 'API name required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Determine date condition
        if period == 'today':
            date_condition = "DATE(created_at) = CURDATE()"
        elif period == 'yesterday':
            date_condition = "DATE(created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)"
        elif period == 'last_7_days':
            date_condition = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        elif period == 'last_30_days':
            date_condition = "DATE(created_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
        else:
            date_condition = "DATE(created_at) = CURDATE()"
        
        # Get statistics
        if service_type == 'PAYIN':
            table = 'payin_transactions'
            net_formula = 'amount - COALESCE(charge_amount, 0)'  # Merchant receives less
        else:
            table = 'payout_transactions'
            net_formula = 'amount + COALESCE(charge_amount, 0)'  # Wallet deduction is more
        
        # Map renamed API names back to database names
        db_api_name = api_name
        if api_name == 'Viyonapay_Truaxis':
            db_api_name = 'Viyonapay'
        elif api_name == 'Paytouch4_Barringer':
            db_api_name = 'paytouch4_barringer'
        elif api_name == 'Paytouch5_Coco':
            db_api_name = 'Paytouch5_Coco'
        elif api_name == 'Paytouch6_Veltrix':
            db_api_name = 'Paytouch6_Veltrix'
        elif api_name == 'PayStorePe_Veltrix':
            db_api_name = 'PayStorePe_Veltrix'
        elif api_name == 'PayStorePe_Coco':
            db_api_name = 'PayStorePe_Coco'
        elif api_name == 'Oxymoney_Truaxis':
            db_api_name = 'Oxymoney_Truaxis'
        elif api_name == 'Oxymoney_Barringer':
            db_api_name = 'Oxymoney_Barringer'
        elif api_name == 'RMS_COCO':
            db_api_name = 'RMS_COCO'
        elif api_name == 'UPILNK_COCO':
            db_api_name = 'UPILNK_COCO'
        elif api_name == 'Airpay_Coco':
            db_api_name = 'Airpay_Coco'
        elif api_name == 'Bridgmoney_Coco':
            db_api_name = 'Bridgmoney_Coco'
        elif api_name == 'Payplus_Veltrix':
            db_api_name = 'PAYPLUS_VELTRIX'
        
        # Build WHERE condition based on API name
        # Viyonapay: txn_id starts with 'viyonapay' or 'VY_TR'
        # VIYONAPAY_BARRINGER: txn_id starts with 'VY_BAR'
        # Oxymoney_Truaxis: txn_id starts with 'OXY_TRU_'
        # Oxymoney_Barringer: txn_id starts with 'OXY_BAR_'
        if db_api_name == 'Viyonapay':
            where_condition = f"(pg_partner = 'Viyonapay' AND (txn_id LIKE 'viyonapay%%' OR txn_id LIKE 'VY_TR%%')) AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'VIYONAPAY_BARRINGER':
            where_condition = f"(pg_partner = 'VIYONAPAY_BARRINGER' OR (pg_partner = 'Viyonapay' AND txn_id LIKE 'VY_BAR%%')) AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'Oxymoney_Truaxis':
            where_condition = f"(pg_partner = 'Oxymoney_Truaxis' OR txn_id LIKE 'OXY_TRU_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'Oxymoney_Barringer':
            where_condition = f"(pg_partner = 'Oxymoney_Barringer' OR txn_id LIKE 'OXY_BAR_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'UPILNK_COCO':
            where_condition = f"(pg_partner = 'Upilnk_Coco' OR txn_id LIKE 'UP_COC_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'Airpay_Coco':
            where_condition = f"(pg_partner = 'Airpay_Coco' OR txn_id LIKE 'AP_CO_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'Bridgmoney_Coco':
            where_condition = f"(pg_partner = 'Bridgmoney_Coco' OR txn_id LIKE 'BM_CO_TXN_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'PAYPLUS_VELTRIX':
            where_condition = f"(pg_partner = 'PAYPLUS_VELTRIX' OR txn_id LIKE 'PP_VEL_%%') AND {date_condition}"
            needs_parameter = False
        else:
            where_condition = f"pg_partner = %s AND {date_condition}"
            needs_parameter = True
        
        query = f"""
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count,
                COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 0) as total_amount,
                COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN ({net_formula}) ELSE 0 END), 0) as total_net_amount
            FROM {table}
            WHERE {where_condition}
        """
        
        if needs_parameter:
            cursor.execute(query, (db_api_name,))
        else:
            cursor.execute(query)
        
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_transactions': stats['total_transactions'],
                'success_count': stats['success_count'],
                'total_amount': float(stats['total_amount']),
                'total_net_amount': float(stats['total_net_amount'])
            }
        }), 200
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_ledger_bp.route('/merchant-wise', methods=['GET'])
@jwt_required()
def get_merchant_wise_stats():
    """Get merchant-wise statistics for a specific API"""
    try:
        api_name = request.args.get('api_name')
        service_type = request.args.get('service_type', 'PAYIN')
        period = request.args.get('period', 'today')
        
        if not api_name:
            return jsonify({'success': False, 'message': 'API name required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Determine date condition
        if period == 'today':
            date_condition = "DATE(t.created_at) = CURDATE()"
        elif period == 'yesterday':
            date_condition = "DATE(t.created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)"
        elif period == 'last_7_days':
            date_condition = "DATE(t.created_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
        elif period == 'last_30_days':
            date_condition = "DATE(t.created_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
        else:
            date_condition = "DATE(t.created_at) = CURDATE()"
        
        # Get merchant-wise statistics
        if service_type == 'PAYIN':
            table = 'payin_transactions'
            net_formula = 't.amount - COALESCE(t.charge_amount, 0)'
        else:
            table = 'payout_transactions'
            net_formula = 't.amount + COALESCE(t.charge_amount, 0)'
        
        # Map renamed API names back to database names
        db_api_name = api_name
        if api_name == 'Viyonapay_Truaxis':
            db_api_name = 'Viyonapay'
        elif api_name == 'Paytouch4_Barringer':
            db_api_name = 'paytouch4_barringer'
        elif api_name == 'Paytouch5_Coco':
            db_api_name = 'Paytouch5_Coco'
        elif api_name == 'Paytouch6_Veltrix':
            db_api_name = 'Paytouch6_Veltrix'
        elif api_name == 'PayStorePe_Veltrix':
            db_api_name = 'PayStorePe_Veltrix'
        elif api_name == 'PayStorePe_Coco':
            db_api_name = 'PayStorePe_Coco'
        elif api_name == 'Oxymoney_Truaxis':
            db_api_name = 'Oxymoney_Truaxis'
        elif api_name == 'Oxymoney_Barringer':
            db_api_name = 'Oxymoney_Barringer'
        elif api_name == 'RMS_COCO':
            db_api_name = 'RMS_COCO'
        elif api_name == 'UPILNK_COCO':
            db_api_name = 'UPILNK_COCO'
        elif api_name == 'Airpay_Coco':
            db_api_name = 'Airpay_Coco'
        elif api_name == 'Bridgmoney_Coco':
            db_api_name = 'Bridgmoney_Coco'
        elif api_name == 'Payplus_Veltrix':
            db_api_name = 'PAYPLUS_VELTRIX'
        
        # Build WHERE condition based on API name
        if db_api_name == 'Viyonapay':
            where_condition = f"(t.pg_partner = 'Viyonapay' AND (t.txn_id LIKE 'viyonapay%%' OR t.txn_id LIKE 'VY_TR%%')) AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'VIYONAPAY_BARRINGER':
            where_condition = f"(t.pg_partner = 'VIYONAPAY_BARRINGER' OR (t.pg_partner = 'Viyonapay' AND t.txn_id LIKE 'VY_BAR%%')) AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'Oxymoney_Truaxis':
            where_condition = f"(t.pg_partner = 'Oxymoney_Truaxis' OR t.txn_id LIKE 'OXY_TRU_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'Oxymoney_Barringer':
            where_condition = f"(t.pg_partner = 'Oxymoney_Barringer' OR t.txn_id LIKE 'OXY_BAR_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'UPILNK_COCO':
            where_condition = f"(t.pg_partner = 'Upilnk_Coco' OR t.txn_id LIKE 'UP_COC_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'Airpay_Coco':
            where_condition = f"(t.pg_partner = 'Airpay_Coco' OR t.txn_id LIKE 'AP_CO_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'Bridgmoney_Coco':
            where_condition = f"(t.pg_partner = 'Bridgmoney_Coco' OR t.txn_id LIKE 'BM_CO_TXN_%%') AND {date_condition}"
            needs_parameter = False
        elif db_api_name == 'PAYPLUS_VELTRIX':
            where_condition = f"(t.pg_partner = 'PAYPLUS_VELTRIX' OR t.txn_id LIKE 'PP_VEL_%%') AND {date_condition}"
            needs_parameter = False
        else:
            where_condition = f"t.pg_partner = %s AND {date_condition}"
            needs_parameter = True
        
        query = f"""
            SELECT 
                t.merchant_id,
                m.full_name as merchant_name,
                COUNT(*) as total_transactions,
                COUNT(CASE WHEN t.status = 'SUCCESS' THEN 1 END) as success_count,
                COALESCE(SUM(CASE WHEN t.status = 'SUCCESS' THEN t.amount ELSE 0 END), 0) as total_amount,
                COALESCE(SUM(CASE WHEN t.status = 'SUCCESS' THEN ({net_formula}) ELSE 0 END), 0) as total_net_amount
            FROM {table} t
            LEFT JOIN merchants m ON t.merchant_id = m.merchant_id
            WHERE {where_condition}
            GROUP BY t.merchant_id, m.full_name
            ORDER BY total_net_amount DESC
        """
        
        if needs_parameter:
            cursor.execute(query, (db_api_name,))
        else:
            cursor.execute(query)
        
        merchant_stats = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format response
        result = []
        for stat in merchant_stats:
            result.append({
                'merchant_id': stat['merchant_id'],
                'merchant_name': stat['merchant_name'] or stat['merchant_id'],
                'total_transactions': stat['total_transactions'],
                'success_count': stat['success_count'],
                'total_amount': float(stat['total_amount']),
                'total_net_amount': float(stat['total_net_amount'])
            })
        
        return jsonify({'success': True, 'merchant_stats': result}), 200
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500