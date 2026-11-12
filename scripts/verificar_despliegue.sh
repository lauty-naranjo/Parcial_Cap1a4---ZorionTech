#!/usr/bin/env bash
# Verificación en el VPS de D-06, D-07 y D-04 (C-09).
#
# Se ejecuta EN el servidor, desde la raíz del repositorio transferido.
#
# Orden obligatorio: D-03 → D-07 → D-04.
#   D-03 se corre antes, desde fuera del VPS (scripts/verificar_publico.sh), y
#   crea la venta.
#   D-07 lee los logs de esa venta.
#   D-04 reinicia el contenedor y BORRA sus logs: por eso va último.
#
# Variables que lee:
#   CONTENEDOR         obligatoria; nombre del contenedor de la aplicación
#   IMAGEN             obligatoria; imagen con la que se recrea en D-04
#   RED                opcional; red de Docker para el `docker run` de D-04
#   ESPERA_SEGUNDOS    opcional; por defecto 90
#   CONFIRMAR_REINICIO obligatoria para D-04; `1` habilita `docker rm -f`
#   ARCHIVO_ENV        obligatoria para D-04 (permisos 600, fuera del repo)
#   PUERTO_PUBLICO     obligatoria para D-04 (mismo puerto que en producción)
#   HOST_BD            opcional; `host.docker.internal` agrega --add-host
#
# No hay valores por defecto para CONTENEDOR ni IMAGEN: en este servidor
# `libreria` y `libreria-db` pertenecen a otro grupo y el script se niega a
# usarlos. El despliegue de este proyecto es `libreria-zoriontech`.
#
# Uso (valores reales de este despliegue):
#   CONTENEDOR=libreria-zoriontech IMAGEN=libreria-zoriontech \
#   RED=libreria-zoriontech-net bash scripts/verificar_despliegue.sh
#
#   CONFIRMAR_REINICIO=1 CONTENEDOR=libreria-zoriontech \
#   IMAGEN=libreria-zoriontech RED=libreria-zoriontech-net \
#   ARCHIVO_ENV=/root/libreria-zoriontech.env PUERTO_PUBLICO=8000 \
#   HOST_BD=libreria-zoriontech-db bash scripts/verificar_despliegue.sh
#
# El archivo de variables nunca se imprime. D-04 solo se ejecuta con
# CONFIRMAR_REINICIO=1 y escribe evidencia/D-04-restart.txt.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

EVIDENCIA="$RAIZ/evidencia"
DESTINO_D04="$EVIDENCIA/D-04-restart.txt"

CONTENEDOR="${CONTENEDOR:-}"
IMAGEN="${IMAGEN:-}"
RED="${RED:-}"
ESPERA_SEGUNDOS="${ESPERA_SEGUNDOS:-90}"
CONFIRMAR_REINICIO="${CONFIRMAR_REINICIO:-0}"

faltantes=()
[ -n "$CONTENEDOR" ] || faltantes+=(CONTENEDOR)
[ -n "$IMAGEN" ] || faltantes+=(IMAGEN)
if [ "${#faltantes[@]}" -gt 0 ]; then
  echo "ERROR: faltan variables obligatorias: ${faltantes[*]}" >&2
  echo "Nombran el contenedor y la imagen; no hay valores por defecto." >&2
  exit 1
fi

case "$CONTENEDOR" in
  libreria|libreria-db)
    echo "ERROR: '$CONTENEDOR' es un contenedor de otro grupo en este VPS." >&2
    echo "Usá un nombre propio, por ejemplo libreria-zoriontech." >&2
    exit 1
    ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: no se encontró 'docker'. Este script corre en el VPS." >&2
  exit 1
fi

echo "Orden obligatorio: D-03 → D-07 → D-04."
echo "D-03 se ejecuta antes y desde fuera del VPS; D-04 reinicia y borra los logs."
echo

echo "== 1/3 docker ps (estado publicado) =="
docker ps --filter "name=^/${CONTENEDOR}$"
estado="$(docker inspect -f '{{.State.Health.Status}}' "$CONTENEDOR" 2>/dev/null || echo desconocido)"
puerto="$(docker inspect -f '{{range $p, $conf := .NetworkSettings.Ports}}{{if eq $p "8000/tcp"}}{{(index $conf 0).HostPort}}{{end}}{{end}}' "$CONTENEDOR" 2>/dev/null || true)"
echo "Estado de salud de $CONTENEDOR: $estado"
echo "Puerto publicado hacia 8000/tcp: ${puerto:-desconocido}"

