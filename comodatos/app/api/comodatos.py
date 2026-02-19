from flask import request, jsonify
from datetime import datetime, date
from app.extensions import db
from app.models import Comodato, Instrumento, Alumno, Representante, EstadoInstrumento
from app.schemas import comodato_schema, comodatos_schema
from app.auth.utils import require_roles
from app.api import api_bp
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, get_jwt
from app.utils.generators import ComodatoManager
from app.utils.validators import Validators
import pandas as pd
from io import BytesIO

@api_bp.route('/comodatos', methods=['GET'])
@jwt_required()
def get_comodatos():
    """
    Obtener todos los comodatos
    ---
    tags:
      - Comodatos
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
        enum: [activo, finalizado, cancelado, renovado]
      - name: fecha_inicio_desde
        in: query
        type: string
        format: date
      - name: fecha_inicio_hasta
        in: query
        type: string
        format: date
      - name: vencidos
        in: query
        type: boolean
      - name: id_alumno
        in: query
        type: integer
      - name: id_instr
        in: query
        type: integer
    responses:
      200:
        description: Lista de comodatos
    """
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    estado = request.args.get('estado')
    fecha_inicio_desde = request.args.get('fecha_inicio_desde')
    fecha_inicio_hasta = request.args.get('fecha_inicio_hasta')
    vencidos = request.args.get('vencidos', False, type=bool)
    id_alumno = request.args.get('id_alumno', type=int)
    id_instr = request.args.get('id_instr', type=int)
    
    query = Comodato.query
    
    # Filtros por rol
    if claims.get('rol') == 'representante':
        # Representantes solo ven sus comodatos
        from app.models import Usuario
        usuario = Usuario.query.get(current_user_id)
        if usuario and usuario.representante:
            query = query.filter_by(id_repr=usuario.representante.id_repr)
    
    # Aplicar filtros
    if estado:
        query = query.filter_by(estado=estado)
    
    if fecha_inicio_desde:
        query = query.filter(Comodato.fecha_inicio >= fecha_inicio_desde)
    
    if fecha_inicio_hasta:
        query = query.filter(Comodato.fecha_inicio <= fecha_inicio_hasta)
    
    if vencidos:
        query = query.filter(
            Comodato.estado == 'activo',
            Comodato.fecha_fin < date.today()
        )
    
    if id_alumno:
        query = query.filter_by(id_alumno=id_alumno)
    
    if id_instr:
        query = query.filter_by(id_instr=id_instr)
    
    # Ordenar por fecha de inicio descendente
    query = query.order_by(Comodato.fecha_inicio.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'comodatos': comodatos_schema.dump(pagination.items),
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@api_bp.route('/comodatos', methods=['POST'])
@jwt_required()
@require_roles('admin', 'representante')
def create_comodato():
    """
    Crear nuevo comodato
    ---
    tags:
      - Comodatos
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - id_alumno
            - id_instr
            - fecha_inicio
            - fecha_fin
          properties:
            id_alumno:
              type: integer
            id_instr:
              type: integer
            fecha_inicio:
              type: string
              format: date
            fecha_fin:
              type: string
              format: date
            observaciones:
              type: string
    responses:
      201:
        description: Comodato creado
      400:
        description: Error en los datos
      403:
        description: No autorizado
    """
    try:
        data = request.get_json()
        
        # Validar fechas
        is_valid, message = Validators.validate_fechas_comodato(
            datetime.strptime(data['fecha_inicio'], '%Y-%m-%d').date(),
            datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
        )
        
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Verificar permisos para representantes
        claims = get_jwt()
        if claims.get('rol') == 'representante':
            # Verificar que el alumno pertenezca al representante
            from app.models import Usuario
            usuario = Usuario.query.get(get_jwt_identity())
            alumno = Alumno.query.get(data['id_alumno'])
            
            if not alumno or alumno.id_repr != usuario.representante.id_repr:
                return jsonify({
                    'error': 'No tienes permiso para crear comodatos para este alumno'
                }), 403
            
            data['id_repr'] = usuario.representante.id_repr
        
        # Crear comodato
        comodato = ComodatoManager.create_comodato(data)
        db.session.add(comodato)
        db.session.commit()
        
        return jsonify(comodato_schema.dump(comodato)), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/comodatos/<int:id>', methods=['GET'])
@jwt_required()
def get_comodato(id):
    """
    Obtener comodato por ID
    ---
    tags:
      - Comodatos
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Comodato encontrado
      404:
        description: Comodato no encontrado
    """
    comodato = Comodato.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        from app.models import Usuario
        usuario = Usuario.query.get(get_jwt_identity())
        if comodato.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    return jsonify(comodato_schema.dump(comodato)), 200

@api_bp.route('/comodatos/<int:id>', methods=['PUT'])
@jwt_required()
@require_roles('admin')
def update_comodato(id):
    """
    Actualizar comodato
    ---
    tags:
      - Comodatos
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
            fecha_fin:
              type: string
              format: date
            observaciones:
              type: string
            estado:
              type: string
              enum: [activo, finalizado, cancelado, renovado]
    responses:
      200:
        description: Comodato actualizado
      400:
        description: Error en los datos
    """
    comodato = Comodato.query.get_or_404(id)
    data = request.get_json()
    
    try:
        if 'fecha_fin' in data:
            # Validar nueva fecha de fin
            nueva_fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d').date()
            if nueva_fecha_fin <= comodato.fecha_inicio:
                return jsonify({
                    'error': 'La fecha de fin debe ser posterior a la fecha de inicio'
                }), 400
            
            comodato.fecha_fin = nueva_fecha_fin
        
        if 'observaciones' in data:
            comodato.observaciones = data['observaciones']
        
        if 'estado' in data:
            if data['estado'] == 'finalizado' and comodato.estado == 'activo':
                comodato.finalizar()
            else:
                comodato.estado = data['estado']
        
        db.session.commit()
        
        return jsonify(comodato_schema.dump(comodato)), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/comodatos/<int:id>/finalizar', methods=['POST'])
@jwt_required()
@require_roles('admin', 'representante')
def finalizar_comodato(id):
    """
    Finalizar comodato
    ---
    tags:
      - Comodatos
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
            fecha_recepcion:
              type: string
              format: date
            observaciones:
              type: string
    responses:
      200:
        description: Comodato finalizado
      400:
        description: Error al finalizar
    """
    comodato = Comodato.query.get_or_404(id)
    
    # Verificar permisos
    claims = get_jwt()
    if claims.get('rol') == 'representante':
        from app.models import Usuario
        usuario = Usuario.query.get(get_jwt_identity())
        if comodato.id_repr != usuario.representante.id_repr:
            return jsonify({'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        fecha_recepcion = None
        
        if data.get('fecha_recepcion'):
            fecha_recepcion = datetime.strptime(data['fecha_recepcion'], '%Y-%m-%d').date()
        
        comodato.finalizar(fecha_recepcion, data.get('observaciones'))
        db.session.commit()
        
        return jsonify({
            'message': 'Comodato finalizado exitosamente',
            'comodato': comodato_schema.dump(comodato)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/comodatos/reportes/vencidos', methods=['GET'])
@jwt_required()
@require_roles('admin')
def get_comodatos_vencidos():
    """
    Obtener reporte de comodatos vencidos
    ---
    tags:
      - Comodatos
      - Reportes
    security:
      - BearerAuth: []
    responses:
      200:
        description: Reporte de comodatos vencidos
    """
    comodatos_vencidos = Comodato.query.filter(
        Comodato.estado == 'activo',
        Comodato.fecha_fin < date.today()
    ).order_by(Comodato.fecha_fin).all()
    
    return jsonify(comodatos_schema.dump(comodatos_vencidos)), 200

@api_bp.route('/comodatos/reportes/exportar', methods=['GET'])
@jwt_required()
@require_roles('admin')
def exportar_comodatos():
    """
    Exportar comodatos a Excel
    ---
    tags:
      - Comodatos
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
        content:
          application/vnd.openxmlformats-officedocument.spreadsheetml.sheet:
            schema:
              type: string
              format: binary
    """
    comodatos = Comodato.query.all()
    data = []
    
    for comodato in comodatos:
        data.append({
            'Código Comodato': comodato.codigo_comodato,
            'Correlativo': comodato.correlativo,
            'Alumno': f"{comodato.alumno.nombre} {comodato.alumno.apellido}" if comodato.alumno else '',
            'Cédula Alumno': comodato.alumno.cedula if comodato.alumno else '',
            'Representante': f"{comodato.representante.nombre} {comodato.representante.apellido}" if comodato.representante else '',
            'Instrumento': comodato.instrumento.descripcion if comodato.instrumento else '',
            'Marca': comodato.instrumento.marca if comodato.instrumento else '',
            'Modelo': comodato.instrumento.modelo if comodato.instrumento else '',
            'Serial Inventario': comodato.instrumento.serial_inventario if comodato.instrumento else '',
            'Fecha Inicio': comodato.fecha_inicio,
            'Fecha Fin': comodato.fecha_fin,
            'Fecha Recepción': comodato.fecha_recepcion,
            'Estado': comodato.estado,
            'Días Restantes': comodato.dias_restantes,
            'Observaciones': comodato.observaciones
        })
    
    df = pd.DataFrame(data)
    
    formato = request.args.get('formato', 'excel')
    
    if formato == 'csv':
        output = df.to_csv(index=False, encoding='utf-8-sig')
        mimetype = 'text/csv'
        filename = f'comodatos_{date.today()}.csv'
    else:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Comodatos')
        output.seek(0)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'comodatos_{date.today()}.xlsx'
    
    from flask import send_file
    return send_file(
        output,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )