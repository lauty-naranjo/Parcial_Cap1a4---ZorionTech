#!/usr/bin/env bash
# Verificación pública de D-03 (C-09). Se ejecuta FUERA del VPS, en la máquina
# del operador, contra la URL publicada por el servidor.
#
# Uso:
#   URL_PUBLICA=http://<IP_VPS>:<PUERTO_PUBLICO> bash scripts/verificar_publico.sh
#
# Variables que lee:
#   URL_PUBLICA   obligatoria; http(s)://host:puerto del VPS (sin barra final)
#
# Comprueba los tres endpoints de D-03 contra la URL pública:
#   GET  /health/ready  -> 200 {"estado": "listo", "base": "ok"}
#   GET  /libros/       -> 200 con los cuatro libros del seed
#   POST /ventas/       -> 201 con el cuerpo del caso C-06 y total "77000.00"
#
# Escribe la salida real en evidencia/D-03-endpoints-publicos.txt. El script se
# niega a correr contra 127.0.0.1/localhost: una prueba local no es D-03.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

EVIDENCIA="$RAIZ/evidencia"
DESTINO="$EVIDENCIA/D-03-endpoints-publicos.txt"

if [ -z "${URL_PUBLICA:-}" ]; then
  echo "ERROR: falta URL_PUBLICA." >&2
  echo "Uso: URL_PUBLICA=http://<IP_VPS>:<PUERTO_PUBLICO> bash scripts/verificar_publico.sh" >&2
  exit 1
fi

URL_PUBLICA="${URL_PUBLICA%/}"

case "$URL_PUBLICA" in
  *localhost*|*127.0.0.1*|*0.0.0.0*|*\[::1\]*)
    echo "ERROR: URL_PUBLICA='$URL_PUBLICA' apunta a la máquina local." >&2
    echo "Este script se niega a ejecutar: una prueba local no es D-03." >&2
    echo "Pasá la URL pública del VPS, no loopback." >&2
    exit 1
    ;;
esac

case "$URL_PUBLICA" in
  http://*|https://*) : ;;
  *)
    echo "ERROR: URL_PUBLICA debe empezar con http:// o https://." >&2
    exit 1
    ;;
esac

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: no se encontró 'curl'. Instalalo y volvé a intentar." >&2
  exit 1
fi

if ! command -v grep >/dev/null 2>&1; then
  echo "ERROR: no se encontró 'grep'." >&2
  exit 1
fi

mkdir -p "$EVIDENCIA"
CUERPOS="$(mktemp -d)"
trap 'rm -rf "$CUERPOS"' EXIT

FECHA="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

CUERPO_VENTA='{"cliente_id": 2, "renglones": [{"libro_id": 1, "cantidad": 2}, {"libro_id": 4, "cantidad": 1}]}'

echo "== D-03: verificación pública contra $URL_PUBLICA =="

CODIGO_READY="$(curl -sS -o "$CUERPOS/ready.json" -w '%{http_code}' "$URL_PUBLICA/health/ready" 2>/dev/null || true)"
[ -n "$CODIGO_READY" ] || CODIGO_READY="000"
echo "GET /health/ready -> HTTP $CODIGO_READY"

CODIGO_LIBROS="$(curl -sS -o "$CUERPOS/libros.json" -w '%{http_code}' "$URL_PUBLICA/libros/" 2>/dev/null || true)"
[ -n "$CODIGO_LIBROS" ] || CODIGO_LIBROS="000"
echo "GET /libros/ -> HTTP $CODIGO_LIBROS"

CODIGO_VENTA="$(curl -sS -o "$CUERPOS/venta.json" -w '%{http_code}' \
  -X POST -H 'Content-Type: application/json' \
  --data "$CUERPO_VENTA" "$URL_PUBLICA/ventas/" 2>/dev/null || true)"
[ -n "$CODIGO_VENTA" ] || CODIGO_VENTA="000"
echo "POST /ventas/ -> HTTP $CODIGO_VENTA"

CUERPO_READY="$(cat "$CUERPOS/ready.json" 2>/dev/null || true)"
CUERPO_LIBROS="$(cat "$CUERPOS/libros.json" 2>/dev/null || true)"
CUERPO_VENTA_RESP="$(cat "$CUERPOS/venta.json" 2>/dev/null || true)"

compacto_ready="$(printf '%s' "$CUERPO_READY" | tr -d '[:space:]')"
compacto_libros="$(printf '%s' "$CUERPO_LIBROS" | tr -d '[:space:]')"
compacto_venta="$(printf '%s' "$CUERPO_VENTA_RESP" | tr -d '[:space:]')"