if [ "$estado" != "healthy" ]; then
  echo "ERROR: el contenedor '$CONTENEDOR' no está healthy (estado: $estado)." >&2
  echo "Revisá 'docker logs $CONTENEDOR' antes de capturar evidencia." >&2
  exit 1
fi

echo
echo "== 2/3 D-06 y D-07 (usuario y logs) =="
USUARIO="$(docker exec "$CONTENEDOR" id)"
echo "D-06: docker exec $CONTENEDOR id"
echo "$USUARIO"
case "$USUARIO" in
  uid=0*) echo "ERROR: el proceso corre como root." >&2; exit 1 ;;
esac

LOGS="$(docker logs --tail 200 "$CONTENEDOR" 2>&1 || true)"
echo "D-07: últimas líneas de 'docker logs $CONTENEDOR'"
printf '%s\n' "$LOGS" | tail -n 20

if ! printf '%s\n' "$LOGS" | grep -q "Aviso de comprobante enviado"; then
  echo "ERROR: no se encontró el aviso del comprobante en los logs (D-07)." >&2
  echo "Ejecutá primero D-03 desde fuera del VPS:" >&2
  echo "  URL_PUBLICA=http://<IP_VPS>:<PUERTO_PUBLICO> bash scripts/verificar_publico.sh" >&2
  echo "El aviso aparece después del POST /ventas/; sin venta no hay nada que leer." >&2
  exit 1
fi
echo "D-07: aviso del comprobante presente en los logs."

if [ "$CONFIRMAR_REINICIO" != "1" ]; then
  echo
  echo "D-04 no se ejecuta: falta CONFIRMAR_REINICIO=1."
  echo "El reinicio elimina el contenedor (y sus logs). Volvé a correr con"
  echo "CONFIRMAR_REINICIO=1 ARCHIVO_ENV=<ARCHIVO_ENV> PUERTO_PUBLICO=<PUERTO_PUBLICO>."
  exit 0
fi

echo
echo "== 3/3 D-04: recrear el contenedor y comprobar los datos =="

faltantes=()
[ -n "${ARCHIVO_ENV:-}" ] || faltantes+=(ARCHIVO_ENV)
[ -n "${PUERTO_PUBLICO:-}" ] || faltantes+=(PUERTO_PUBLICO)
if [ "${#faltantes[@]}" -gt 0 ]; then
  echo "ERROR: faltan variables obligatorias para D-04: ${faltantes[*]}" >&2
  exit 1
fi

if [ ! -f "$ARCHIVO_ENV" ]; then
  echo "ERROR: no existe el archivo de variables '$ARCHIVO_ENV'." >&2
  exit 1
fi

if command -v stat >/dev/null 2>&1; then
  permisos="$(stat -c %a "$ARCHIVO_ENV" 2>/dev/null || stat -f %Lp "$ARCHIVO_ENV" 2>/dev/null || echo desconocido)"
else
  permisos="desconocido"
fi

if [ "$permisos" != "600" ]; then
  echo "ERROR: '$ARCHIVO_ENV' tiene permisos '$permisos'; deben ser 600." >&2
  exit 1
fi

if ! grep -q '^DATABASE_URL=' "$ARCHIVO_ENV"; then
  echo "ERROR: '$ARCHIVO_ENV' no define DATABASE_URL." >&2
  exit 1
fi

url_bd="$(grep -m1 '^DATABASE_URL=' "$ARCHIVO_ENV" | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"

host_url="${url_bd#*://}"
host_url="${host_url##*@}"
host_url="${host_url%%[:/]*}"

case "$host_url" in
  localhost|127.0.0.1|::1)
    echo "ERROR: DATABASE_URL usa '$host_url' como host dentro del contenedor." >&2
    echo "localhost está prohibido: apunta al propio contenedor." >&2
    exit 1
    ;;
esac

args_base=(--restart unless-stopped)
if [ -n "$RED" ]; then
  args_base+=(--network "$RED")
fi
if [ "${HOST_BD:-}" = "host.docker.internal" ] || [ "$host_url" = "host.docker.internal" ]; then
  args_base+=(--add-host=host.docker.internal:host-gateway)
fi

CMD_RUN=(docker run -d --name "$CONTENEDOR" -p "${PUERTO_PUBLICO}:8000" "${args_base[@]}" --env-file "$ARCHIVO_ENV" "$IMAGEN")

ANTES_PS="$(docker ps --filter "name=^/${CONTENEDOR}$")"

docker rm -f "$CONTENEDOR" >/dev/null
"${CMD_RUN[@]}" >/dev/null

estado="desconocido"
limite=$((SECONDS + ESPERA_SEGUNDOS))
while [ "$SECONDS" -lt "$limite" ]; do
  estado="$(docker inspect -f '{{.State.Health.Status}}' "$CONTENEDOR" 2>/dev/null || echo desconocido)"
  [ "$estado" = "healthy" ] && break
  sleep 2
done

DESPUES_PS="$(docker ps --filter "name=^/${CONTENEDOR}$")"

CODIGO_READY="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PUERTO_PUBLICO}/health/ready" 2>/dev/null || true)"
[ -n "$CODIGO_READY" ] || CODIGO_READY="000"
CODIGO_LIBROS="$(curl -sS -o /tmp/libreria-libros-d04.json -w '%{http_code}' "http://127.0.0.1:${PUERTO_PUBLICO}/libros/" 2>/dev/null || true)"
[ -n "$CODIGO_LIBROS" ] || CODIGO_LIBROS="000"
LIBROS_JSON="$(cat /tmp/libreria-libros-d04.json 2>/dev/null || true)"
rm -f /tmp/libreria-libros-d04.json
cantidad_libros="$(printf '%s' "$LIBROS_JSON" | grep -o '"titulo"' | wc -l | tr -d ' ' || true)"
[ -n "$cantidad_libros" ] || cantidad_libros=0

FECHA="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
fallos=()
[ "$estado" = "healthy" ] || fallos+=("el contenedor no volvió a healthy (estado: $estado)")
[ "$CODIGO_READY" = "200" ] || fallos+=("GET /health/ready devolvió $CODIGO_READY (esperado 200)")
[ "$CODIGO_LIBROS" = "200" ] || fallos+=("GET /libros/ devolvió $CODIGO_LIBROS (esperado 200)")
[ "$cantidad_libros" -ge 4 ] || fallos+=("GET /libros/ trajo $cantidad_libros libros (esperado al menos 4)")

if [ "${#fallos[@]}" -eq 0 ]; then
  ESTADO="VERIFICADO ($FECHA)"
else
  ESTADO="ERROR ($FECHA)"
fi

{
  echo "ESTADO: $ESTADO"
  echo "CASO: D-04 — reinicio del contenedor con los datos intactos (C-09)"
  echo "ENTORNO: VPS de la cátedra, $(hostname 2>/dev/null || echo host-desconocido)"
  echo "FECHA (UTC): $FECHA"
  echo "COMANDOS (sin imprimir el contenido del archivo de variables):"
  echo "  docker ps --filter name=^/${CONTENEDOR}\$"
  echo "  docker rm -f $CONTENEDOR"
  echo "  docker run -d --name $CONTENEDOR -p ${PUERTO_PUBLICO}:8000 ${args_base[*]} --env-file <ARCHIVO_ENV> $IMAGEN"
  echo "  docker ps --filter name=^/${CONTENEDOR}\$"
  echo "  curl -s -i http://127.0.0.1:${PUERTO_PUBLICO}/health/ready"
  echo "  curl -s -i http://127.0.0.1:${PUERTO_PUBLICO}/libros/"
  echo "CRITERIO DE ACEPTACIÓN:"
  echo "  El contenedor vuelve a quedar healthy y los datos de la base siguen ahí"
  echo "  (create_all solo crea tablas faltantes; la base vive fuera del contenedor)."
  echo
  echo "=== SALIDA REAL ==="
  echo "--- Antes: docker ps ---"
  echo "$ANTES_PS"
  echo
  echo "--- Después: docker ps ---"
  echo "$DESPUES_PS"
  echo "Estado de salud: $estado"
  echo
  echo "--- GET /health/ready -> HTTP $CODIGO_READY ---"
  echo "--- GET /libros/ -> HTTP $CODIGO_LIBROS (libros: $cantidad_libros) ---"
  echo "$LIBROS_JSON"
  echo
  echo "=== COMPROBACIONES ==="
  if [ "${#fallos[@]}" -eq 0 ]; then
    echo "OK: el contenedor volvió a healthy y los libros del seed siguen visibles."
  else
    for fallo in "${fallos[@]}"; do
      echo "FALLO: $fallo"
    done
  fi
} >"$DESTINO_D04"

echo "Evidencia escrita en: $DESTINO_D04"
echo "Estado de D-04: $estado"

if [ "${#fallos[@]}" -gt 0 ]; then
  for fallo in "${fallos[@]}"; do
    echo "  FALLO: $fallo" >&2
  done
  exit 1
fi

echo "D-04 verificado: contenedor healthy y datos intactos."
