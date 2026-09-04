from flask import Blueprint, jsonify
import psycopg2
from config import Config
import time

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancer"""
    health_status = {
        'status': 'healthy',
        'service': 'moneyone-backend',
        'timestamp': time.time(),
        'checks': {}
    }
    
    try:
        # Check database connection
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = f'error: {str(e)}'
        return jsonify(health_status), 503
    
    return jsonify(health_status), 200

@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check for Kubernetes/container orchestration"""
    return jsonify({'status': 'ready'}), 200
