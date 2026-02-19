from flask import request, jsonify
from datetime import datetime
from app.extensions import db
from app.models import Alumno, Representante, Usuario
from app.schemas import alumno_schema, alumnos_schema
from app.auth.utils import require_roles
from app.api import api_bp
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.utils.validators import Validators

@api_bp.route('/alumnos', methods=['GET'])
@jwt_required()
def get_alumnos():
    """
    Obtener todos los alumnos
    ---
    tags:
      - Alumnos
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
      - name: estado
        in: query
        type: string
        enum: [activo, inactivo]
      - name: programa
        in: query
        type: string
        enum: [iniciacion, coral, orquestal, alma_llanera, otros]
      - name: id_repr
        in: query
        type: integer
      - name: search
        in: query
        type: string
        description: Buscar por nombre, apellido o cédula
    responses:
      200:
        description: Lista de alumnos
    """
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    estado = request.args.get('estado')
    programa = request.args.get('programa')
    id_repr = request.args.get('id_repr', type=int)
    search = request.args.get('search')
    
    query = Alumno.query
    
    # Filtros por rol
    if claims.get('rol') == 'representante':
        # Representantes solo ven sus alumnos
        usuario = Usuario.query.get(current_user_id)
        if usuario and usuario.representante:
            query = query.filter_by(id_repr=usuario.representante.id_repr)
    
    # Aplicar filtros
    if estado:
        query = query.filter_by(estado=estado)
    
    if programa:
        query = query.filter_by(programa=programa)
    
    if id_repr and claims.get('rol') == 'admin':
        query = query.filter_by(id_repr=id_repr)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Alumno.nombre.ilike(search_term),
                Alumno.apellido.ilike(search_term),
                Alumno.cedula.ilike(search_term)
            )
        )
    
    # Ordenar por nombre
    query = query.order_by(Alumno.nombre, Alumno.apellido)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'alumnos': alumnos_schema.dump(pagination.items),
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@api_bp.route('/alumnos', methods=['POST'])
@jwt_required()
@require_roles('admin', 'representante')
def create_alumno():
    """
    Crear nuevo alumno
    ---
    tags:
      - Alumnos
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - nombre
            - apellido
            - cedula
          properties:
            nombre:
              type: string
            apellido:
              type: string
            cedula:
              type: string
            fecha_nacimiento:
              type: string
              format: date
            programa:
              type: string
              enum: [iniciacion, coral, orquestal, alma_llanera, otros]
            estado:
              type: string
              enum: [activo, inactivo]
            id_repr:
              type: integer
    responses:
      201:
        description: Alumno creado
      400:
        description: Error en los datos
      403:
        description: No autorizado
    """
    try:
        data = request.get_json()
        
        # Verificar que la cédula no exista
        if Alumno.query.filter_by(cedula=data['cedula']).first():
            return jsonify({'error': 'La cédula ya está registrada'}), 400
        
        # Validar cédula
        if not Validators.validate_cedula(data['cedula']):
            return jsonify({'error': 'Formato de cédula inválido'}), 400
        
        # Si es representante, asignar automáticamente su ID
        claims = get_jwt()
        if claims.get('rol') == 'representante':
            usuario = Usuario.query.get(get_jwt_identity())
            if usuario and usuario.representante:
                data['id_repr'] = usuario.representante.id_repr
            else:
                return jsonify({'error': 'Representante no encontrado'}), 404
        
        # Validar que el representante exista (si se proporciona)
        if 'id_repr' in data and data['id_repr']:
            if not Representante.query.get(data['id_repr']):
                return jsonify({'error': 'Representante no encontrado'}), 404
        
        # Sanitizar entradas
        for field in ['nombre', 'apellido', 'cedula']:
            if field in data:
                data[field] = Validators.sanitize_input(data[field])
        
        # Crear alumno
        alumno = alumno_schema.load(data)
        
        db.session.add(alumno)
        db.session.commit()
        
        return jsonify(alumno_schema.dump(alumno)), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/alumnos/<int:id>', methods=['GET'])
@jwt_required()
def get_alumno(id):
    """
    Obtener alumno por ID
    ---
    tags:
      - Alumnos
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Alumno encontrado
      404:
        description: Alumno no encontrado
    """
    alumno = Alumno.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        usuario = Usuario.query.get(get_jwt_identity())
        if alumno.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    return jsonify(alumno_schema.dump(alumno)), 200

