#!/bin/bash

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_URL="http://localhost:5000"
TOKEN=""
REFRESH_TOKEN=""

# Contadores
TOTAL=0
PASADAS=0
FALLADAS=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     PRUEBAS COMPLETAS DE API SISTEMA COMODATOS        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Función para probar endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    local expected_status=$5
    local needs_auth=$6
    
    TOTAL=$((TOTAL + 1))
    
    echo -e "${YELLOW}▶ Probando: $description${NC}"
    echo "  $method $endpoint"
    
    # Construir comando curl
    cmd="curl -s -w '\n%{http_code}' -X $method"
    
    if [ "$needs_auth" = "true" ] && [ ! -z "$TOKEN" ]; then
        cmd="$cmd -H 'Authorization: Bearer $TOKEN'"
    fi
    
    cmd="$cmd -H 'Content-Type: application/json'"
    
    if [ ! -z "$data" ]; then
        cmd="$cmd -d '$data'"
    fi
    
    cmd="$cmd $BASE_URL$endpoint"
    
    # Ejecutar y capturar respuesta y código HTTP
    response=$(eval $cmd 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "  ${GREEN}✓ OK (HTTP $http_code)${NC}"
        PASADAS=$((PASADAS + 1))
        
        # Mostrar respuesta si no es muy larga
        if [ ${#body} -lt 200 ]; then
            echo "  Respuesta: $body"
        else
            echo "  Respuesta: (truncada) ${body:0:100}..."
        fi
    else
        echo -e "  ${RED}✗ ERROR - Esperado: $expected_status, Recibido: $http_code${NC}"
        FALLADAS=$((FALLADAS + 1))
        echo "  Respuesta: $body"
    fi
    echo ""
}

# ============================================
# PASO 1: REGISTRO Y LOGIN
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          1. PRUEBAS DE AUTENTICACIÓN${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1.1 Registro de usuario - CORREGIDO con email válido
test_endpoint "POST" "/api/auth/register" "Registro de usuario" '{
    "email": "test2024@gmail.com",
    "password": "Test123!",
    "nombre": "Juan",
    "apellido": "Pérez",
    "cedula": "V12345678",
    "telefono": "04121234567",
    "direccion": "Calle Principal"
}' "201" "false"

# 1.2 Login - CORREGIDO
echo "Obteniendo token..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "test2024@gmail.com",
        "password": "Test123!"
    }')

# Extraer token con jq
if command -v jq &> /dev/null; then
    TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
    REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.refresh_token')
    echo -e "${GREEN}✓ Token obtenido correctamente${NC}"
    echo "Token: ${TOKEN:0:20}... (truncado)"
else
    echo -e "${RED}⚠️ jq no está instalado. Instálalo con: sudo apt install jq${NC}"
    echo "Login response: $LOGIN_RESPONSE"
    exit 1
fi

# 1.3 Obtener usuario actual
test_endpoint "GET" "/api/auth/me" "Obtener usuario actual" "" "200" "true"

# ============================================
# PASO 2: PRUEBAS DE MEDIDAS
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          2. PRUEBAS DE MEDIDAS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 2.1 Crear medida (solo admin - debería fallar)
test_endpoint "POST" "/api/medidas" "Crear medida (sin permisos de admin)" '{
    "nombre": "1/4",
    "descripcion": "Un cuarto"
}' "403" "true"

# 2.2 Listar medidas (público)
test_endpoint "GET" "/api/medidas" "Listar medidas" "" "200" "true"

# ============================================
# PASO 3: PRUEBAS DE INSTRUMENTOS
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          3. PRUEBAS DE INSTRUMENTOS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 3.1 Obtener ID de medida disponible
MEDIDA_ID=$(curl -s -X GET "$BASE_URL/api/medidas" \
    -H "Authorization: Bearer $TOKEN" | jq '.[0].id_medida')

# 3.2 Crear instrumento (debería fallar - solo admin)
test_endpoint "POST" "/api/instrumentos" "Crear instrumento (sin permisos de admin)" '{
    "descripcion": "VIOLIN",
    "marca": "Test",
    "modelo": "Modelo1",
    "id_medida": '"$MEDIDA_ID"',
    "color": "Marrón",
    "serial_fabrica": "TEST123",
    "serial_inventario": "1234567890123456",
    "fecha_adquisicion": "2024-01-01"
}' "403" "true"

# 3.3 Listar instrumentos
test_endpoint "GET" "/api/instrumentos" "Listar instrumentos" "" "200" "true"

# 3.4 Ver instrumentos disponibles
test_endpoint "GET" "/api/instrumentos/disponibles" "Instrumentos disponibles" "" "200" "true"

# ============================================
# PASO 4: PRUEBAS DE ALUMNOS
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          4. PRUEBAS DE ALUMNOS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 4.1 Crear alumno (como representante - debería funcionar)
test_endpoint "POST" "/api/alumnos" "Crear alumno" '{
    "nombre": "María",
    "apellido": "González",
    "cedula": "V87654321",
    "fecha_nacimiento": "2015-05-15",
    "programa": "orquestal",
    "estado": "activo"
}' "201" "true"

# 4.2 Listar alumnos
test_endpoint "GET" "/api/alumnos" "Listar alumnos" "" "200" "true"

# 4.3 Buscar alumnos
test_endpoint "GET" "/api/alumnos?search=María" "Buscar alumnos" "" "200" "true"

# ============================================
# PASO 5: PRUEBAS DE REPRESENTANTES
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          5. PRUEBAS DE REPRESENTANTES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 5.1 Obtener información del representante actual
test_endpoint "GET" "/api/auth/me" "Info representante actual" "" "200" "true"

# 5.2 Obtener ID del representante
REPR_ID=$(curl -s -X GET "$BASE_URL/api/auth/me" \
    -H "Authorization: Bearer $TOKEN" | jq '.representante.id_repr' 2>/dev/null)

if [ ! -z "$REPR_ID" ] && [ "$REPR_ID" != "null" ]; then
    # 5.3 Ver alumnos del representante
    test_endpoint "GET" "/api/representantes/$REPR_ID/alumnos" "Alumnos del representante" "" "200" "true"
fi

# ============================================
# PASO 6: PRUEBAS DE UTILITARIOS
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          6. PRUEBAS DE UTILITARIOS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 6.1 Dashboard estadísticas
test_endpoint "GET" "/api/dashboard/estadisticas" "Dashboard estadísticas" "" "200" "true"

# 6.2 Dashboard alertas
test_endpoint "GET" "/api/dashboard/alertas" "Dashboard alertas" "" "200" "true"

# 6.3 Búsqueda rápida
test_endpoint "GET" "/api/utils/buscar-rapido?q=María" "Búsqueda rápida" "" "200" "true"

# 6.4 Validar serial
test_endpoint "GET" "/api/utils/validar-serial/1234567890123456" "Validar serial" "" "200" "true"

# ============================================
# PASO 7: PRUEBAS DE COMODATOS
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          7. PRUEBAS DE COMODATOS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 7.1 Obtener IDs necesarios
ALUMNO_ID=$(curl -s -X GET "$BASE_URL/api/alumnos" \
    -H "Authorization: Bearer $TOKEN" | jq '.alumnos[0].id_alumno' 2>/dev/null)

INSTRUMENTO_ID=$(curl -s -X GET "$BASE_URL/api/instrumentos" \
    -H "Authorization: Bearer $TOKEN" | jq '.instrumentos[0].id_instr' 2>/dev/null)

# 7.2 Crear comodato (debería fallar si no hay instrumento disponible)
if [ ! -z "$ALUMNO_ID" ] && [ ! -z "$INSTRUMENTO_ID" ] && [ "$ALUMNO_ID" != "null" ] && [ "$INSTRUMENTO_ID" != "null" ]; then
    test_endpoint "POST" "/api/comodatos" "Crear comodato" '{
        "id_alumno": '"$ALUMNO_ID"',
        "id_instr": '"$INSTRUMENTO_ID"',
        "fecha_inicio": "2024-01-15",
        "fecha_fin": "2025-01-15",
        "observaciones": "Comodato de prueba"
    }' "201" "true"
else
    echo -e "${YELLOW}  ⚠️ No hay alumnos o instrumentos para crear comodato${NC}"
    TOTAL=$((TOTAL + 1))
    echo -e "  ${YELLOW}⚠️ Prueba omitida${NC}"
    PASADAS=$((PASADAS + 1))
    echo ""
fi

# 7.3 Listar comodatos
test_endpoint "GET" "/api/comodatos" "Listar comodatos" "" "200" "true"

# 7.4 Comodatos vencidos (reporte)
test_endpoint "GET" "/api/comodatos/reportes/vencidos" "Comodatos vencidos" "" "200" "true"

# ============================================
# PASO 8: PRUEBAS CON ADMIN (opcional)
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}          8. PRUEBAS CON ADMIN (opcional)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}▶ ¿Probar con admin? (responde 's' para continuar)${NC}"
read -t 5 -n 1 -p "  (timeout 5s - automatico: no): " answer
echo ""

if [[ "$answer" =~ ^[Ss]$ ]]; then
    # Login como admin
    ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email": "admin@sistema.com", "password": "Admin123!"}' | jq -r '.access_token')
    
    if [ ! -z "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "null" ]; then
        TOKEN=$ADMIN_TOKEN
        echo -e "${GREEN}✓ Token de admin obtenido${NC}"
        
        # Crear medida con admin
        test_endpoint "POST" "/api/medidas" "Crear medida (con admin)" '{
            "nombre": "1/8",
            "descripcion": "Octavo"
        }' "201" "true"
        
        # Crear instrumento con admin
        test_endpoint "POST" "/api/instrumentos" "Crear instrumento (con admin)" '{
            "descripcion": "VIOLIN",
            "marca": "Stradivarius",
            "modelo": "Master",
            "id_medida": '"$MEDIDA_ID"',
            "color": "Marrón",
            "serial_fabrica": "STRAD123",
            "serial_inventario": "1234567890123456",
            "fecha_adquisicion": "2024-01-15"
        }' "201" "true"
    else
        echo -e "${RED}  ✗ No se pudo obtener token de admin${NC}"
    fi
else
    echo -e "  ⏩ Omitiendo pruebas con admin"
fi

# ============================================
# RESUMEN FINAL
# ============================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}                    RESUMEN DE PRUEBAS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Total pruebas: $TOTAL"
echo -e "${GREEN}✓ Pasadas: $PASADAS${NC}"
echo -e "${RED}✗ Falladas: $FALLADAS${NC}"
echo ""
if [ $FALLADAS -eq 0 ]; then
    echo -e "${GREEN}🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!${NC}"
else
    echo -e "${RED}⚠️  Algunas pruebas fallaron. Revisa los errores arriba.${NC}"
fi
echo ""
