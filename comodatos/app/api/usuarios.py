from flask import request, jsonify
from app.extensions import db
from app.models import Usuario
from app.schemas import usuario_schema, usuarios_schema
from app.auth.utils import require_roles
from app.api import api_bp
from flask_jwt_extended import jwt_required

@api_bp.route('/usuarios', methods=['GET'])
@jwt_required()
@require_roles('admin')
def get_usuarios():
    """
    Obtener todos los usuarios
    ---
    tags:
      - Usuarios
    security:
      - BearerAuth: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
      - name: rol
        in: query
        type: string
        enum: [admin, representante, invitado]
    responses:
      200:
        description: Lista de usuarios
      403:
        description: No autorizado
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    rol = request.args.get('rol')
    
    query = Usuario.query
    
    if rol:
        query = query.filter_by(rol=rol)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'usuarios': usuarios_schema.dump(pagination.items),
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@api_bp.route('/usuarios/<int:id>', methods=['GET'])
@jwt_required()
@require_roles('admin')
def get_usuario(id):
    """
    Obtener usuario por ID
    ---
    tags:
      - Usuarios
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Usuario encontrado
      404:
        description: Usuario no encontrado
    """
    usuario = Usuario.query.get_or_404(id)
    return jsonify(usuario_schema.dump(usuario)), 200

@api_bp.route('/usuarios/<int:id>', methods=['PUT'])
@jwt_required()
@require_roles('admin')
def update_usuario(id):
    """
    Actualizar usuario
    ---
    tags:
      - Usuarios
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            rol:
              type: string
              enum: [admin, representante, invitado]
            is_active:
              type: boolean
    responses:
      200:
        description: Usuario actualizado
      404:
        description: Usuario no encontrado
    """
    usuario = Usuario.query.get_or_404(id)
    data = request.get_json()
    
    if 'rol' in data:
        usuario.rol = data['rol']
    
    if 'is_active' in data:
        usuario.is_active = data['is_active']
    
    db.session.commit()
    
    return jsonify(usuario_schema.dump(usuario)), 200

@api_bp.route('/usuarios/<int:id>/deactivate', methods=['POST'])
@jwt_required()
@require_roles('admin')
def deactivate_usuario(id):
    """
    Desactivar usuario
    ---
    tags:
      - Usuarios
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Usuario desactivado
      404:
        description: Usuario no encontrado
    """
    usuario = Usuario.query.get_or_404(id)
    usuario.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Usuario desactivado exitosamente'}), 200