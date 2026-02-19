from flask import request, jsonify
from datetime import datetime, date
from app.extensions import db
from app.models import Instrumento, Medida, EstadoInstrumento, Accesorio, HistorialEstadoInstr
from app.schemas import instrumento_schema, instrumentos_schema, accesorio_schema, accesorios_schema, historial_estado_schema, historiales_estado_schema
from app.auth.utils import require_roles
from app.api import api_bp
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.utils.validators import Validators
from app.utils.generators import CodeGenerator
import pandas as pd
from io import BytesIO
from flask import send_file

@api_bp.route('/instrumentos', methods=['GET'])
@jwt_required()
def get_instrumentos():
    """
    Obtener todos los instrumentos
    ---
    tags:
      - Instrumentos
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
        enum: [disponible, asignado, no_operativo, mantenimiento, baja]
      - name: descripcion
        in: query
        type: string
      - name: marca
        in: query
        type: string
      - name: id_medida
        in: query
        type: integer
      - name: search
        in: query
        type: string
        description: Buscar por descripción, marca, modelo o serial
    responses:
      200:
        description: Lista de instrumentos
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    estado = request.args.get('estado')
    descripcion = request.args.get('descripcion')
    marca = request.args.get('marca')
    id_medida = request.args.get('id_medida', type=int)
    search = request.args.get('search')
    
    query = Instrumento.query
    
    # Aplicar filtros
    if estado:
        query = query.join(EstadoInstrumento).filter(
            EstadoInstrumento.nombre == estado
        )
    
    if descripcion:
        query = query.filter(Instrumento.descripcion.ilike(f"%{descripcion}%"))
    
    if marca:
        query = query.filter(Instrumento.marca.ilike(f"%{marca}%"))
    
    if id_medida:
        query = query.filter_by(id_medida=id_medida)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Instrumento.descripcion.ilike(search_term),
                Instrumento.marca.ilike(search_term),
                Instrumento.modelo.ilike(search_term),
                Instrumento.serial_fabrica.ilike(search_term),
                Instrumento.serial_inventario.ilike(search_term)
            )
        )
    
    # Ordenar por descripción
    query = query.order_by(Instrumento.descripcion, Instrumento.marca)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'instrumentos': instrumentos_schema.dump(pagination.items),
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@api_bp.route('/instrumentos/disponibles', methods=['GET'])
@jwt_required()
@require_roles('admin', 'representante')
def get_instrumentos_disponibles():
    """
    Obtener instrumentos disponibles
    ---
    tags:
      - Instrumentos
    security:
      - BearerAuth: []
    parameters:
      - name: descripcion
        in: query
        type: string
      - name: id_medida
        in: query
        type: integer
    responses:
      200:
        description: Lista de instrumentos disponibles
    """
    descripcion = request.args.get('descripcion')
    id_medida = request.args.get('id_medida', type=int)
    
    query = Instrumento.query.join(EstadoInstrumento).filter(
        EstadoInstrumento.nombre == 'disponible'
    )
    
    if descripcion:
        query = query.filter(Instrumento.descripcion.ilike(f"%{descripcion}%"))
    
    if id_medida:
        query = query.filter_by(id_medida=id_medida)
    
    # Ordenar por descripción
    query = query.order_by(Instrumento.descripcion, Instrumento.marca)
    
    instrumentos = query.all()
    
    return jsonify(instrumentos_schema.dump(instrumentos)), 200

@api_bp.route('/instrumentos', methods=['POST'])
@jwt_required()
@require_roles('admin')
def create_instrumento():
    """
    Crear nuevo instrumento
    ---
    tags:
      - Instrumentos
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - descripcion
            - serial_inventario
          properties:
            descripcion:
              type: string
            marca:
              type: string
            modelo:
              type: string
            id_medida:
              type: integer
            color:
              type: string
            serial_fabrica:
              type: string
            serial_inventario:
              type: string
            id_estado_instr:
              type: integer
            fecha_adquisicion:
              type: string
              format: date
            observaciones:
              type: string
    responses:
      201:
        description: Instrumento creado
      400:
        description: Error en los datos
    """
    try:
        data = request.get_json()
        
        # Validar serial de inventario
        if not Validators.validate_serial_inventario(data['serial_inventario']):
            return jsonify({
                'error': 'El serial de inventario debe tener exactamente 16 dígitos'
            }), 400
        
        # Verificar que el serial no exista
        if Instrumento.query.filter_by(
            serial_inventario=data['serial_inventario']
        ).first():
            return jsonify({
                'error': 'El serial de inventario ya está registrado'
            }), 400
        
        # Verificar que la medida exista (si se proporciona)
        if 'id_medida' in data and data['id_medida']:
            if not Medida.query.get(data['id_medida']):
                return jsonify({'error': 'Medida no encontrada'}), 404
        
        # Verificar que el estado exista (si se proporciona)
        estado_id = data.get('id_estado_instr')
        if not estado_id:
            # Por defecto, disponible
            estado_disponible = EstadoInstrumento.query.filter_by(
                nombre='disponible'
            ).first()
            if estado_disponible:
                data['id_estado_instr'] = estado_disponible.id_estado_instr
            else:
                return jsonify({'error': 'Estado "disponible" no configurado'}), 500
        elif not EstadoInstrumento.query.get(estado_id):
            return jsonify({'error': 'Estado no encontrado'}), 404
        
        # Sanitizar entradas
        for field in ['descripcion', 'marca', 'modelo', 'color', 
                     'serial_fabrica', 'observaciones']:
            if field in data and data[field]:
                data[field] = Validators.sanitize_input(data[field])
        
        # Crear instrumento
        instrumento = instrumento_schema.load(data)
        
        db.session.add(instrumento)
        db.session.commit()
        
        # Registrar en historial
        historial = HistorialEstadoInstr(
            id_instr=instrumento.id_instr,
            id_estado_instr=instrumento.id_estado_instr,
            observacion='Instrumento creado en el sistema'
        )
        db.session.add(historial)
        db.session.commit()
        
        return jsonify(instrumento_schema.dump(instrumento)), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/instrumentos/<int:id>', methods=['GET'])
@jwt_required()
def get_instrumento(id):
    """
    Obtener instrumento por ID
    ---
    tags:
      - Instrumentos
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Instrumento encontrado
      404:
        description: Instrumento no encontrado
    """
    instrumento = Instrumento.query.get_or_404(id)
    return jsonify(instrumento_schema.dump(instrumento)), 200

@api_bp.route('/instrumentos/<int:id>', methods=['PUT'])
@jwt_required()
@require_roles('admin')
def update_instrumento(id):
    """
    Actualizar instrumento
    ---
    tags:
      - Instrumentos
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
            descripcion:
              type: string
            marca:
              type: string
            modelo:
              type: string
            id_medida:
              type: integer
            color:
              type: string
            serial_fabrica:
              type: string
            fecha_adquisicion:
              type: string
              format: date
            observaciones:
              type: string
    responses:
      200:
        description: Instrumento actualizado
      400:
        description: Error en los datos
    """
    instrumento = Instrumento.query.get_or_404(id)
    
    try:
        data = request.get_json()
        
        # No permitir cambiar serial de inventario
        if 'serial_inventario' in data:
            del data['serial_inventario']
        
        # Verificar que la medida exista (si se proporciona)
        if 'id_medida' in data and data['id_medida']:
            if not Medida.query.get(data['id_medida']):
                return jsonify({'error': 'Medida no encontrada'}), 404
        
        # Sanitizar entradas
        for field in ['descripcion', 'marca', 'modelo', 'color', 
                     'serial_fabrica', 'observaciones']:
            if field in data and data[field]:
                data[field] = Validators.sanitize_input(data[field])
        
        # Actualizar instrumento
        for key, value in data.items():
            if hasattr(instrumento, key) and key not in ['id_instr', 'id_estado_instr']:
                setattr(instrumento, key, value)
        
        db.session.commit()
        
        return jsonify(instrumento_schema.dump(instrumento)), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/instrumentos/<int:id>/cambiar-estado', methods=['POST'])
@jwt_required()
@require_roles('admin')
def cambiar_estado_instrumento(id):
    """
    Cambiar estado de un instrumento
    ---
    tags:
      - Instrumentos
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
          required:
            - id_estado_instr
          properties:
            id_estado_instr:
              type: integer
            observacion:
              type: string
    responses:
      200:
        description: Estado cambiado exitosamente
      400:
        description: Error en los datos
    """
    instrumento = Instrumento.query.get_or_404(id)
    
    try:
        data = request.get_json()
        
        # Verificar que el estado exista
        nuevo_estado = EstadoInstrumento.query.get(data['id_estado_instr'])
        if not nuevo_estado:
            return jsonify({'error': 'Estado no encontrado'}), 404
        
        # Verificar que no sea el mismo estado
        if instrumento.id_estado_instr == data['id_estado_instr']:
            return jsonify({'error': 'El instrumento ya tiene ese estado'}), 400
        
        # Cambiar estado
        historial = instrumento.cambiar_estado(
            data['id_estado_instr'],
            data.get('observacion')
        )
        
        db.session.commit()
        
        return jsonify({
            'message': f'Estado cambiado a {nuevo_estado.nombre}',
            'instrumento': instrumento_schema.dump(instrumento),
            'historial': historial_estado_schema.dump(historial)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/instrumentos/<int:id>/historial-estados', methods=['GET'])
@jwt_required()
@require_roles('admin')
def get_historial_estados(id):
    """
    Obtener historial de estados de un instrumento
    ---
    tags:
      - Instrumentos
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
      - name: limit
        in: query
        type: integer
        default: 50
    responses:
      200:
        description: Historial de estados
    """
    limit = request.args.get('limit', 50, type=int)
    
    historial = HistorialEstadoInstr.query.filter_by(
        id_instr=id
    ).order_by(
        HistorialEstadoInstr.fecha.desc()
    ).limit(limit).all()
    
    return jsonify(historiales_estado_schema.dump(historial)), 200

@api_bp.route('/instrumentos/<int:id>/accesorios', methods=['GET'])
@jwt_required()
def get_accesorios_instrumento(id):
    """
    Obtener accesorios de un instrumento
    ---
    tags:
      - Instrumentos
      - Accesorios
    security:
      - BearerAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Lista de accesorios
    """
    instrumento = Instrumento.query.get_or_404(id)
    accesorios = instrumento.accesorios.all()
    
    return jsonify(accesorios_schema.dump(accesorios)), 200

@api_bp.route('/instrumentos/<int:id>/accesorios', methods=['POST'])
@jwt_required()
@require_roles('admin')
def add_accesorio(id):
    """
    Agregar accesorio a un instrumento
    ---
    tags:
      - Instrumentos
      - Accesorios
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
          required:
            - nombre
          properties:
            nombre:
              type: string
            descripcion:
              type: string
            serial:
              type: string
            estado:
              type: string
              enum: [bueno, regular, malo, perdido]
    responses:
      201:
        description: Accesorio agregado
      400:
        description: Error en los datos
    """
    instrumento = Instrumento.query.get_or_404(id)
    
    try:
        data = request.get_json()
        data['id_instr'] = id
        
        # Sanitizar entradas
        for field in ['nombre', 'descripcion', 'serial']:
            if field in data and data[field]:
                data[field] = Validators.sanitize_input(data[field])
        
        # Crear accesorio
        accesorio = accesorio_schema.load(data)
        
        db.session.add(accesorio)
        db.session.commit()
        
        return jsonify(accesorio_schema.dump(accesorio)), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/instrumentos/<int:id>/comodatos', methods=['GET'])
@jwt_required()
@require_roles('admin')
def get_comodatos_instrumento(id):
    """
    Obtener comodatos de un instrumento
    ---
    tags:
      - Instrumentos
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
        description: Lista de comodatos
    """
    instrumento = Instrumento.query.get_or_404(id)
    
    estado = request.args.get('estado')
    
    query = instrumento.comodatos
    
    if estado:
        query = query.filter_by(estado=estado)
    
    query = query.order_by(Comodato.fecha_inicio.desc())
    
    comodatos = query.all()
    
    from app.schemas import comodatos_schema
    return jsonify(comodatos_schema.dump(comodatos)), 200

@api_bp.route('/instrumentos/exportar', methods=['GET'])
@jwt_required()
@require_roles('admin')
def exportar_instrumentos():
    """
    Exportar instrumentos a Excel
    ---
    tags:
      - Instrumentos
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
    
    instrumentos = Instrumento.query.all()
    data = []
    
    for instrumento in instrumentos:
        data.append({
            'ID': instrumento.id_instr,
            'Descripción': instrumento.descripcion,
            'Marca': instrumento.marca,
            'Modelo': instrumento.modelo,
            'Medida': instrumento.medida.nombre if instrumento.medida else '',
            'Color': instrumento.color,
            'Serial Fábrica': instrumento.serial_fabrica,
            'Serial Inventario': instrumento.serial_inventario,
            'Estado': instrumento.estado_actual.nombre if instrumento.estado_actual else '',
            'Fecha Adquisición': instrumento.fecha_adquisicion,
            'Observaciones': instrumento.observaciones,
            'Accesorios': len(instrumento.accesorios.all()),
            'Comodatos Activos': len([c for c in instrumento.comodatos if c.estado == 'activo']),
            'Comodatos Totales': len(instrumento.comodatos.all())
        })
    
    df = pd.DataFrame(data)
    
    formato = request.args.get('formato', 'excel')
    
    if formato == 'csv':
        output = df.to_csv(index=False, encoding='utf-8-sig')
        mimetype = 'text/csv'
        filename = f'instrumentos_{date.today()}.csv'
        return send_file(
            BytesIO(output.encode('utf-8-sig')),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    else:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Instrumentos')
        output.seek(0)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'instrumentos_{date.today()}.xlsx'
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )