from datetime import datetime
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
import re

class Usuario(db.Model):
    __tablename__ = 'usuario'
    
    id_usuario = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.Enum('admin', 'representante', 'invitado'), 
                   default='invitado', nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_ultimo_login = db.Column(db.DateTime)
    
    # Relaciones
    representante = db.relationship('Representante', backref='usuario', 
                                   uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id_usuario': self.id_usuario,
            'email': self.email,
            'rol': self.rol,
            'is_active': self.is_active,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'representante': self.representante.to_dict() if hasattr(self, 'representante') and self.representante else None
        }

class Representante(db.Model):
    __tablename__ = 'representante'
    
    id_repr = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), 
                          unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False, index=True)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.Text)
    
    # Relaciones
    alumnos = db.relationship('Alumno', backref='representante', 
                             lazy='dynamic', cascade='all, delete-orphan')
    comodatos = db.relationship('Comodato', backref='representante', 
                               lazy='dynamic')
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    def to_dict(self):
        return {
            'id_repr': self.id_repr,
            'id_usuario': self.id_usuario,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'cedula': self.cedula,
            'telefono': self.telefono,
            'direccion': self.direccion,
            'nombre_completo': self.nombre_completo
        }

class Alumno(db.Model):
    __tablename__ = 'alumno'
    
    id_alumno = db.Column(db.Integer, primary_key=True)
    id_repr = db.Column(db.Integer, db.ForeignKey('representante.id_repr'), 
                       nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False, index=True)
    fecha_nacimiento = db.Column(db.Date)
    programa = db.Column(db.Enum('iniciacion', 'coral', 'orquestal', 
                                'alma_llanera', 'otros'), default='iniciacion')
    estado = db.Column(db.Enum('activo', 'inactivo'), default='activo')
    
    # Relaciones
    comodatos = db.relationship('Comodato', backref='alumno', 
                               lazy='dynamic')
    
    @property
    def edad(self):
        if self.fecha_nacimiento:
            today = datetime.utcnow().date()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < 
                (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None
    
    def to_dict(self):
        return {
            'id_alumno': self.id_alumno,
            'id_repr': self.id_repr,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'cedula': self.cedula,
            'fecha_nacimiento': self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else None,
            'programa': self.programa,
            'estado': self.estado,
            'edad': self.edad,
            'nombre_completo': f"{self.nombre} {self.apellido}"
        }

class Medida(db.Model):
    __tablename__ = 'medida'
    
    id_medida = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    
    # Relaciones
    instrumentos = db.relationship('Instrumento', backref='medida', 
                                  lazy='dynamic')
    
    def to_dict(self):
        return {
            'id_medida': self.id_medida,
            'nombre': self.nombre,
            'descripcion': self.descripcion
        }

class EstadoInstrumento(db.Model):
    __tablename__ = 'estado_instrumento'
    
    id_estado_instr = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Enum('disponible', 'asignado', 'no_operativo', 
                              'mantenimiento', 'baja'), 
                      default='disponible', nullable=False)
    descripcion = db.Column(db.String(200))
    
    # Relaciones
    instrumentos = db.relationship('Instrumento', backref='estado_actual', 
                                  lazy='dynamic')
    historiales = db.relationship('HistorialEstadoInstr', backref='estado', 
                                 lazy='dynamic')
    
    def to_dict(self):
        return {
            'id_estado_instr': self.id_estado_instr,
            'nombre': self.nombre,
            'descripcion': self.descripcion
        }

class Instrumento(db.Model):
    __tablename__ = 'instrumento'
    
    id_instr = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(100), nullable=False)  # VIOLIN, VIOLA, etc.
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    id_medida = db.Column(db.Integer, db.ForeignKey('medida.id_medida'))
    color = db.Column(db.String(50))
    serial_fabrica = db.Column(db.String(100))
    serial_inventario = db.Column(db.String(16), unique=True, nullable=False, index=True)
    id_estado_instr = db.Column(db.Integer, db.ForeignKey('estado_instrumento.id_estado_instr'), 
                               nullable=False)
    fecha_adquisicion = db.Column(db.Date)
    observaciones = db.Column(db.Text)
    
    # Validación del serial de inventario
    @staticmethod
    def validate_serial_inventario(serial):
        if not re.match(r'^\d{16}$', str(serial)):
            raise ValueError('El serial de inventario debe tener 16 dígitos')
        return True
    
    # Relaciones
    accesorios = db.relationship('Accesorio', backref='instrumento', 
                                lazy='dynamic', cascade='all, delete-orphan')
    comodatos = db.relationship('Comodato', backref='instrumento', 
                               lazy='dynamic')
    historiales_estado = db.relationship('HistorialEstadoInstr', backref='instrumento', 
                                        lazy='dynamic', cascade='all, delete-orphan')
    
    def cambiar_estado(self, nuevo_estado_id, observacion=None):
        """Cambia el estado del instrumento y registra en historial"""
        historial = HistorialEstadoInstr(
            id_instr=self.id_instr,
            id_estado_instr=nuevo_estado_id,
            observacion=observacion
        )
        self.id_estado_instr = nuevo_estado_id
        db.session.add(historial)
        return historial
    
    def to_dict(self):
        return {
            'id_instr': self.id_instr,
            'descripcion': self.descripcion,
            'marca': self.marca,
            'modelo': self.modelo,
            'id_medida': self.id_medida,
            'color': self.color,
            'serial_fabrica': self.serial_fabrica,
            'serial_inventario': self.serial_inventario,
            'id_estado_instr': self.id_estado_instr,
            'fecha_adquisicion': self.fecha_adquisicion.isoformat() if self.fecha_adquisicion else None,
            'observaciones': self.observaciones,
            'estado_actual': self.estado_actual.to_dict() if self.estado_actual else None,
            'medida': self.medida.to_dict() if self.medida else None
        }

