"""
Bridgmoney Coco Beneficiary Management Routes
Handles create, list, get, update, archive, and reactivate operations for tenant-scoped payout targets (Bank & UPI).
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bridgmoney_coco_service import bridgmoney_coco_service

bridgmoney_coco_beneficiary_bp = Blueprint(
    'bridgmoney_coco_beneficiaries',
    __name__,
    url_prefix='/api/bridgmoney-coco/beneficiaries'
)

@bridgmoney_coco_beneficiary_bp.route('', methods=['POST'])
@jwt_required()
def add_beneficiary_route():
    """
    POST /api/bridgmoney-coco/beneficiaries
    Add a beneficiary by providing name, phone number, and payment details.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'JSON payload required'}), 400

        name = data.get('name')
        phone_number = data.get('phoneNumber') or data.get('phone_number') or data.get('mobile')
        email = data.get('email')

        if not name or not phone_number:
            return jsonify({'success': False, 'message': 'name and phoneNumber are required'}), 400

        vpa = data.get('vpa')
        account_number = data.get('accountNumber') or data.get('account_number')
        ifsc = data.get('ifsc') or data.get('ifsc_code')

        if not vpa and not (account_number and ifsc):
            return jsonify({
                'success': False,
                'message': 'Send exactly one of: Bank target (accountNumber + ifsc) or UPI target (vpa)'
            }), 400

        if vpa and (account_number or ifsc):
            return jsonify({
                'success': False,
                'message': 'Do not send accountNumber or ifsc when vpa is provided'
            }), 400

        result = bridgmoney_coco_service.add_beneficiary(
            name=name,
            phone_number=phone_number,
            account_number=account_number,
            ifsc=ifsc,
            vpa=vpa,
            email=email
        )

        status_code = result.get('status_code', 400)
        if result.get('success'):
            return jsonify(result), status_code
        else:
            return jsonify(result), status_code
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bridgmoney_coco_beneficiary_bp.route('', methods=['GET'])
@jwt_required()
def list_beneficiaries_route():
    """
    GET /api/bridgmoney-coco/beneficiaries
    List tenant-scoped beneficiaries.
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        status = request.args.get('status', None)

        result = bridgmoney_coco_service.list_beneficiaries(page=page, limit=limit, status=status)
        status_code = 200 if result.get('success') else result.get('status_code', 400)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bridgmoney_coco_beneficiary_bp.route('/<beneficiary_id>', methods=['GET'])
@jwt_required()
def get_beneficiary_route(beneficiary_id):
    """
    GET /api/bridgmoney-coco/beneficiaries/<beneficiary_id>
    Get details of a specific beneficiary.
    """
    try:
        result = bridgmoney_coco_service.get_beneficiary(beneficiary_id)
        status_code = 200 if result.get('success') else result.get('status_code', 404)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bridgmoney_coco_beneficiary_bp.route('/<beneficiary_id>', methods=['PATCH', 'PUT'])
@jwt_required()
def update_beneficiary_route(beneficiary_id):
    """
    PATCH /api/bridgmoney-coco/beneficiaries/<beneficiary_id>
    Update beneficiary details.
    """
    try:
        data = request.get_json() or {}
        result = bridgmoney_coco_service.update_beneficiary(
            beneficiary_id=beneficiary_id,
            name=data.get('name'),
            phone_number=data.get('phoneNumber') or data.get('phone_number'),
            email=data.get('email'),
            status=data.get('status')
        )
        status_code = 200 if result.get('success') else result.get('status_code', 400)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bridgmoney_coco_beneficiary_bp.route('/<beneficiary_id>', methods=['DELETE'])
@jwt_required()
def archive_beneficiary_route(beneficiary_id):
    """
    DELETE /api/bridgmoney-coco/beneficiaries/<beneficiary_id>
    Archive a beneficiary.
    """
    try:
        result = bridgmoney_coco_service.archive_beneficiary(beneficiary_id)
        status_code = 200 if result.get('success') else result.get('status_code', 400)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bridgmoney_coco_beneficiary_bp.route('/<beneficiary_id>/reactivate', methods=['POST'])
@jwt_required()
def reactivate_beneficiary_route(beneficiary_id):
    """
    POST /api/bridgmoney-coco/beneficiaries/<beneficiary_id>/reactivate
    Reactivate an archived beneficiary.
    """
    try:
        result = bridgmoney_coco_service.reactivate_beneficiary(beneficiary_id)
        status_code = 200 if result.get('success') else result.get('status_code', 400)
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
