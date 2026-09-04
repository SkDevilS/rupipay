from flask import Blueprint, send_file, jsonify, request
import subprocess
import os
from datetime import datetime
from functools import wraps
import jwt
from config import Config

backup_bp = Blueprint('backup', __name__)

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
            
            # Check if user is admin
            if payload.get('role') != 'admin':
                return jsonify({'error': 'Admin access required'}), 403
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

@backup_bp.route('/api/admin/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Create a database backup and return download link"""
    try:
        # Create backup directory
        backup_dir = '/tmp/database_backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'{backup_dir}/moneyone_backup_{timestamp}.sql'
        
        # Get database credentials from config
        db_host = Config.DB_HOST
        db_name = Config.DB_NAME
        db_user = Config.DB_USER
        db_password = Config.DB_PASSWORD
        
        # Create mysqldump command
        if db_host == 'localhost' or '127.0.0.1' in db_host:
            # Local MySQL
            cmd = f'mysqldump -u {db_user} -p{db_password} {db_name} > {backup_file}'
        else:
            # Remote MySQL (RDS)
            cmd = f'mysqldump -h {db_host} -u {db_user} -p{db_password} {db_name} > {backup_file}'
        
        # Execute backup
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Backup failed',
                'details': result.stderr
            }), 500
        
        # Compress backup
        subprocess.run(f'gzip {backup_file}', shell=True)
        compressed_file = f'{backup_file}.gz'
        
        # Get file size
        file_size = os.path.getsize(compressed_file)
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        return jsonify({
            'success': True,
            'message': 'Backup created successfully',
            'filename': os.path.basename(compressed_file),
            'size_mb': file_size_mb,
            'download_url': f'/api/admin/backup/download/{os.path.basename(compressed_file)}'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to create backup',
            'details': str(e)
        }), 500

@backup_bp.route('/api/admin/backup/download/<filename>', methods=['GET'])
@admin_required
def download_backup(filename):
    """Download a backup file"""
    try:
        backup_dir = '/tmp/database_backups'
        file_path = os.path.join(backup_dir, filename)
        
        # Security check - ensure filename doesn't contain path traversal
        if '..' in filename or '/' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        # Send file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/gzip'
        )
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to download backup',
            'details': str(e)
        }), 500

@backup_bp.route('/api/admin/backup/list', methods=['GET'])
@admin_required
def list_backups():
    """List all available backups"""
    try:
        backup_dir = '/tmp/database_backups'
        
        if not os.path.exists(backup_dir):
            return jsonify({'backups': []}), 200
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.sql.gz'):
                file_path = os.path.join(backup_dir, filename)
                file_size = os.path.getsize(file_path)
                file_size_mb = round(file_size / (1024 * 1024), 2)
                created_time = os.path.getctime(file_path)
                
                backups.append({
                    'filename': filename,
                    'size_mb': file_size_mb,
                    'created_at': datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'download_url': f'/api/admin/backup/download/{filename}'
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'backups': backups}), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to list backups',
            'details': str(e)
        }), 500
