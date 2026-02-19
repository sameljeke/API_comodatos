import secrets
import string
from datetime import datetime
from app.extensions import db
from app.models import Comodato, EstadoInstrumento, Instrumento

class CodeGenerator:
    @staticmethod
    def generate_codigo_comodato(correlativo, nucleo_codigo=None, year=None):
        """Genera código de comodato basado en el Excel"""
        year = year or datetime.now().year
        nucleo = nucleo_codigo or "GEN"
        return f"{nucleo}/{str(correlativo).zfill(4)}/{year}"
    
    @staticmethod
    def generate_serial_inventario():
        """Genera un serial de inventario único de 16 dígitos"""
        import random
        while True:
            serial = ''.join([str(random.randint(0, 9)) for _ in range(16)])
            # Verificar que no exista
            if not Instrumento.query.filter_by(serial_inventario=serial).first():
                return serial
    
    @staticmethod
    def get_next_correlativo(year=None):
        """Obtiene el siguiente número correlativo para comodatos"""
        year = year or datetime.now().year
        last_comodato = Comodato.query.filter(
            db.extract('year', Comodato.fecha_inicio) == year
        ).order_by(Comodato.correlativo.desc()).first()
        
        return last_comodato.correlativo + 1 if last_comodato else 1
    
    @staticmethod
    def generate_token(length=32):
        """Genera token seguro para verificación y recuperación"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

class ComodatoManager:
    @staticmethod
    def create_comodato(data):
        """Crea un nuevo comodato con validaciones"""
        from app.models import Instrumento, Alumno, Representante
        
        # Validar instrumento disponible
        instrumento = Instrumento.query.get(data['id_instr'])
        if not instrumento:
            raise ValueError("Instrumento no encontrado")
        
        if instrumento.estado_actual.nombre != 'disponible':
            raise ValueError(f"Instrumento no disponible. Estado: {instrumento.estado_actual.nombre}")
        
        # Validar alumno activo
        alumno = Alumno.query.get(data['id_alumno'])
        if not alumno or alumno.estado != 'activo':
            raise ValueError("Alumno no activo")
        
        # Validar representante
        representante = Representante.query.get(data['id_repr'])
        if not representante:
            raise ValueError("Representante no encontrado")
        
        # Generar correlativo y código
        correlativo = CodeGenerator.get_next_correlativo(
            data['fecha_inicio'].year if 'fecha_inicio' in data else None
        )
        
        codigo_comodato = CodeGenerator.generate_codigo_comodato(
            correlativo,
            nucleo_codigo="DN-GC-11-054",  # Ejemplo: Núcleo EL JUNKO
            year=data['fecha_inicio'].year if 'fecha_inicio' in data else None
        )
        
        # Crear comodato
        comodato = Comodato(
            correlativo=correlativo,
            codigo_comodato=codigo_comodato,
            **{k: v for k, v in data.items() if k not in ['correlativo', 'codigo_comodato']}
        )
        
        # Cambiar estado del instrumento
        estado_asignado = EstadoInstrumento.query.filter_by(nombre='asignado').first()
        instrumento.cambiar_estado(
            estado_asignado.id_estado_instr,
            f"Asignado a alumno {alumno.nombre_completo} via comodato {codigo_comodato}"
        )
        
        return comodato