#!/usr/bin/env bash
# Despliegue del contenedor en el VPS de la cátedra (C-09).
#
# Se ejecuta EN el servidor, desde la raíz del repositorio ya transferido.
# Construye la imagen, elimina el contenedor anterior si existe y lo vuelve a
# correr con el archivo de variables del servidor.
#
# Variables que lee (todas obligatorias salvo las marcadas como opcionales):
#   IMAGEN           nombre/tag de la imagen a construir y correr
#   CONTENEDOR       nombre del contenedor de la aplicación
#   PUERTO_PUBLICO   puerto público de la cátedra (se publica hacia el 8000)
#   HOST_BD          host de PostgreSQL visto desde el contenedor
#                    (host.docker.internal si la base corre en el host del VPS)
#   NOMBRE_BD        nombre de la base
#   USUARIO_BD       usuario de la base
#   PASSWORD_BD      contraseña de la base (solo se valida: nunca se imprime)
#   ARCHIVO_ENV      ruta al archivo de variables del servidor (permisos 600,
#                    fuera del repositorio)
#   RED              opcional; red de Docker a la que se conecta el contenedor
#                    (por ejemplo, la red propia de la base)
#   IP_VPS           opcional; solo para el mensaje final con la URL
#   ESPERA_SEGUNDOS  opcional; por defecto 90
#   DRY_RUN          opcional; `1` muestra los comandos sin ejecutarlos
#
# No hay valores por defecto para IMAGEN ni CONTENEDOR: en un servidor
# compartido, `libreria` es el contenedor de otro grupo y el script se niega a
# usarlo. El despliegue de este proyecto se llama `libreria-zoriontech`.
#
# Ejemplo real (sin la contraseña, que solo vive en el archivo de variables):
#   DRY_RUN=1 IMAGEN=libreria-zoriontech CONTENEDOR=libreria-zoriontech \
#   RED=libreria-zoriontech-net PUERTO_PUBLICO=8000 \
#   HOST_BD=libreria-zoriontech-db NOMBRE_BD=libreria USUARIO_BD=libreria \
#   PASSWORD_BD=<PASSWORD_BD> ARCHIVO_ENV=/root/libreria-zoriontech.env \
#   IP_VPS=46.202.151.202 bash scripts/desplegar_vps.sh
#
# El archivo de variables NUNCA se imprime: Docker lo lee con --env-file y este
# script solo comprueba que exista, que tenga permisos 600 y que la base no
# apunte al propio contenedor. La contraseña tampoco se escribe en pantalla.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

IMAGEN="${IMAGEN:-}"
CONTENEDOR="${CONTENEDOR:-}"
RED="${RED:-}"
IP_VPS="${IP_VPS:-<IP_VPS>}"
ESPERA_SEGUNDOS="${ESPERA_SEGUNDOS:-90}"
DRY_RUN="${DRY_RUN:-0}"

# --- 1. Variables obligatorias --------------------------------------------
# Se acumulan todas las que faltan para nombrarlas juntas y fallar una sola vez.
faltantes=()
[ -n "${IMAGEN:-}" ] || faltantes+=(IMAGEN)
[ -n "${CONTENEDOR:-}" ] || faltantes+=(CONTENEDOR)
[ -n "${PUERTO_PUBLICO:-}" ] || faltantes+=(PUERTO_PUBLICO)
[ -n "${HOST_BD:-}" ] || faltantes+=(HOST_BD)
[ -n "${NOMBRE_BD:-}" ] || faltantes+=(NOMBRE_BD)
[ -n "${USUARIO_BD:-}" ] || faltantes+=(USUARIO_BD)
[ -n "${PASSWORD_BD:-}" ] || faltantes+=(PASSWORD_BD)
[ -n "${ARCHIVO_ENV:-}" ] || faltantes+=(ARCHIVO_ENV)

if [ "${#faltantes[@]}" -gt 0 ]; then
  echo "ERROR: faltan variables obligatorias: ${faltantes[*]}" >&2
  echo "Exportalas antes de correr el script; la cabecera lista cada una." >&2
  echo "No hay valores por defecto para imagen, contenedor, host, puerto ni base." >&2
  exit 1
fi

# En este servidor `libreria` y `libreria-db` pertenecen a otro grupo: nunca se
# reemplazan desde este script.
case "$CONTENEDOR" in
  libreria|libreria-db)
    echo "ERROR: '$CONTENEDOR' es un contenedor de otro grupo en este VPS." >&2
    echo "Usá un nombre propio, por ejemplo libreria-zoriontech." >&2
    exit 1
    ;;
esac

case "$PUERTO_PUBLICO" in
  ''|*[!0-9]*)
    echo "ERROR: PUERTO_PUBLICO debe ser numérico (recibido: '$PUERTO_PUBLICO')." >&2
    exit 1
    ;;
esac

# --- 2. La base no puede estar en el propio contenedor --------------------
case "$HOST_BD" in
  localhost|127.0.0.1|::1|0.0.0.0)
    echo "ERROR: HOST_BD='$HOST_BD' apunta al propio contenedor." >&2
    echo "Usá host.docker.internal si la base corre en el host del VPS, o la" >&2
    echo "dirección que haya provisto la cátedra. 'localhost' está prohibido." >&2
    exit 1
    ;;
esac

# --- 3. Archivo de variables del servidor ---------------------------------
if [ ! -f "$ARCHIVO_ENV" ]; then
  echo "ERROR: no existe el archivo de variables '$ARCHIVO_ENV'." >&2
  echo "Creálo con: install -m 600 /dev/null <ruta>/libreria-zoriontech.env" >&2
  exit 1
fi

if command -v stat >/dev/null 2>&1; then
  permisos="$(stat -c %a "$ARCHIVO_ENV" 2>/dev/null || stat -f %Lp "$ARCHIVO_ENV" 2>/dev/null || echo desconocido)"
else
  permisos="desconocido"
fi

if [ "$permisos" != "600" ]; then
  echo "ERROR: '$ARCHIVO_ENV' tiene permisos '$permisos'; deben ser 600." >&2
  echo "Corregí con: chmod 600 '$ARCHIVO_ENV'" >&2
  exit 1
fi

env_abs="$(cd "$(dirname "$ARCHIVO_ENV")" && pwd)/$(basename "$ARCHIVO_ENV")"
case "$env_abs" in
  "$RAIZ"/*)
    echo "ERROR: el archivo de variables no puede estar dentro del repositorio." >&2
    echo "Movelo fuera (por ejemplo /root/libreria-zoriontech.env) y volvé a intentar." >&2
    exit 1
    ;;
esac

if ! grep -q '^DATABASE_URL=' "$ARCHIVO_ENV"; then
  echo "ERROR: '$ARCHIVO_ENV' no define DATABASE_URL." >&2
  exit 1
fi

# El valor se lee en memoria solo para extraer el host y validarlo; nunca se
# imprime ni se pasa por la línea de comandos.
url_bd="$(grep -m1 '^DATABASE_URL=' "$ARCHIVO_ENV" | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
host_url="${url_bd#*://}"
host_url="${host_url##*@}"
host_url="${host_url%%[:/]*}"

case "$host_url" in
  localhost|127.0.0.1|::1)
    echo "ERROR: DATABASE_URL de '$ARCHIVO_ENV' usa '$host_url' como host." >&2
    echo "Dentro del contenedor eso apunta al contenedor mismo." >&2
    echo "Usá host.docker.internal si la base corre en el host del VPS." >&2
    exit 1
    ;;
esac

# --- 4. Comandos ----------------------------------------------------------
args_base=(--restart unless-stopped)
if [ -n "$RED" ]; then
  args_base+=(--network "$RED")
fi
if [ "$HOST_BD" = "host.docker.internal" ] || [ "$host_url" = "host.docker.internal" ]; then
  args_base+=(--add-host=host.docker.internal:host-gateway)
fi

CMD_BUILD=(docker build -t "$IMAGEN" .)
CMD_RM=(docker rm -f "$CONTENEDOR")
CMD_RUN=(docker run -d --name "$CONTENEDOR" -p "${PUERTO_PUBLICO}:8000" "${args_base[@]}" --env-file "$ARCHIVO_ENV" "$IMAGEN")

mostrar_comando() {
  printf ' '
  printf '%s ' "$@"
  printf '\n'
}

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN=1: no se ejecuta nada contra Docker ni contra el VPS."
  echo "Archivo de variables: '$ARCHIVO_ENV' (contenido no se imprime)."
  echo "Host de la base: '$host_url'."
  echo "Comandos que se ejecutarían:"
  mostrar_comando "${CMD_BUILD[@]}"
  mostrar_comando "${CMD_RM[@]}"
  mostrar_comando "${CMD_RUN[@]}"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: no se encontró el comando 'docker'. Este script corre en el VPS." >&2
  exit 1
fi

# --- 5. Build, reemplazo y arranque ---------------------------------------
echo "== 1/4 build de la imagen =="
"${CMD_BUILD[@]}"

echo "== 2/4 eliminar el contenedor anterior si existe =="
"${CMD_RM[@]}" >/dev/null 2>&1 || true

echo "== 3/4 arrancar el contenedor =="
id_contenedor="$("${CMD_RUN[@]}")"
echo "Contenedor iniciado: ${id_contenedor:0:12}"

echo "== 4/4 esperar el estado healthy (máximo ${ESPERA_SEGUNDOS}s) =="
estado="desconocido"
limite=$((SECONDS + ESPERA_SEGUNDOS))
while [ "$SECONDS" -lt "$limite" ]; do
  estado="$(docker inspect -f '{{.State.Health.Status}}' "$CONTENEDOR" 2>/dev/null || echo desconocido)"
  [ "$estado" = "healthy" ] && break
  sleep 2
done

docker ps --filter "name=^/${CONTENEDOR}$"
echo "Estado de salud de $CONTENEDOR: $estado"

if [ "$estado" != "healthy" ]; then
  echo "ERROR: el contenedor no quedó healthy en ${ESPERA_SEGUNDOS}s." >&2
  echo "Últimas líneas de 'docker logs $CONTENEDOR':" >&2
  docker logs --tail 40 "$CONTENEDOR" >&2 || true
  echo "Revisá la base y el archivo de variables (no se imprime su contenido)." >&2
  exit 1
fi

echo "Despliegue listo: http://${IP_VPS}:${PUERTO_PUBLICO}/health/ready"
echo "Cargá los datos iniciales con: docker exec $CONTENEDOR python -m app.seed"
