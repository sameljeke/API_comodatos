#!/bin/bash

BASE_URL="http://localhost:5000"

echo "1. Probando registro..."
curl -s -X POST $BASE_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@localhost.com",
    "password": "Test123!",
    "nombre": "Juan",
    "apellido": "Perez",
    "cedula": "V12345678"
  }' | jq .

echo ""
echo "2. Probando login..."
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@localhost.com", "password": "Test123!"}')

echo $LOGIN_RESPONSE | jq .

# Extraer token
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ ! -z "$TOKEN" ]; then
    echo ""
    echo "3. Probando /me con token..."
    curl -s -H "Authorization: Bearer $TOKEN" \
      $BASE_URL/api/auth/me | jq .
    
    echo ""
    echo "4. Probando /medidas con token..."
    curl -s -H "Authorization: Bearer $TOKEN" \
      $BASE_URL/api/medidas | jq .
else
    echo "❌ No se pudo obtener token"
fi
