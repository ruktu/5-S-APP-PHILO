#!/bin/bash
# Arranca flex.ruktu.com (postgres + backend + nginx via Docker Compose).
# Uso: ./arrancar.sh

cd "$(dirname "$0")"

if [ -d ".git" ]; then
    echo "Actualizando codigo desde git..."
    git pull || echo "ADVERTENCIA: git pull fallo, sigo con el codigo actual en disco."
fi

echo ""
echo "==========================================="
echo "  flex.ruktu.com · levantando contenedores"
echo "==========================================="
echo ""

exec docker compose up --build