@api_bp.route('/alumnos/<int:id>', methods=['PUT'])
@jwt_required()
@require_roles('admin', 'representante')
def update_alumno(id):
    """
    Actualizar alumno
    ---
    tags:
      - Alumnos
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
            nombre:
              type: string
            apellido:
              type: string
            cedula:
              type: string
            fecha_nacimiento:
              type: string
              format: date
            programa:
              type: string
              enum: [iniciacion, coral, orquestal, alma_llanera, otros]
            estado:
              type: string
              enum: [activo, inactivo]
    responses:
      200:
        description: Alumno actualizado
      400:
        description: Error en los datos
    """
    alumno = Alumno.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        usuario = Usuario.query.get(get_jwt_identity())
        if alumno.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        
        # No permitir cambiar cédula si ya existe otra con la misma
        if 'cedula' in data and data['cedula'] != alumno.cedula:
            if Alumno.query.filter_by(cedula=data['cedula']).first():
                return jsonify({'error': 'La cédula ya está registrada'}), 400
            
            if not Validators.validate_cedula(data['cedula']):
                return jsonify({'error': 'Formato de cédula inválido'}), 400
        
        # Sanitizar entradas
        for field in ['nombre', 'apellido', 'cedula']:
            if field in data:
                data[field] = Validators.sanitize_input(data[field])
        
        # Actualizar alumno
        for key, value in data.items():
            if hasattr(alumno, key) and key not in ['id_alumno', 'id_repr']:
                setattr(alumno, key, value)
        
        db.session.commit()
        
        return jsonify(alumno_schema.dump(alumno)), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/alumnos/<int:id>', methods=['DELETE'])
@jwt_required()
@require_roles('admin')
def delete_alumno(id):
    """
    Eliminar alumno
    ---
    tags:
      - Alumnos
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Alumno eliminado
      400:
        description: No se puede eliminar (tiene comodatos activos)
    """
    alumno = Alumno.query.get_or_404(id)
    
    # Verificar si tiene comodatos activos
    from app.models import Comodato
    comodatos_activos = Comodato.query.filter_by(
        id_alumno=id,
        estado='activo'
    ).first()
    
    if comodatos_activos:
        return jsonify({
            'error': 'No se puede eliminar el alumno porque tiene comodatos activos'
        }), 400
    
    try:
        # Marcar como inactivo en lugar de eliminar
        alumno.estado = 'inactivo'
        db.session.commit()
        
        return jsonify({
            'message': 'Alumno marcado como inactivo exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/alumnos/<int:id>/comodatos', methods=['GET'])
@jwt_required()
def get_alumno_comodatos(id):
    """
    Obtener comodatos de un alumno
    ---
    tags:
      - Alumnos
      - Comodatos
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
      - name: estado
        in: query
        type: string
        enum: [activo, finalizado, cancelado, renovado]
    responses:
      200:
        description: Lista de comodatos del alumno
    """
    alumno = Alumno.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        usuario = Usuario.query.get(get_jwt_identity())
        if alumno.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    estado = request.args.get('estado')
    
    query = alumno.comodatos
    
    if estado:
        query = query.filter_by(estado=estado)
    
    query = query.order_by(Comodato.fecha_inicio.desc())
    
    comodatos = query.all()
    
    from app.schemas import comodatos_schema
    return jsonify(comodatos_schema.dump(comodatos)), 200

@api_bp.route('/alumnos/exportar', methods=['GET'])
@jwt_required()
@require_roles('admin')
def exportar_alumnos():
    """
    Exportar alumnos a Excel
    ---
    tags:
      - Alumnos
      - Reportes
    security:
      - BearerAuth: []
    parameters:
      - name: formato
        in: query
        type: string
        enum: [excel, csv]
        default: excel
    responses:
      200:
        description: Archivo exportado
    """
    from datetime import date
    import pandas as pd
    from io import BytesIO
    from flask import send_file
    
    alumnos = Alumno.query.all()
    data = []
    
    for alumno in alumnos:
        data.append({
            'ID': alumno.id_alumno,
            'Nombre': alumno.nombre,
            'Apellido': alumno.apellido,
            'Cédula': alumno.cedula,
            'Fecha Nacimiento': alumno.fecha_nacimiento,
            'Edad': alumno.edad,
            'Programa': alumno.programa,
            'Estado': alumno.estado,
            'Representante': alumno.representante.nombre_completo if alumno.representante else '',
            'Cédula Representante': alumno.representante.cedula if alumno.representante else '',
            'Teléfono Representante': alumno.representante.telefono if alumno.representante else '',
            'Comodatos Activos': len([c for c in alumno.comodatos if c.estado == 'activo']),
            'Comodatos Totales': len(alumno.comodatos.all())
        })
    
    df = pd.DataFrame(data)
    
    formato = request.args.get('formato', 'excel')
    
    if formato == 'csv':
        output = df.to_csv(index=False, encoding='utf-8-sig')
        mimetype = 'text/csv'
        filename = f'alumnos_{date.today()}.csv'
        return send_file(
            BytesIO(output.encode('utf-8-sig')),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    else:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Alumnos')
        output.seek(0)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'alumnos_{date.today()}.xlsx'
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )