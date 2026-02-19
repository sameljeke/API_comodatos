import pytest
from app import create_app
from app.extensions import db
from app.models import Usuario, Representante

@pytest.fixture
def app():
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    # Crear usuario de prueba
    usuario = Usuario(
        email='test@example.com',
        rol='admin',
        is_active=True
    )
    usuario.set_password('password123')
    
    representante = Representante(
        nombre='Test',
        apellido='User',
        cedula='V12345678'
    )
    
    usuario.representante = representante
    db.session.add(usuario)
    db.session.commit()
    
    # Login para obtener token
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    token = response.json['access_token']
    
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

def test_get_alumnos(client, auth_headers):
    response = client.get('/api/alumnos', headers=auth_headers)
    assert response.status_code == 200
    assert 'alumnos' in response.json

def test_create_alumno(client, auth_headers):
    response = client.post('/api/alumnos', json={
        'nombre': 'Juan',
        'apellido': 'Pérez',
        'cedula': 'V12345679',
        'programa': 'orquestal',
        'estado': 'activo'
    }, headers=auth_headers)
    
    assert response.status_code == 201
    assert response.json['nombre'] == 'Juan'

def test_get_instrumentos(client, auth_headers):
    response = client.get('/api/instrumentos', headers=auth_headers)
    assert response.status_code == 200
    assert 'instrumentos' in response.json

def test_get_comodatos(client, auth_headers):
    response = client.get('/api/comodatos', headers=auth_headers)
    assert response.status_code == 200
    assert 'comodatos' in response.json

def test_busqueda_rapida(client, auth_headers):
    response = client.get('/api/utils/buscar-rapido?q=test', headers=auth_headers)
    assert response.status_code == 200
    assert 'alumnos' in response.json
    assert 'representantes' in response.json
    assert 'instrumentos' in response.json
    assert 'comodatos' in response.json

def test_dashboard_estadisticas(client, auth_headers):
    response = client.get('/api/dashboard/estadisticas', headers=auth_headers)
    assert response.status_code == 200
    assert 'estadisticas' in response.json