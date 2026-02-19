from flask import request, jsonify
from app.extensions import db
from app.models import Representante, Usuario, Alumno, Comodato
from app.schemas import representante_schema, representantes_schema
from app.auth.utils import require_roles
from app.api import api_bp
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.utils.validators import Validators
import pandas as pd
from io import BytesIO
from flask import send_file
from datetime import date

@api_bp.route('/representantes', methods=['GET'])
@jwt_required()
@require_roles('admin')
def get_representantes():
    """
    Obtener todos los representantes
    ---
    tags:
      - Representantes
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
      - name: search
        in: query
        type: string
        description: Buscar por nombre, apellido o cédula
    responses:
      200:
        description: Lista de representantes
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search')
    
    query = Representante.query
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Representante.nombre.ilike(search_term),
                Representante.apellido.ilike(search_term),
                Representante.cedula.ilike(search_term)
            )
        )
    
    # Ordenar por nombre
    query = query.order_by(Representante.nombre, Representante.apellido)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'representantes': representantes_schema.dump(pagination.items),
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@api_bp.route('/representantes/<int:id>', methods=['GET'])
@jwt_required()
def get_representante(id):
    """
    Obtener representante por ID
    ---
    tags:
      - Representantes
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Representante encontrado
      404:
        description: Representante no encontrado
    """
    representante = Representante.query.get_or_404(id)
    
    # Verificar permisos (representantes solo pueden verse a sí mismos)
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        usuario = Usuario.query.get(get_jwt_identity())
        if representante.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    return jsonify(representante_schema.dump(representante)), 200

@api_bp.route('/representantes/<int:id>', methods=['PUT'])
@jwt_required()
@require_roles('admin', 'representante')
def update_representante(id):
    """
    Actualizar representante
    ---
    tags:
      - Representantes
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
            telefono:
              type: string
            direccion:
              type: string
    responses:
      200:
        description: Representante actualizado
      400:
        description: Error en los datos
    """
    representante = Representante.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        usuario = Usuario.query.get(get_jwt_identity())
        if representante.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        
        # No permitir cambiar cédula si ya existe otra con la misma
        if 'cedula' in data and data['cedula'] != representante.cedula:
            if Representante.query.filter_by(cedula=data['cedula']).first():
                return jsonify({'error': 'La cédula ya está registrada'}), 400
            
            if not Validators.validate_cedula(data['cedula']):
                return jsonify({'error': 'Formato de cédula inválido'}), 400
        
        # Sanitizar entradas
        for field in ['nombre', 'apellido', 'cedula', 'telefono', 'direccion']:
            if field in data:
                data[field] = Validators.sanitize_input(data[field])
        
        # Actualizar representante
        for key, value in data.items():
            if hasattr(representante, key) and key not in ['id_repr', 'id_usuario']:
                setattr(representante, key, value)
        
        db.session.commit()
        
        return jsonify(representante_schema.dump(representante)), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/representantes/<int:id>/alumnos', methods=['GET'])
@jwt_required()
def get_alumnos_representante(id):
    """
    Obtener alumnos de un representante
    ---
    tags:
      - Representantes
      - Alumnos
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
        enum: [activo, inactivo]
    responses:
      200:
        description: Lista de alumnos
    """
    representante = Representante.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        usuario = Usuario.query.get(get_jwt_identity())
        if representante.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    estado = request.args.get('estado')
    
    query = representante.alumnos
    
    if estado:
        query = query.filter_by(estado=estado)
    
    query = query.order_by(Alumno.nombre, Alumno.apellido)
    
    alumnos = query.all()
    
    from app.schemas import alumnos_schema
    return jsonify(alumnos_schema.dump(alumnos)), 200

@api_bp.route('/representantes/<int:id>/comodatos', methods=['GET'])
@jwt_required()
def get_comodatos_representante(id):
    """
    Obtener comodatos de un representante
    ---
    tags:
      - Representantes
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
      - name: vencidos
        in: query
        type: boolean
    responses:
      200:
        description: Lista de comodatos
    """
    representante = Representante.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        usuario = Usuario.query.get(get_jwt_identity())
        if representante.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    estado = request.args.get('estado')
    vencidos = request.args.get('vencidos', False, type=bool)
    
    query = representante.comodatos
    
    if estado:
        query = query.filter_by(estado=estado)
    
    if vencidos:
        query = query.filter(
            Comodato.estado == 'activo',
            Comodato.fecha_fin < date.today()
        )
    
    query = query.order_by(Comodato.fecha_inicio.desc())
    
    comodatos = query.all()
    
    from app.schemas import comodatos_schema
    return jsonify(comodatos_schema.dump(comodatos)), 200

@api_bp.route('/representantes/<int:id>/estadisticas', methods=['GET'])
@jwt_required()
def get_estadisticas_representante(id):
    """
    Obtener estadísticas de un representante
    ---
    tags:
      - Representantes
      - Reportes
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Estadísticas del representante
    """
    representante = Representante.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        usuario = Usuario.query.get(get_jwt_identity())
        if representante.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    # Obtener estadísticas
    alumnos_activos = representante.alumnos.filter_by(estado='activo').count()
    alumnos_totales = representante.alumnos.count()
    
    comodatos_activos = representante.comodatos.filter_by(estado='activo').count()
    comodatos_finalizados = representante.comodatos.filter_by(estado='finalizado').count()
    comodatos_vencidos = representante.comodatos.filter(
        Comodato.estado == 'activo',
        Comodato.fecha_fin < date.today()
    ).count()
    comodatos_totales = representante.comodatos.count()
    
    return jsonify({
        'representante': representante_schema.dump(representante),
        'estadisticas': {
            'alumnos': {
                'activos': alumnos_activos,
                'total': alumnos_totales,
                'inactivos': alumnos_totales - alumnos_activos
            },
            'comodatos': {
                'activos': comodatos_activos,
                'finalizados': comodatos_finalizados,
                'vencidos': comodatos_vencidos,
                'total': comodatos_totales
            }
        }
    }), 200

@api_bp.route('/representantes/exportar', methods=['GET'])
@jwt_required()
@require_roles('admin')
def exportar_representantes():
    """
    Exportar representantes a Excel
    ---
    tags:
      - Representantes
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
    
    representantes = Representante.query.all()
    data = []
    
    for representante in representantes:
        alumnos_activos = representante.alumnos.filter_by(estado='activo').count()
        alumnos_totales = representante.alumnos.count()
        
        comodatos_activos = representante.comodatos.filter_by(estado='activo').count()
        comodatos_vencidos = representante.comodatos.filter(
            Comodato.estado == 'activo',
            Comodato.fecha_fin < date.today()
        ).count()
        
        data.append({
            'ID': representante.id_repr,
            'Nombre': representante.nombre,
            'Apellido': representante.apellido,
            'Cédula': representante.cedula,
            'Teléfono': representante.telefono,
            'Dirección': representante.direccion,
            'Email': representante.usuario.email if representante.usuario else '',
            'Estado Usuario': 'Activo' if representante.usuario and representante.usuario.is_active else 'Inactivo',
            'Alumnos Activos': alumnos_activos,
            'Alumnos Totales': alumnos_totales,
            'Comodatos Activos': comodatos_activos,
            'Comodatos Vencidos': comodatos_vencidos
        })
    
    df = pd.DataFrame(data)
    
    formato = request.args.get('formato', 'excel')
    
    if formato == 'csv':
        output = df.to_csv(index=False, encoding='utf-8-sig')
        mimetype = 'text/csv'
        filename = f'representantes_{date.today()}.csv'
        return send_file(
            BytesIO(output.encode('utf-8-sig')),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    else:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Representantes')
        output.seek(0)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'representantes_{date.today()}.xlsx'
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )