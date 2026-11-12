# Tasks

## 1. Parser de `.http`

- [x] 1.1 Crear `test/http_runner.py` con `BloqueHttp` (archivo, línea, caso, método, ruta, cuerpo, esperado) y `leer_archivo(path)`; verificar que `python -c "from test.http_runner import leer_archivo"` no falla y que el módulo no se recolecta como test.
- [x] 1.2 Crear `test/test_http_runner.py` con casos del parser (bloque de solo comentarios ignorado, variables `{{base}}`/`{{id}}` sustituidas, `# Esperado:` con y sin fragmento JSON, normalización de fragmentos); verificar con `pytest test/test_http_runner.py -q`.

## 2. Contrato estático y archivos `.http` por módulo

- [x] 2.1 Crear `test/test_artefactos_http.py` con las reglas de formato de D1 (ocho archivos presentes, `@base = http://localhost:8000`, `###`, `# Caso:`, `# Esperado:`, UTF-8 sin BOM, sin secretos, rutas contra `app.openapi()["paths"]`); verificar que falla por archivos ausentes y que cada regla tiene un test propio.
- [x] 2.2 Escribir `test/health.http` con `/health/live` y `/health/ready` (200/200) y la nota del `HEALTHCHECK` con `127.0.0.1`; verificar con `pytest test/test_artefactos_http.py -k health -q`.
- [x] 2.3 Escribir `test/editoriales.http` (listar, crear, duplicado 409, detalle, `PATCH` parcial, `PATCH` 404, `/{id}/libros`, 404, `/abc` → C-01); verificar con `pytest test/test_artefactos_http.py -k editoriales -q`.
- [x] 2.4 Escribir `test/generos.http` (listar, crear, duplicado 409, `/{id}/libros`, 404, `limit=0` → 422) y `test/autores.http` (listar, crear, detalle, `PATCH`, 404, `/{id}/libros` con `rol`/`orden`, `/abc` → C-01); verificar con `pytest test/test_artefactos_http.py -k "generos or autores" -q`.
- [x] 2.5 Escribir `test/libros.http` (listado con `limit/offset/titulo/genero_id`, detalle, `PATCH` parcial que ignora `autores`, `PATCH` 404, `/abc` → C-01, alta completa 201); verificar con `pytest test/test_artefactos_http.py -k libros -q`.
- [x] 2.6 Escribir `test/clientes.http` (listar, crear, email duplicado → C-02, detalle con perfil `null`, `PATCH`, `/{id}/ventas`, `/abc` → C-01); verificar con `pytest test/test_artefactos_http.py -k clientes -q`.
- [x] 2.7 Escribir `test/ventas.http` (listado paginado, detalle con renglones, detalle 404, `/abc` → C-01, venta con dos renglones → C-06 con `77000.00`); verificar con `pytest test/test_artefactos_http.py -k ventas -q`.
- [x] 2.8 Escribir `test/casos-C.http` con C-01 (tres rutas), C-02 (ISBN y email), C-03 (perfil 201 y segundo 409), C-04 (editorial y autor inexistentes), C-05 (cliente y libro inexistentes), C-06 (201, precios copiados, `77000.00`) y C-08 (`' OR '1'='1` → 200 lista vacía en URL codificada); C-07 como bloque de solo comentarios (D3). Verificar con `pytest test/test_artefactos_http.py -q` completo.
- [x] 2.9 Verificar la cobertura: un test de `test_artefactos_http.py` exige que la unión de bloques contenga C-01…C-06 y C-08 y que C-07 mencione `SQL_ECHO`, `evidencia/C-07-consultas-libro.txt` y `evidencia/C-07-consultas-venta.txt`; correr `pytest test/test_artefactos_http.py::test_cobertura_de_casos -q`.

## 3. Replay ejecutable de los `.http`