cantidad_libros="$(printf '%s' "$CUERPO_LIBROS" | grep -o '"titulo"' | wc -l | tr -d ' ' || true)"
[ -n "$cantidad_libros" ] || cantidad_libros=0

fallos=()

[ "$CODIGO_READY" = "200" ] || fallos+=("GET /health/ready devolvió $CODIGO_READY (esperado 200)")
case "$compacto_ready" in
  *'"estado":"listo"'*) : ;;
  *) fallos+=("GET /health/ready no devolvió \"estado\": \"listo\"") ;;
esac
case "$compacto_ready" in
  *'"base":"ok"'*) : ;;
  *) fallos+=("GET /health/ready no devolvió \"base\": \"ok\"") ;;
esac

[ "$CODIGO_LIBROS" = "200" ] || fallos+=("GET /libros/ devolvió $CODIGO_LIBROS (esperado 200)")
[ "$cantidad_libros" -ge 4 ] || fallos+=("GET /libros/ trajo $cantidad_libros libros (esperado al menos 4)")
case "$CUERPO_LIBROS" in
  *Rayuela*) : ;;
  *) fallos+=("GET /libros/ no incluye Rayuela") ;;
esac
case "$CUERPO_LIBROS" in
  *"Respiración artificial"*) : ;;
  *) fallos+=("GET /libros/ no incluye Respiración artificial") ;;
esac

[ "$CODIGO_VENTA" = "201" ] || fallos+=("POST /ventas/ devolvió $CODIGO_VENTA (esperado 201)")
case "$compacto_venta" in
  *'"total":"77000.00"'*) : ;;
  *) fallos+=("POST /ventas/ no devolvió total \"77000.00\"") ;;
esac
case "$compacto_venta" in
  *'"precio_unitario":"25000.00"'*) : ;;
  *) fallos+=("POST /ventas/ no copió el precio 25000.00 del libro 1") ;;
esac
case "$compacto_venta" in
  *'"precio_unitario":"27000.00"'*) : ;;
  *) fallos+=("POST /ventas/ no copió el precio 27000.00 del libro 4") ;;
esac

if [ "${#fallos[@]}" -eq 0 ]; then
  ESTADO="VERIFICADO ($FECHA)"
else
  ESTADO="ERROR ($FECHA)"
fi

{
  echo "ESTADO: $ESTADO"
  echo "CASO: D-03 — endpoints públicos desde fuera del VPS (C-09)"
  echo "ENTORNO: operador fuera del VPS, curl $(curl --version 2>/dev/null | head -n 1 || echo 'desconocido')"
  echo "FECHA (UTC): $FECHA"
  echo "URL PÚBLICA: $URL_PUBLICA"
  echo "COMANDOS:"
  echo "  curl -s -i $URL_PUBLICA/health/ready"
  echo "  curl -s -i $URL_PUBLICA/libros/"
  echo "  curl -s -i -X POST $URL_PUBLICA/ventas/ -H 'Content-Type: application/json' -d '$CUERPO_VENTA'"
  echo "CRITERIO DE ACEPTACIÓN:"
  echo "  /health/ready -> 200 {\"estado\":\"listo\",\"base\":\"ok\"}"
  echo "  /libros/ -> 200 con los cuatro libros del seed"
  echo "  POST /ventas/ -> 201 con precios copiados y total \"77000.00\""
  echo
  echo "=== CÓDIGOS HTTP ==="
  echo "GET /health/ready: $CODIGO_READY"
  echo "GET /libros/: $CODIGO_LIBROS"
  echo "POST /ventas/: $CODIGO_VENTA"
  echo "Libros listados (\"titulo\"): $cantidad_libros"
  echo
  echo "=== RESPUESTA /health/ready ==="
  echo "$CUERPO_READY"
  echo
  echo "=== RESPUESTA /libros/ ==="
  echo "$CUERPO_LIBROS"
  echo
  echo "=== RESPUESTA /ventas/ (cuerpo C-06) ==="
  echo "$CUERPO_VENTA_RESP"
  echo
  echo "=== COMPROBACIONES ==="
  if [ "${#fallos[@]}" -eq 0 ]; then
    echo "OK: los tres endpoints y el total \"77000.00\" coinciden con el criterio."
  else
    for fallo in "${fallos[@]}"; do
      echo "FALLO: $fallo"
    done
  fi
} >"$DESTINO"

echo "Evidencia escrita en: $DESTINO"

if [ "${#fallos[@]}" -gt 0 ]; then
  echo "ESTADO: $ESTADO" >&2
  for fallo in "${fallos[@]}"; do
    echo "  FALLO: $fallo" >&2
  done
  exit 1
fi

echo "ESTADO: $ESTADO"
echo "D-03 verificado: 200 / 200 con libros / 201 con total 77000.00."
