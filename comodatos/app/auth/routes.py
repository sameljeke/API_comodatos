from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity
)
from app.extensions import db
from app.models import Usuario, Representante, VerificacionEmail, RecuperacionPass
from app.schemas import usuario_schema
from app.utils.validators import Validators
from app.auth.utils import create_tokens
import secrets
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registro de nuevo usuario"""
    try:
        data = request.get_json()
        
        # Validar email
        try:
            email = Validators.validate_email(data['email'])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(email=email).first():
            return jsonify({'error': 'El email ya está registrado'}), 409
        
        # Verificar cédula
        if Representante.query.filter_by(cedula=data['cedula']).first():
            return jsonify({'error': 'La cédula ya está registrada'}), 409
        
        # Crear usuario
        usuario = Usuario(
            email=email,
            rol='representante',
            is_active=True  # Activado automáticamente para desarrollo
        )
        usuario.set_password(data['password'])
        
        # Crear representante
        representante = Representante(
            nombre=data['nombre'],
            apellido=data['apellido'],
            cedula=data['cedula'],
            telefono=data.get('telefono'),
            direccion=data.get('direccion')
        )
        
        usuario.representante = representante
        db.session.add(usuario)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuario registrado exitosamente',
            'user': usuario.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    """Inicio de sesión"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email y password requeridos'}), 400
    
    usuario = Usuario.query.filter_by(email=data['email']).first()
    
    if not usuario or not usuario.check_password(data['password']):
        return jsonify({'error': 'Credenciales inválidas'}), 401
    
    if not usuario.is_active:
        return jsonify({'error': 'Cuenta inactiva'}), 403
    
    # Actualizar último login
    usuario.fecha_ultimo_login = datetime.utcnow()
    db.session.commit()
    
    # Crear tokens
    tokens = create_tokens(usuario)
    
    return jsonify(tokens), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Obtener información del usuario actual"""
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(current_user_id)
    
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    return jsonify(usuario.to_dict()), 200
