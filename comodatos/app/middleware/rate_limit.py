from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # En producción usar Redis: "redis://localhost:6379"
    strategy="fixed-window"
)

def setup_rate_limiter(app):
    """Configura rate limiting basado en roles"""
    
    @limiter.request_filter
    def exempt_from_limits():
        # Eximir ciertas rutas de rate limiting
        from flask import request
        if request.endpoint in ['auth.login', 'auth.refresh', 'auth.forgot_password']:
            return False
        return True
    
    # Límites específicos por endpoint
    @app.before_request
    def configure_rate_limits():
        if request.endpoint:
            # Límites más estrictos para creación de recursos
            if request.endpoint in [
                'api.create_alumno',
                'api.create_instrumento',
                'api.create_comodato'
            ]:
                limiter.limit("10 per hour")
            
            # Límites más generosos para búsquedas
            elif request.endpoint in ['api.buscar_rapido']:
                limiter.limit("30 per minute")