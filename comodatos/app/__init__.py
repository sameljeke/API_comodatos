from flask import Flask, jsonify, request
from flask_cors import CORS
from app.config import config
from app.extensions import db, migrate, jwt, cors, mail, limiter, swagger, ma  # <-- Agregar ma
from app.middleware.rate_limit import setup_rate_limiter
from app.middleware.logging import setup_logging
import logging
import os

def create_app(config_name='default'):
    """Factory de aplicación Flask"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    ma.init_app(app)  # <-- Inicializar Marshmallow
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    mail.init_app(app)
    limiter.init_app(app)
    swagger.init_app(app)
    
    # Configurar logging
    setup_logging(app)
    
    # Registrar blueprints
    from app.auth.routes import auth_bp
    from app.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    
    # Registrar manejadores de errores
    register_error_handlers(app)
    
    # Comandos CLI
    register_commands(app)
    
    return app

def register_error_handlers(app):
    """Registra manejadores de errores globales"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description if hasattr(error, 'description') else error)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Token inválido o expirado'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'error': 'Forbidden',
            'message': 'No tienes permisos para acceder a este recurso'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'Recurso no encontrado'
        }), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Has excedido el límite de solicitudes'
        }), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f'Server Error: {error}')
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Ha ocurrido un error interno del servidor'
        }), 500

def register_commands(app):
    """Registra comandos CLI"""
    @app.cli.command('init-db')
    def init_db():
        """Inicializa la base de datos con datos por defecto"""
        from app.models import Medida, EstadoInstrumento, Usuario
        
        db.create_all()
        
        # Crear medidas por defecto
        medidas = [
            ('4/4', 'Tamaño completo'),
            ('3/4', 'Tres cuartos'),
            ('1/2', 'Medio'),
            ('1/4', 'Cuarto'),
            ('1/8', 'Octavo'),
            ('13"', 'Trece pulgadas'),
            ('14"', 'Catorce pulgadas'),
            ('15"', 'Quince pulgadas'),
            ('N/A', 'No aplica'),
            ('OTRO', 'Otra medida')
        ]
        
        for nombre, descripcion in medidas:
            if not Medida.query.filter_by(nombre=nombre).first():
                medida = Medida(nombre=nombre, descripcion=descripcion)
                db.session.add(medida)
        
        # Crear estados por defecto
        estados = [
            ('disponible', 'Instrumento disponible para asignación'),
            ('asignado', 'Instrumento asignado en comodato'),
            ('no_operativo', 'Instrumento no operativo'),
            ('mantenimiento', 'En proceso de mantenimiento'),
            ('baja', 'Dado de baja del inventario')
        ]
        
        for nombre, descripcion in estados:
            if not EstadoInstrumento.query.filter_by(nombre=nombre).first():
                estado = EstadoInstrumento(nombre=nombre, descripcion=descripcion)
                db.session.add(estado)
        
        # Crear usuario admin por defecto
        if not Usuario.query.filter_by(email='admin@sistema.com').first():
            admin = Usuario(
                email='admin@sistema.com',
                rol='admin',
                is_active=True
            )
            admin.set_password('Admin123!')
            db.session.add(admin)
        
        db.session.commit()
        print('✅ Base de datos inicializada exitosamente')
        print('   Usuario admin: admin@sistema.com')
        print('   Contraseña: Admin123!')