class Accesorio(db.Model):
    __tablename__ = 'accesorio'
    
    id_acc = db.Column(db.Integer, primary_key=True)
    id_instr = db.Column(db.Integer, db.ForeignKey('instrumento.id_instr'), 
                        nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    serial = db.Column(db.String(50))
    estado = db.Column(db.Enum('bueno', 'regular', 'malo', 'perdido'), 
                      default='bueno')
    
    def to_dict(self):
        return {
            'id_acc': self.id_acc,
            'id_instr': self.id_instr,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'serial': self.serial,
            'estado': self.estado
        }

class Comodato(db.Model):
    __tablename__ = 'comodato'
    
    id_comodato = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey('alumno.id_alumno'), 
                         nullable=False)
    id_instr = db.Column(db.Integer, db.ForeignKey('instrumento.id_instr'), 
                        nullable=False)
    id_repr = db.Column(db.Integer, db.ForeignKey('representante.id_repr'), 
                       nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    fecha_recepcion = db.Column(db.Date)
    estado = db.Column(db.Enum('activo', 'finalizado', 'cancelado', 
                              'renovado'), default='activo')
    observaciones = db.Column(db.Text)
    correlativo = db.Column(db.Integer, unique=True, index=True)
    codigo_comodato = db.Column(db.String(50), unique=True, index=True)
    
    # Índices compuestos
    __table_args__ = (
        db.Index('idx_comodato_alumno_estado', 'id_alumno', 'estado'),
        db.Index('idx_comodato_instr_estado', 'id_instr', 'estado'),
        db.Index('idx_comodato_fechas', 'fecha_inicio', 'fecha_fin'),
    )
    
    @property
    def dias_restantes(self):
        """Calcula días restantes para la fecha de fin"""
        if self.estado != 'activo':
            return 0
        
        from datetime import date
        hoy = date.today()
        if hoy > self.fecha_fin:
            return 0
        return (self.fecha_fin - hoy).days
    
    @property
    def esta_vencido(self):
        """Verifica si el comodato está vencido"""
        from datetime import date
        return self.estado == 'activo' and date.today() > self.fecha_fin
    
    def finalizar(self, fecha_recepcion=None, observaciones=None):
        """Finaliza el comodato"""
        self.estado = 'finalizado'
        self.fecha_recepcion = fecha_recepcion or datetime.utcnow().date()
        if observaciones:
            self.observaciones = f"{self.observaciones or ''}\nFinalizado: {observaciones}"
        
        # Liberar el instrumento
        if self.instrumento:
            estado_disponible = EstadoInstrumento.query.filter_by(
                nombre='disponible').first()
            if estado_disponible:
                self.instrumento.cambiar_estado(
                    estado_disponible.id_estado_instr,
                    'Instrumento devuelto por finalización de comodato'
                )
    
    def to_dict(self):
        return {
            'id_comodato': self.id_comodato,
            'id_alumno': self.id_alumno,
            'id_instr': self.id_instr,
            'id_repr': self.id_repr,
            'fecha_inicio': self.fecha_inicio.isoformat(),
            'fecha_fin': self.fecha_fin.isoformat(),
            'fecha_recepcion': self.fecha_recepcion.isoformat() if self.fecha_recepcion else None,
            'estado': self.estado,
            'observaciones': self.observaciones,
            'correlativo': self.correlativo,
            'codigo_comodato': self.codigo_comodato,
            'dias_restantes': self.dias_restantes,
            'esta_vencido': self.esta_vencido,
            'alumno': self.alumno.to_dict() if self.alumno else None,
            'instrumento': self.instrumento.to_dict() if self.instrumento else None,
            'representante': self.representante.to_dict() if self.representante else None
        }

class HistorialEstadoInstr(db.Model):
    __tablename__ = 'historial_estado_instr'
    
    id_hist = db.Column(db.Integer, primary_key=True)
    id_instr = db.Column(db.Integer, db.ForeignKey('instrumento.id_instr'), 
                        nullable=False)
    id_estado_instr = db.Column(db.Integer, db.ForeignKey('estado_instrumento.id_estado_instr'), 
                               nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    observacion = db.Column(db.Text)
    
    __table_args__ = (
        db.Index('idx_historial_instr_fecha', 'id_instr', 'fecha'),
    )
    
    def to_dict(self):
        return {
            'id_hist': self.id_hist,
            'id_instr': self.id_instr,
            'id_estado_instr': self.id_estado_instr,
            'fecha': self.fecha.isoformat(),
            'observacion': self.observacion,
            'estado': self.estado.to_dict() if self.estado else None
        }

class VerificacionEmail(db.Model):
    __tablename__ = 'verificacion_email'
    
    id_verificacion = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), 
                          nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_verificacion = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id_verificacion': self.id_verificacion,
            'id_usuario': self.id_usuario,
            'token': self.token,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'fecha_verificacion': self.fecha_verificacion.isoformat() if self.fecha_verificacion else None,
            'expirado': self.expirado
        }
    
    @property
    def expirado(self):
        from datetime import datetime, timedelta
        return datetime.utcnow() > self.fecha_creacion + timedelta(hours=24)

class RecuperacionPass(db.Model):
    __tablename__ = 'recuperacion_pass'
    
    id_recuperacion = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), 
                          nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_uso = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id_recuperacion': self.id_recuperacion,
            'id_usuario': self.id_usuario,
            'token': self.token,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'fecha_uso': self.fecha_uso.isoformat() if self.fecha_uso else None,
            'expirado': self.expirado
        }
    
    @property
    def expirado(self):
        from datetime import datetime, timedelta
        return datetime.utcnow() > self.fecha_creacion + timedelta(hours=1)