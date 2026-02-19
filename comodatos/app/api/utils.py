from flask import jsonify, request
from app.extensions import db
from app.models import Medida, EstadoInstrumento, Usuario, Representante, Alumno, Instrumento, Comodato
from app.schemas import medida_schema, medidas_schema, estado_instrumento_schema, estados_instrumento_schema
from app.schemas import alumnos_schema, representantes_schema, instrumentos_schema, comodatos_schema
from app.api import api_bp
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.auth.utils import require_roles
from datetime import date, timedelta
from sqlalchemy import func

@api_bp.route('/medidas', methods=['GET'])
@jwt_required()
def get_medidas():
    """Obtener todas las medidas"""
    medidas = Medida.query.order_by(Medida.nombre).all()
    return jsonify(medidas_schema.dump(medidas)), 200

@api_bp.route('/medidas', methods=['POST'])
@jwt_required()
@require_roles('admin')
def create_medida():
    """Crear nueva medida"""
    try:
        data = request.get_json()
        
        if Medida.query.filter_by(nombre=data['nombre']).first():
            return jsonify({'error': 'La medida ya existe'}), 400
        
        medida = medida_schema.load(data)
        db.session.add(medida)
        db.session.commit()
        
        return jsonify(medida_schema.dump(medida)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/estados-instrumento', methods=['GET'])
@jwt_required()
def get_estados_instrumento():
    """Obtener todos los estados de instrumento"""
    estados = EstadoInstrumento.query.order_by(EstadoInstrumento.nombre).all()
    return jsonify(estados_instrumento_schema.dump(estados)), 200

@api_bp.route('/estados-instrumento', methods=['POST'])
@jwt_required()
@require_roles('admin')
def create_estado_instrumento():
    """Crear nuevo estado de instrumento"""
    try:
        data = request.get_json()
        
        if EstadoInstrumento.query.filter_by(nombre=data['nombre']).first():
            return jsonify({'error': 'El estado ya existe'}), 400
        
        estado = estado_instrumento_schema.load(data)
        db.session.add(estado)
        db.session.commit()
        
        return jsonify(estado_instrumento_schema.dump(estado)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/dashboard/estadisticas', methods=['GET'])
@jwt_required()
def get_estadisticas_dashboard():
    """Obtener estadísticas para el dashboard"""
    
    total_usuarios = Usuario.query.count()
    total_representantes = Representante.query.count()
    total_alumnos = Alumno.query.count()
    total_instrumentos = Instrumento.query.count()
    
    # Instrumentos por estado
    instrumentos_por_estado = db.session.query(
        EstadoInstrumento.nombre,
        func.count(Instrumento.id_instr)
    ).join(Instrumento).group_by(EstadoInstrumento.nombre).all()
    
    # Comodatos por estado
    comodatos_activos = Comodato.query.filter_by(estado='activo').count()
    comodatos_finalizados = Comodato.query.filter_by(estado='finalizado').count()
    comodatos_vencidos = Comodato.query.filter(
        Comodato.estado == 'activo',
        Comodato.fecha_fin < date.today()
    ).count()
    total_comodatos = Comodato.query.count()
    
    # Comodatos próximos a vencer (próximos 30 días)
    fecha_limite = date.today() + timedelta(days=30)
    comodatos_proximos = Comodato.query.filter(
        Comodato.estado == 'activo',
        Comodato.fecha_fin >= date.today(),
        Comodato.fecha_fin <= fecha_limite
    ).count()
    
    # Alumnos por programa
    alumnos_por_programa = db.session.query(
        Alumno.programa,
        func.count(Alumno.id_alumno)
    ).group_by(Alumno.programa).all()
    
    return jsonify({
        'estadisticas': {
            'usuarios': {
                'total': total_usuarios,
                'activos': Usuario.query.filter_by(is_active=True).count()
            },
            'representantes': {
                'total': total_representantes
            },
            'alumnos': {
                'total': total_alumnos,
                'activos': Alumno.query.filter_by(estado='activo').count(),
                'por_programa': dict(alumnos_por_programa)
            },
            'instrumentos': {
                'total': total_instrumentos,
                'por_estado': dict(instrumentos_por_estado)
            },
            'comodatos': {
                'total': total_comodatos,
                'activos': comodatos_activos,
                'finalizados': comodatos_finalizados,
                'vencidos': comodatos_vencidos,
                'proximos_a_vencer': comodatos_proximos
            }
        }
    }), 200

@api_bp.route('/dashboard/alertas', methods=['GET'])
@jwt_required()
def get_alertas_dashboard():
    """Obtener alertas para el dashboard"""
    
    limit = request.args.get('limit', 10, type=int)
    
    alertas = []
    
    # Comodatos vencidos
    comodatos_vencidos = Comodato.query.filter(
        Comodato.estado == 'activo',
        Comodato.fecha_fin < date.today()
    ).order_by(Comodato.fecha_fin.desc()).limit(limit).all()
    
    for comodato in comodatos_vencidos:
        alertas.append({
            'tipo': 'vencido',
            'nivel': 'alto',
            'titulo': 'Comodato vencido',
            'descripcion': f'Comodato {comodato.codigo_comodato} vencido el {comodato.fecha_fin}',
            'fecha': comodato.fecha_fin.isoformat(),
            'entidad': 'comodato',
            'entidad_id': comodato.id_comodato,
            'dias_vencido': (date.today() - comodato.fecha_fin).days
        })
    
    # Comodatos próximos a vencer (próximos 7 días)
    fecha_limite = date.today() + timedelta(days=7)
    comodatos_proximos = Comodato.query.filter(
        Comodato.estado == 'activo',
        Comodato.fecha_fin >= date.today(),
        Comodato.fecha_fin <= fecha_limite
    ).order_by(Comodato.fecha_fin).limit(limit).all()
    
    for comodato in comodatos_proximos:
        dias_restantes = (comodato.fecha_fin - date.today()).days
        alertas.append({
            'tipo': 'proximo_a_vencer',
            'nivel': 'medio' if dias_restantes > 3 else 'alto',
            'titulo': 'Comodato próximo a vencer',
            'descripcion': f'Comodato {comodato.codigo_comodato} vence en {dias_restantes} días',
            'fecha': comodato.fecha_fin.isoformat(),
            'entidad': 'comodato',
            'entidad_id': comodato.id_comodato,
            'dias_restantes': dias_restantes
        })
    
    # Ordenar alertas por nivel y fecha
    nivel_prioridad = {'alto': 1, 'medio': 2, 'bajo': 3}
    alertas.sort(key=lambda x: (nivel_prioridad.get(x['nivel'], 4), x['fecha']))
    
    return jsonify({
        'alertas': alertas[:limit],
        'total': len(alertas)
    }), 200

@api_bp.route('/utils/buscar-rapido', methods=['GET'])
@jwt_required()
def buscar_rapido():
    """Búsqueda rápida en todo el sistema"""
    
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({
            'alumnos': [],
            'representantes': [],
            'instrumentos': [],
            'comodatos': [],
            'total': 0
        }), 200
    
    # Función para normalizar texto (quitar acentos)
    import unicodedata
    def normalize(text):
        if not text:
            return text
        return ''.join(
            c for c in unicodedata.normalize('NFD', text.lower())
            if unicodedata.category(c) != 'Mn'
        )
    
    search_term = f"%{query}%"
    search_term_normalized = f"%{normalize(query)}%"
    
    # Buscar alumnos
    alumnos = Alumno.query.filter(
        db.or_(
            Alumno.nombre.ilike(search_term),
            Alumno.apellido.ilike(search_term),
            Alumno.cedula.ilike(search_term),
            db.func.lower(Alumno.nombre).ilike(search_term_normalized),
            db.func.lower(Alumno.apellido).ilike(search_term_normalized)
        )
    ).limit(10).all()
    
    # Buscar representantes
    representantes = Representante.query.filter(
        db.or_(
            Representante.nombre.ilike(search_term),
            Representante.apellido.ilike(search_term),
            Representante.cedula.ilike(search_term),
            db.func.lower(Representante.nombre).ilike(search_term_normalized),
            db.func.lower(Representante.apellido).ilike(search_term_normalized)
        )
    ).limit(10).all()
    
    # Buscar instrumentos
    instrumentos = Instrumento.query.filter(
        db.or_(
            Instrumento.descripcion.ilike(search_term),
            Instrumento.marca.ilike(search_term),
            Instrumento.modelo.ilike(search_term),
            Instrumento.serial_fabrica.ilike(search_term),
            Instrumento.serial_inventario.ilike(search_term)
        )
    ).limit(10).all()
    
    # Buscar comodatos
    comodatos = Comodato.query.filter(
        Comodato.codigo_comodato.ilike(search_term)
    ).limit(10).all()
    
    return jsonify({
        'alumnos': alumnos_schema.dump(alumnos),
        'representantes': representantes_schema.dump(representantes),
        'instrumentos': instrumentos_schema.dump(instrumentos),
        'comodatos': comodatos_schema.dump(comodatos),
        'total': len(alumnos) + len(representantes) + len(instrumentos) + len(comodatos)
    }), 200

@api_bp.route('/utils/validar-serial/<serial>', methods=['GET'])
@jwt_required()
def validar_serial(serial):
    """
    Validar un serial de inventario
    """
    from app.models import Instrumento
    from app.utils.validators import Validators
    
    # Validar formato
    formato_valido = Validators.validate_serial_inventario(serial)
    
    # Verificar si ya existe
    existe = Instrumento.query.filter_by(serial_inventario=serial).first() is not None
    
    return jsonify({
        'serial': serial,
        'formato_valido': formato_valido,
        'existe_en_sistema': existe,
        'disponible': formato_valido and not existe
    }), 200
