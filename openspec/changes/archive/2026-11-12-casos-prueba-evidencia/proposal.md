# Proposal

## Why

La API está completa y desplegada, pero la entrega exige demostrar los casos C-01…C-08 con archivos `.http` ejecutables en `test/` y una suite de regresión que impida que esos contratos se rompan. Hoy no existe ningún `.http` (solo `test/.gitkeep`): el corrector no tiene un guion reproducible para verificar los casos, y la evidencia D-01…D-07 y C-07 ya existe pero no está referenciada ni protegida contra borrados accidentales.

## What Changes

- Agregar ocho archivos `.http` en `test/` (`health`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas` y `casos-C`), compatibles con VS Code REST Client y JetBrains HTTP Client, con `@base` configurable, un bloque por request y el resultado esperado declarado en comentarios.
- Concentrar C-01…C-08 en `test/casos-C.http` y usar los archivos por módulo para el CRUD de soporte y los healthchecks.
- Documentar C-07 como comando (`SQL_ECHO=true` + `GET /libros/{id}` y `GET /ventas/{id}`) referenciando la evidencia ya generada, no como un request HTTP.
- Completar la suite `pytest` + `httpx` solo donde hay huecos reales: replay automático de cada request `.http` contra la app ASGI con base sembrada, guardas de exposición de errores (RN-12) de extremo a extremo, 422 sin ejecutar el handler, paginación de las colecciones que faltaban y presencia/integridad de los artefactos de evidencia.
- Verificar que la evidencia D-01…D-07 y C-07 sigue completa y consistente; C-10 **no** la reescribe.
- Sin cambios de comportamiento de la API: no se agregan ni modifican endpoints, DTO, esquema ni reglas de negocio.

## Capabilities

### New Capabilities

- `test-evidence`: entrega los casos de prueba ejecutables (`.http` C-01…C-08), la suite de regresión que los respalda y la integridad de la carpeta `evidencia/` con C-07 y D-01…D-07.

### Modified Capabilities

- Ninguna. `api-contracts`, `health-checks`, `seed-data` y `vps-deployment` ya describen el comportamiento verificado; C-10 solo lo demuestra y lo protege. No se reescriben requisitos existentes.

## Impact

- **Archivos nuevos**: `test/health.http`, `test/editoriales.http`, `test/generos.http`, `test/autores.http`, `test/libros.http`, `test/clientes.http`, `test/ventas.http`, `test/casos-C.http`; tests nuevos en `test/test_artefactos_http.py`, `test/test_casos_http.py`, `test/test_regresion_entrega.py` y un helper `test/http_runner.py`.
- **Archivos leídos, no modificados**: `evidencia/C-07-consultas-*.txt`, `evidencia/D-01…D-07-*.txt`, `scripts/generar_evidencia_c07.py`, `app/seed.py`.
- **Sin impacto en runtime**: no cambia `app/`, `Dockerfile`, `requirements.txt` ni la base de datos.
- **Documentación**: el bloque de arranque de `.http` debe quedar referenciado desde `README.md` en C-11; C-10 deja el contrato listo.
