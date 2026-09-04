"""
Bulk Bank Upload Routes for Admin
Handles CSV template download, upload preview, and bulk bank addition
"""

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
import csv
import io
import bcrypt
from database import get_db_connection

bulk_bank_bp = Blueprint('bulk_bank', __name__)


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


@bulk_bank_bp.route('/api/admin/banks/bulk/template', methods=['GET'])
@jwt_required()
def download_bank_template():
    """Download CSV template for bulk bank upload"""
    try:
        # Create CSV template
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Bank Name',
            'Account Number',
            'IFSC Code',
            'Branch Name',
            'Account Holder Name'
        ])
        
        # Write sample row
        writer.writerow([
            'State Bank of India',
            '1234567890',
            'SBIN0001234',
            'Main Branch',
            'John Doe'
        ])
        
        # Convert to bytes
        output.seek(0)
        byte_output = io.BytesIO()
        byte_output.write(output.getvalue().encode('utf-8'))
        byte_output.seek(0)
        
        return send_file(
            byte_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='bank_upload_template.csv'
        )
        
    except Exception as e:
        print(f"Download template error: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate template'}), 500


@bulk_bank_bp.route('/api/admin/banks/bulk/preview', methods=['POST'])
@jwt_required()
def preview_bulk_banks():
    """Preview banks from uploaded CSV"""
    try:
        current_admin = get_jwt_identity()
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'message': 'Only CSV files are allowed'}), 400
        
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        banks = []
        errors = []
        row_number = 1  # Start from 1 (header is row 0)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        try:
            with conn.cursor() as cursor:
                for row in csv_reader:
                    row_number += 1
                    
                    # Validate required fields
                    bank_name = row.get('Bank Name', '').strip()
                    account_number = row.get('Account Number', '').strip()
                    ifsc_code = row.get('IFSC Code', '').strip().upper()
                    branch_name = row.get('Branch Name', '').strip()
                    account_holder_name = row.get('Account Holder Name', '').strip()
                    
                    # Validation
                    row_errors = []
                    
                    if not bank_name:
                        row_errors.append('Bank Name is required')
                    
                    if not account_number:
                        row_errors.append('Account Number is required')
                    elif not account_number.isdigit():
                        row_errors.append('Account Number must contain only digits')
                    
                    if not ifsc_code:
                        row_errors.append('IFSC Code is required')
                    elif len(ifsc_code) != 11:
                        row_errors.append('IFSC Code must be 11 characters')
                    
                    if not branch_name:
                        row_errors.append('Branch Name is required')
                    
                    if not account_holder_name:
                        row_errors.append('Account Holder Name is required')
                    
                    # Check for duplicate in database
                    if account_number:
                        cursor.execute("""
                            SELECT id FROM admin_banks 
                            WHERE admin_id = %s AND account_number = %s
                        """, (current_admin, account_number))
                        
                        if cursor.fetchone():
                            row_errors.append('Account already exists in database')
                    
                    # Check for duplicate in current upload
                    if account_number and any(b['accountNumber'] == account_number for b in banks):
                        row_errors.append('Duplicate account in CSV')
                    
                    if row_errors:
                        errors.append({
                            'row': row_number,
                            'errors': row_errors,
                            'data': row
                        })
                    else:
                        banks.append({
                            'bankName': bank_name,
                            'accountNumber': account_number,
                            'ifscCode': ifsc_code,
                            'branchName': branch_name,
                            'accountHolderName': account_holder_name
                        })
        
        finally:
            conn.close()
        
        return jsonify({
            'success': True,
            'banks': banks,
            'errors': errors,
            'totalRows': row_number - 1,
            'validRows': len(banks),
            'errorRows': len(errors)
        }), 200
        
    except Exception as e:
        print(f"Preview bulk banks error: {e}")
        return jsonify({'success': False, 'message': f'Failed to process CSV: {str(e)}'}), 500


@bulk_bank_bp.route('/api/admin/banks/bulk/add', methods=['POST'])
@jwt_required()
def bulk_add_banks():
    """Add multiple banks after TPIN verification"""
    try:
        current_admin = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('banks') or not isinstance(data['banks'], list):
            return jsonify({'success': False, 'message': 'Banks array is required'}), 400
        
        if not data.get('tpin'):
            return jsonify({'success': False, 'message': 'TPIN is required'}), 400
        
        if len(data['tpin']) != 6:
            return jsonify({'success': False, 'message': 'TPIN must be 6 digits'}), 400
        
        banks = data['banks']
        tpin = data['tpin']
        
        if len(banks) == 0:
            return jsonify({'success': False, 'message': 'No banks to add'}), 400
        
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
                
                if not bcrypt.checkpw(tpin.encode('utf-8'), admin['pin_hash'].encode('utf-8')):
                    return jsonify({'success': False, 'message': 'Invalid TPIN'}), 401
                
                # Hash TPIN for bank records
                tpin_hash = bcrypt.hashpw(tpin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                added_count = 0
                failed_banks = []
                
                # Insert each bank
                for bank in banks:
                    try:
                        # Validate bank data
                        required_fields = ['bankName', 'accountNumber', 'ifscCode', 
                                         'branchName', 'accountHolderName']
                        
                        if not all(bank.get(field) for field in required_fields):
                            failed_banks.append({
                                'bank': bank,
                                'reason': 'Missing required fields'
                            })
                            continue
                        
                        # Check for duplicate
                        cursor.execute("""
                            SELECT id FROM admin_banks 
                            WHERE admin_id = %s AND account_number = %s
                        """, (current_admin, bank['accountNumber']))
                        
                        if cursor.fetchone():
                            failed_banks.append({
                                'bank': bank,
                                'reason': 'Account already exists'
                            })
                            continue
                        
                        # Insert bank
                        cursor.execute("""
                            INSERT INTO admin_banks 
                            (admin_id, bank_name, account_number, ifsc_code, branch_name, 
                             account_holder_name, tpin_hash, is_active)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                        """, (current_admin, bank['bankName'], bank['accountNumber'], 
                              bank['ifscCode'], bank['branchName'], 
                              bank['accountHolderName'], tpin_hash))
                        
                        added_count += 1
                        
                    except Exception as e:
                        print(f"Error adding bank {bank.get('accountNumber')}: {e}")
                        failed_banks.append({
                            'bank': bank,
                            'reason': str(e)
                        })
                
                conn.commit()
                
                # Log activity
                log_activity(
                    current_admin, 
                    f'Bulk bank upload: {added_count} banks added, {len(failed_banks)} failed', 
                    'SUCCESS' if added_count > 0 else 'FAILED'
                )
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully added {added_count} bank(s)',
                    'addedCount': added_count,
                    'failedCount': len(failed_banks),
                    'failedBanks': failed_banks
                }), 200
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Bulk add banks error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
