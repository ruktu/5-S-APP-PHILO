#!/bin/bash
# Arranca flex.ruktu.com dentro de una sesión de `screen` llamada "flex" —
# pensado para dispararse solo al reiniciar la máquina (ver el @reboot en el
# crontab de este usuario) y dejar el stack corriendo aunque no haya ninguna
# terminal abierta.
#
# A diferencia del script equivalente de CRM VISAGE, aquí no hace falta un
# loop manual esperando a Postgres: todo el stack (postgres+backend+nginx) es
# un solo docker-compose, y el propio compose ya espera a que Postgres esté
# "healthy" antes de arrancar el backend (ver docker-compose.yml).
#
# Prueba manual: bash scripts/iniciar_en_boot.sh && screen -r flex

set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESION="flex"

if screen -list | grep -q "\.${SESION}[[:space:]]"; then
    echo "[iniciar_en_boot] Ya hay una sesión de screen '$SESION' corriendo — no se hace nada."
    exit 0
fi

screen -dmS "$SESION" bash -c "cd \"$ROOT_DIR\" && exec ./arrancar.sh"
echo "[iniciar_en_boot] Sesión '$SESION' iniciada. Ver con: screen -r $SESION"
