# app/middleware/logging.py
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from flask import request  # <-- ¡ESTA ES LA LÍNEA QUE FALTA!

def setup_logging(app):
    """Configura el sistema de logging"""
    
    if not app.debug:
        # Crear directorio de logs si no existe
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Handler para archivo principal
        file_handler = RotatingFileHandler(
            f'{log_dir}/comodatos.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Handler para errores
        error_handler = RotatingFileHandler(
            f'{log_dir}/errors.log',
            maxBytes=10485760,
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
        ))
        
        # Handler para auditoría
        audit_handler = RotatingFileHandler(
            f'{log_dir}/audit.log',
            maxBytes=10485760,
            backupCount=10
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # Configurar logger de aplicación
        app.logger.addHandler(file_handler)
        app.logger.addHandler(error_handler)
        app.logger.setLevel(logging.INFO)
        
        # Logger de auditoría
        audit_logger = logging.getLogger('audit')
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False
        
        # Configurar logger de SQLAlchemy
        sql_logger = logging.getLogger('sqlalchemy.engine')
        sql_logger.addHandler(file_handler)
        sql_logger.setLevel(logging.WARNING)
        
        # Middleware para logging de requests
        @app.before_request
        def before_request_logging():
            if request.endpoint and 'static' not in request.endpoint:
                app.logger.info(f'Request: {request.method} {request.path} - IP: {request.remote_addr}')
        
        @app.after_request
        def after_request_logging(response):
            if request.endpoint and 'static' not in request.endpoint:
                # Obtener usuario actual si está autenticado
                user_id = 'anonymous'
                try:
                    from flask_jwt_extended import get_jwt_identity
                    user_id = get_jwt_identity() or 'anonymous'
                except:
                    pass
                
                audit_logger.info(
                    f'User: {user_id} - '
                    f'Method: {request.method} - '
                    f'Path: {request.path} - '
                    f'Status: {response.status_code}'
                )
            return response
