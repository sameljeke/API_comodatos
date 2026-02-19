import sys
import os
from app import create_app
from app.extensions import db
from datetime import date

def test_app():
    print("🔍 INICIANDO PRUEBAS RÁPIDAS")
    print("=" * 50)
    
    try:
        print("1. Creando aplicación en modo testing...")
        app = create_app('testing')
        print("   ✅ Aplicación creada exitosamente")
        
        with app.app_context():
            print("2. Probando conexión a base de datos SQLite...")
            db.create_all()
            print("   ✅ Base de datos creada en memoria")
            
            print("3. Probando importación de modelos...")
            from app.models import (
                Usuario, Representante, Alumno, Medida,
                EstadoInstrumento, Instrumento, Accesorio,
                Comodato, HistorialEstadoInstr, VerificacionEmail,
                RecuperacionPass
            )
            print("   ✅ Todos los modelos importados correctamente")
            
            print("4. Probando creación de tablas...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"   📊 Tablas creadas: {', '.join(tables)}")
            
            print("5. Probando inserción básica...")
            
            # Crear medida de prueba
            medida = Medida(nombre="4/4", descripcion="Tamaño completo")
            db.session.add(medida)
            db.session.flush()
            
            # Crear estado de prueba
            estado = EstadoInstrumento(nombre="disponible", descripcion="Disponible")
            db.session.add(estado)
            db.session.flush()
            
            # Crear usuario de prueba
            usuario = Usuario(
                email="test@test.com",
                rol="admin",
                is_active=True
            )
            usuario.set_password("Test123!")
            db.session.add(usuario)
            db.session.flush()
            
            # Crear representante de prueba
            representante = Representante(
                id_usuario=usuario.id_usuario,
                nombre="Test",
                apellido="User",
                cedula="V12345678",
                telefono="04121234567",
                direccion="Dirección de prueba"
            )
            db.session.add(representante)
            db.session.flush()
            
            # Crear alumno de prueba
            alumno = Alumno(
                id_repr=representante.id_repr,
                nombre="Juan",
                apellido="Pérez",
                cedula="V87654321",
                fecha_nacimiento=date(2010, 1, 1),
                programa="orquestal",
                estado="activo"
            )
            db.session.add(alumno)
            db.session.flush()
            
            # Crear instrumento de prueba
            instrumento = Instrumento(
                descripcion="VIOLIN",
                marca="Test",
                modelo="Test Model",
                id_medida=medida.id_medida,
                color="Marrón",
                serial_fabrica="TEST123",
                serial_inventario="1234567890123456",
                id_estado_instr=estado.id_estado_instr,
                fecha_adquisicion=date.today()
            )
            db.session.add(instrumento)
            db.session.flush()
            
            db.session.commit()
            print("   ✅ Datos de prueba insertados correctamente")
            
            print("6. Probando consultas...")
            usuarios_count = Usuario.query.count()
            representantes_count = Representante.query.count()
            alumnos_count = Alumno.query.count()
            instrumentos_count = Instrumento.query.count()
            
            print(f"   📊 Usuarios: {usuarios_count}")
            print(f"   📊 Representantes: {representantes_count}")
            print(f"   📊 Alumnos: {alumnos_count}")
            print(f"   📊 Instrumentos: {instrumentos_count}")
            
            print("7. Probando relaciones...")
            if representante.alumnos.first():
                print(f"   ✅ Representante tiene alumnos: {representante.alumnos.count()}")
            
            if instrumento.medida:
                print(f"   ✅ Instrumento tiene medida: {instrumento.medida.nombre}")
            
            if instrumento.estado_actual:
                print(f"   ✅ Instrumento tiene estado: {instrumento.estado_actual.nombre}")
            
            print("8. Probando blueprints...")
            # CORRECCIÓN: usar blueprints (con s) en lugar de blueprint
            blueprints = list(app.blueprints.keys())
            print(f"   📋 Blueprints registrados: {', '.join(blueprints)}")
            
            print("9. Probando rutas de autenticación...")
            from app.auth.routes import auth_bp
            print("   ✅ Módulo de autenticación cargado correctamente")
            
            print("10. Probando rutas de API...")
            from app.api import api_bp
            print("   ✅ Módulo de API cargado correctamente")
            
            print("\n" + "=" * 50)
            print("✅ ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
            print("=" * 50)
            print("\n🚀 La aplicación está lista para ejecutarse con:")
            print("   flask run --debug")
            print("\n📚 Documentación disponible en:")
            print("   http://localhost:5000/api/docs/")
            
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_app()
    sys.exit(0 if success else 1)