from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Importar todos los módulos de la API
from . import usuarios
from . import representantes
from . import alumnos
from . import instrumentos
from . import comodatos
from . import utils