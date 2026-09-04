import logging
import os
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

# Create logs directory
os.makedirs('/var/log/flask', exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing"""
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if available
        if hasattr(record, 'merchant_id'):
            log_data['merchant_id'] = record.merchant_id
        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        if hasattr(record, 'duration'):
            log_data['duration_ms'] = record.duration
            
        return json.dumps(log_data)

def setup_logging(app):
    """Setup application logging"""
    
    # Application log handler
    app_handler = RotatingFileHandler(
        '/var/log/flask/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(JSONFormatter())
    
    # Error log handler
    error_handler = RotatingFileHandler(
        '/var/log/flask/error.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    
    # Add handlers to app logger
    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.INFO)
    
    return app.logger
