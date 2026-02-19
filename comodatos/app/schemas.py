from app.extensions import db, ma
from marshmallow import fields, validate, validates, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
import re
from datetime import datetime
from app.models import (
    Usuario, Representante, Alumno, Medida, EstadoInstrumento,
    Instrumento, Accesorio, Comodato, HistorialEstadoInstr
)

class UsuarioSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Usuario
        sqla_session = db.session
        load_instance = True
        exclude = ('password_hash',)
    
    email = fields.Email(required=True)
    rol = fields.String(validate=validate.OneOf(['admin', 'representante', 'invitado']))
    password = fields.String(load_only=True, required=True, 
                           validate=validate.Length(min=8))

class RepresentanteSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Representante
        sqla_session = db.session
        load_instance = True
        include_fk = True
    
    nombre = fields.String(required=True, validate=validate.Length(min=2, max=100))
    apellido = fields.String(required=True, validate=validate.Length(min=2, max=100))
    cedula = fields.String(required=True, validate=validate.Length(min=6, max=20))
    telefono = fields.String(validate=validate.Length(max=20))
    
    @validates('cedula')
    def validate_cedula(self, value):
        if not re.match(r'^[VEJPGvejpg]\d{5,9}$', value):
            raise ValidationError('Formato de cédula inválido')

class AlumnoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Alumno
        sqla_session = db.session
        load_instance = True
        include_fk = True
    
    nombre = fields.String(required=True, validate=validate.Length(min=2, max=100))
    apellido = fields.String(required=True, validate=validate.Length(min=2, max=100))
    cedula = fields.String(required=True, validate=validate.Length(min=6, max=20))
    fecha_nacimiento = fields.Date()
    programa = fields.String(validate=validate.OneOf([
        'iniciacion', 'coral', 'orquestal', 'alma_llanera', 'otros'
    ]))
    estado = fields.String(validate=validate.OneOf(['activo', 'inactivo']))
    
    edad = fields.Method('calculate_age')
    
    def calculate_age(self, obj):
        return obj.edad if hasattr(obj, 'edad') else None

class MedidaSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Medida
        sqla_session = db.session
        load_instance = True
    
    nombre = fields.String(required=True, validate=validate.Length(max=50))
    descripcion = fields.String(validate=validate.Length(max=200))

class EstadoInstrumentoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = EstadoInstrumento
        sqla_session = db.session
        load_instance = True
    
    nombre = fields.String(required=True, validate=validate.OneOf([
        'disponible', 'asignado', 'no_operativo', 'mantenimiento', 'baja'
    ]))

class InstrumentoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Instrumento
        sqla_session = db.session
        load_instance = True
        include_fk = True
    
    descripcion = fields.String(required=True, validate=validate.Length(max=100))
    marca = fields.String(validate=validate.Length(max=100))
    modelo = fields.String(validate=validate.Length(max=100))
    color = fields.String(validate=validate.Length(max=50))
    serial_fabrica = fields.String(validate=validate.Length(max=100))
    serial_inventario = fields.String(required=True, validate=validate.Length(equal=16))
    fecha_adquisicion = fields.Date()
    
    @validates('serial_inventario')
    def validate_serial_inventario(self, value):
        if not re.match(r'^\d{16}$', value):
            raise ValidationError('El serial de inventario debe tener exactamente 16 dígitos')

class AccesorioSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Accesorio
        sqla_session = db.session
        load_instance = True
        include_fk = True
    
    nombre = fields.String(required=True, validate=validate.Length(max=100))
    descripcion = fields.String()
    serial = fields.String(validate=validate.Length(max=50))
    estado = fields.String(validate=validate.OneOf([
        'bueno', 'regular', 'malo', 'perdido'
    ]))

class ComodatoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Comodato
        sqla_session = db.session
        load_instance = True
        include_fk = True
    
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    fecha_recepcion = fields.Date()
    estado = fields.String(validate=validate.OneOf([
        'activo', 'finalizado', 'cancelado', 'renovado'
    ]))
    observaciones = fields.String()
    correlativo = fields.Integer()
    codigo_comodato = fields.String()
    
    dias_restantes = fields.Method('get_dias_restantes')
    esta_vencido = fields.Method('get_esta_vencido')
    
    def get_dias_restantes(self, obj):
        return obj.dias_restantes if hasattr(obj, 'dias_restantes') else None
    
    def get_esta_vencido(self, obj):
        return obj.esta_vencido if hasattr(obj, 'esta_vencido') else None
    
    @validates('fecha_fin')
    def validate_fecha_fin(self, value, **kwargs):
        fecha_inicio = kwargs.get('data', {}).get('fecha_inicio')
        if fecha_inicio and value <= fecha_inicio:
            raise ValidationError('La fecha de fin debe ser posterior a la fecha de inicio')

class HistorialEstadoInstrSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = HistorialEstadoInstr
        sqla_session = db.session
        load_instance = True
        include_fk = True
    
    fecha = fields.DateTime()
    observacion = fields.String()

# Instancias de los esquemas
usuario_schema = UsuarioSchema()
usuarios_schema = UsuarioSchema(many=True)
representante_schema = RepresentanteSchema()
representantes_schema = RepresentanteSchema(many=True)
alumno_schema = AlumnoSchema()
alumnos_schema = AlumnoSchema(many=True)
medida_schema = MedidaSchema()
medidas_schema = MedidaSchema(many=True)
estado_instrumento_schema = EstadoInstrumentoSchema()
estados_instrumento_schema = EstadoInstrumentoSchema(many=True)
instrumento_schema = InstrumentoSchema()
instrumentos_schema = InstrumentoSchema(many=True)
accesorio_schema = AccesorioSchema()
accesorios_schema = AccesorioSchema(many=True)
comodato_schema = ComodatoSchema()
comodatos_schema = ComodatoSchema(many=True)
historial_estado_schema = HistorialEstadoInstrSchema()
historiales_estado_schema = HistorialEstadoInstrSchema(many=True)