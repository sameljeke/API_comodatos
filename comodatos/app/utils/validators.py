import re
from datetime import datetime, date
from email_validator import validate_email, EmailNotValidError
from flask import current_app

class Validators:
    @staticmethod
    def validate_email(email):
        """Valida y normaliza un email"""
        try:
            v = validate_email(email)
            return v.normalized
        except EmailNotValidError as e:
            raise ValueError(f"Email inválido: {str(e)}")
    
    @staticmethod
    def validate_cedula(cedula):
        """Valida cédula venezolana"""
        if not re.match(r'^[VEJPGvejpg]\d{5,9}$', cedula):
            return False
        return True
    
    @staticmethod
    def validate_serial_inventario(serial):
        """Valida serial de inventario de 16 dígitos"""
        return bool(re.match(r'^\d{16}$', str(serial)))
    
    @staticmethod
    def validate_fechas_comodato(fecha_inicio, fecha_fin):
        """Valida que las fechas del comodato sean coherentes"""
        if fecha_fin <= fecha_inicio:
            return False, "La fecha de fin debe ser posterior a la fecha de inicio"
        
        if fecha_inicio < date.today():
            return False, "La fecha de inicio no puede ser en el pasado"
        
        # Máximo 2 años de comodato
        max_fecha = date.fromordinal(fecha_inicio.toordinal() + 730)  # 2 años
        if fecha_fin > max_fecha:
            return False, "El comodato no puede exceder 2 años"
        
        return True, ""
    
    @staticmethod
    def sanitize_input(text):
        """Limpia entrada de texto para prevenir XSS"""
        import bleach
        if not text:
            return text
        return bleach.clean(text, tags=[], strip=True)