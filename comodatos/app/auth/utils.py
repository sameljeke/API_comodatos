from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def require_roles(*roles):
    """
    Decorador para requerir roles específicos
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('rol')
            
            if user_role not in roles:
                return jsonify({
                    'error': 'No autorizado',
                    'message': f'Se requiere uno de los roles: {roles}'
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def create_tokens(user):
    """Crea tokens de acceso y refresh"""
    from flask_jwt_extended import create_access_token, create_refresh_token
    
    access_token = create_access_token(
        identity=user.id_usuario,
        additional_claims={
            'rol': user.rol,
            'email': user.email
        }
    )
    refresh_token = create_refresh_token(identity=user.id_usuario)
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }
