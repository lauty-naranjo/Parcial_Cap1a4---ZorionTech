#!/usr/bin/env bash
# Verificación reproducible de la imagen (C-08): D-01, D-02, D-05 y D-06.
#
# Uso:
#   bash scripts/verificar_imagen.sh
#   ENV_FILE=/ruta/al/archivo.env bash scripts/verificar_imagen.sh
#
# El archivo de variables NUNCA se imprime ni se pasa por la línea de comandos:
# Docker lo lee directamente con --env-file. Las salidas reales se escriben en
# evidencia/D-0*.txt con fecha UTC y el comando que las produjo.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

ENV_FILE="${ENV_FILE:-.env.docker}"
IMAGEN="${IMAGEN:-libreria}"
IMAGEN_BASE="${IMAGEN_BASE:-python:3.12-alpine}"
CONTENEDOR="${CONTENEDOR:-libreria}"
PUERTO="${PUERTO:-8000}"
ESPERA_SEGUNDOS="${ESPERA_SEGUNDOS:-60}"
EVIDENCIA="$RAIZ/evidencia"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: no se encontró el comando 'docker'. Instalá Docker o corré este script en el VPS." >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: falta el archivo de variables '$ENV_FILE'." >&2
  echo "Copiá env.example, completá DATABASE_URL y nombralo .env.docker (no se versiona)." >&2
  exit 1
fi

mkdir -p "$EVIDENCIA"
FECHA="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
red_args=()
if [ -n "${DOCKER_NETWORK:-}" ]; then
  red_args=(--network "$DOCKER_NETWORK")
fi

echo "== 1/6 build de la imagen =="
BUILD_LOG="$(mktemp)"
docker build -t "$IMAGEN" . 2>&1 | tee "$BUILD_LOG"

echo "== 2/6 D-01: tamaño de la base y de la imagen =="
# Con el store containerd de Docker 29 el FROM por digest no deja la base
# etiquetada en `docker images`: el pull explícito la publica y no vuelve a
# descargar las capas ya presentes.
docker pull "$IMAGEN_BASE" >/dev/null

{
  echo "Evidencia D-01 — imagen base por debajo de 100 MB (C-08)"
  echo "Fecha (UTC): $FECHA"
  echo "Comando: docker pull $IMAGEN_BASE && docker images $IMAGEN_BASE && docker images $IMAGEN"
  echo "Criterio: la entrada de $IMAGEN_BASE pesa menos de 100 MB."
  echo
  docker images "$IMAGEN_BASE"
  if [ -z "$(docker images -q "$IMAGEN_BASE")" ]; then
    # Fallback: el tamaño de contenido en bytes si el listado no la muestra.
    echo
    echo "(docker images no lista la base; se inspecciona su tamaño igual)"
    docker image inspect --format "{{.RepoTags}} tamaño de contenido: {{.Size}} bytes" \
      "$IMAGEN_BASE" || true
  fi
  echo
  docker images "$IMAGEN"
} >"$EVIDENCIA/D-01-docker-images.txt"

echo "== 3/6 D-02: run, estado healthy y logs =="
docker rm -f "$CONTENEDOR" >/dev/null 2>&1 || true
docker run -d --name "$CONTENEDOR" "${red_args[@]}" \
  -p "${PUERTO}:8000" --env-file "$ENV_FILE" "$IMAGEN" >/dev/null

ESTADO="desconocido"
LIMITE=$((SECONDS + ESPERA_SEGUNDOS))
while [ "$SECONDS" -lt "$LIMITE" ]; do
  ESTADO="$(docker inspect -f '{{.State.Health.Status}}' "$CONTENEDOR" 2>/dev/null || echo desconocido)"
  [ "$ESTADO" = "healthy" ] && break
  sleep 2
done

docker ps --filter "name=^/${CONTENEDOR}$"
echo "Estado de salud de $CONTENEDOR: $ESTADO"

{
  echo "Evidencia D-02 — build, run, docker ps y docker logs (C-08)"
  echo "Fecha (UTC): $FECHA"
  echo "Comandos:"
  echo "  docker build -t $IMAGEN ."
  echo "  docker run -d --name $CONTENEDOR ${DOCKER_NETWORK:+--network $DOCKER_NETWORK }-p ${PUERTO}:8000 --env-file <archivo-de-variables> $IMAGEN"
  echo "  docker ps --filter name=^/${CONTENEDOR}$"
  echo "  docker logs $CONTENEDOR"
  echo "Criterio: el build termina con código 0, docker ps muestra 'healthy' y"
  echo "los logs muestran el arranque y las tablas creadas."
  echo
  echo "=== docker build (últimas 40 líneas) ==="
  tail -n 40 "$BUILD_LOG"
  echo
  echo "=== docker ps ==="
  docker ps --filter "name=^/${CONTENEDOR}$"
  echo
  echo "=== docker logs $CONTENEDOR ==="
  docker logs "$CONTENEDOR" 2>&1 | tail -n 80
} >"$EVIDENCIA/D-02-build-run-ps.txt"

if [ "$ESTADO" != "healthy" ]; then
  echo "ERROR: el contenedor no quedó 'healthy' en ${ESPERA_SEGUNDOS}s (estado: $ESTADO)." >&2
  docker logs "$CONTENEDOR" >&2 || true
  exit 1
fi

echo "== 4/6 D-06: usuario del proceso =="
USUARIO="$(docker exec "$CONTENEDOR" id)"
echo "$USUARIO"
{
  echo "Evidencia D-06 — usuario sin privilegios (C-08)"
  echo "Fecha (UTC): $FECHA"
  echo "Comando: docker exec $CONTENEDOR id"
  echo "Criterio: uid distinto de 0 (appuser, uid 1000)."
  echo
  echo "SALIDA REAL:"
  echo "$USUARIO"
} >"$EVIDENCIA/D-06-usuario.txt"

case "$USUARIO" in
  uid=0*) echo "ERROR: el proceso corre como root." >&2; exit 1 ;;
esac

echo "== 5/6 seed dentro del contenedor =="
docker exec "$CONTENEDOR" python -m app.seed

echo "== 6/6 D-05: contenedor sin DATABASE_URL =="
docker rm -f "$CONTENEDOR" >/dev/null
set +e
SALIDA_D05="$(docker run --rm "${red_args[@]}" "$IMAGEN" 2>&1)"
CODIGO_D05=$?
set -e
echo "$SALIDA_D05"
echo "Código de salida sin --env-file: $CODIGO_D05"

{
  echo "Evidencia D-05 — contenedor sin DATABASE_URL (C-08)"
  echo "Fecha (UTC): $FECHA"
  echo "Comando: docker run --rm ${DOCKER_NETWORK:+--network $DOCKER_NETWORK }$IMAGEN"
  echo "Criterio: el proceso termina con código distinto de 0 y no queda sirviendo."
  echo
  echo "Código de salida: $CODIGO_D05"
  echo
  echo "SALIDA REAL:"
  echo "$SALIDA_D05"
} >"$EVIDENCIA/D-05-sin-database-url.txt"

if [ "$CODIGO_D05" -eq 0 ]; then
  echo "ERROR: el contenedor arrancó sin DATABASE_URL (código 0)." >&2
  exit 1
fi

echo
echo "Verificación completa: D-01, D-02, D-05 y D-06 en evidencia/."
echo "La imagen '$IMAGEN' queda construida para inspección."
