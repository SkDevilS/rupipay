import logging
from logging.handlers import RotatingFileHandler
import os

def setup_app_logging(app):
    """Setup enhanced logging for Flask app"""
    
    # Create dozzle_logs directory
    log_dir = os.path.join(os.path.dirname(__file__), 'dozzle_logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Clear existing handlers
    app.logger.handlers.clear()
    app.logger.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Main log file (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10485760,
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    
    # Error log file
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10485760,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    app.logger.addHandler(error_handler)
    
    # Console output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)
    
    # Log startup
    app.logger.info("="*50)
    app.logger.info("MoneyOne Backend Started")
    app.logger.info("="*50)
    
    return app

def log_request(app):
    """Add request/response logging"""
    
    @app.before_request
    def before_request():
        from flask import request
        app.logger.info(f"→ {request.method} {request.path} | IP: {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        from flask import request
        app.logger.info(f"← {request.method} {request.path} | Status: {response.status_code}")
        return response