- [x] 3.1 Crear `test/test_casos_http.py` que recorra un archivo por prueba en orden, con `motor_bd` + `sembrar(url_bd_test)` + `cliente_bd` y `monkeypatch` de `avisar_comprobante` a no-op; verificar con `pytest test/test_casos_http.py -q` y que los 8 archivos pasan.
- [x] 3.2 Agregar el reporte acumulado de desvíos (archivo, línea, esperado, obtenido) y comprobar el mensaje forzando un `# Esperado:` incorrecto en una copia temporal; verificar que el test falla nombrando el bloque y revertir la copia.
- [x] 3.3 Verificar el determinismo ejecutando el replay dos veces seguidas (`pytest test/test_casos_http.py -q` ×2) y confirmando los mismos resultados sin residuos de la corrida anterior.

## 4. Huecos de regresión

- [x] 4.1 Crear `test/test_regresion_entrega.py::test_parametro_de_ruta_invalido_no_consulta` con `contador_consultas`: 422 y cero consultas en `/libros/abc`, `/editoriales/abc`, `/generos/abc/libros`, `/autores/abc`, `/clientes/abc`, `/clientes/abc/ventas`, `/ventas/abc` y `PATCH /libros/abc`; verificar con `pytest test/test_regresion_entrega.py -k ruta_invalido -q`.
- [x] 4.2 Agregar `test_toda_coleccion_pagina` parametrizado sobre las ocho colecciones y sub-colecciones: defaults 20/0 y 422 con `limit=0`, `limit=101` y `offset=-1`; verificar con `pytest test/test_regresion_entrega.py -k paginacion -q`.
- [x] 4.3 Agregar `test_errores_no_filtran_texto_de_base`: 409 por ISBN, email, perfil, editorial, autor, cliente y libro; 404 de detalle; 422 de contrato; comprobar el `detail` propio y la ausencia de `duplicate key`, `violates`, `constraint`, `Traceback`, `asyncpg`, `psycopg`, `IntegrityError`, `SELECT`, `uq_` y `fk_`; verificar con `pytest test/test_regresion_entrega.py -k filtra -q`.
- [x] 4.4 Agregar `test_importes_son_string_decimal` sobre `GET /libros/`, `GET /libros/1`, `GET /ventas/`, `GET /ventas/2`, `GET /clientes/2/ventas` y el alta C-06: `precio`, `total`, `precio_unitario` y `subtotal` deben ser `str` con `^\d+\.\d{2}$`; verificar con `pytest test/test_regresion_entrega.py -k importes -q`.

## 5. Integridad de la evidencia

- [x] 5.1 Agregar a `test/test_artefactos_http.py` la guarda de `evidencia/`: existen los nueve archivos, C-07 contiene `SELECT` y conteos, D-01…D-07 declaran comando/criterio y ninguno conserva marcadores de plantilla; verificar con `pytest test/test_artefactos_http.py -k evidencia -q`.
- [x] 5.2 Confirmar sin reescribirlos que el comando documentado de C-07 sigue siendo reproducible: correr con `SQL_ECHO=true` `GET /libros/1`, `GET /libros/2` y `GET /ventas/2` y comparar el conteo (2 SELECT) con la evidencia; registrar el resultado en el informe del change, sin sobrescribir `evidencia/`.

## 6. Integración de la entrega

- [x] 6.1 Correr la suite completa con base real (`pytest -q`) y confirmar 299 tests previos + los nuevos pasando, 3 skipped esperados y cero duplicados de cobertura respecto de `test_sin_n_plus_uno.py`, `test_pagination.py`, `test_errores.py` y los tests por módulo; dejar el conteo en el informe.
- [x] 6.2 Ejecutar el smoke de solo lectura contra `http://46.202.151.202:8000` (`/health/live`, `/health/ready`, `GET /libros/` y C-08) y confirmar 200 y lista vacía; documentar comandos y salidas en el informe del change, sin tocar `evidencia/` ni crear datos.
- [x] 6.3 Recorrer los `.http` con VS Code REST Client y con JetBrains HTTP Client contra local (o validar el formato con ambos clientes) y confirmar que ningún request requiere editar el archivo para ejecutarse.

## Workflow follow-up

- Actualizar la fila de C-10 en `CHANGES.md` con el resultado de la verificación y marcarla al archivar.
- `/opsx:verify` antes de `/opsx:archive`.
