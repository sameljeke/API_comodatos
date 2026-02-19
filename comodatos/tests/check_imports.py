# check_imports.py
import os
import glob

print("🔍 VERIFICANDO IMPORTACIONES DE require_roles")
print("=" * 50)

# Buscar todos los archivos Python en app/api/
api_files = glob.glob("app/api/*.py")

for file in api_files:
    with open(file, 'r') as f:
        content = f.read()
        
        # Verificar si usa require_roles
        if '@require_roles' in content:
            print(f"\n📄 {file}:")
            
            # Verificar si lo importa
            if 'from app.auth.utils import require_roles' in content:
                print("   ✅ require_roles IMPORTADO correctamente")
            else:
                print("   ❌ FALTA: from app.auth.utils import require_roles")
                
                # Sugerir la línea a agregar
                print("   📝 Agregar: from app.auth.utils import require_roles")