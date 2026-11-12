# Tasks

> TDD estricto en el apply: cada grupo arranca con el test que falla (RED), sigue con la implementación mínima (GREEN) y refactoriza. Los tests de API usan `httpx.AsyncClient(transport=ASGITransport(app=app))` y `dependency_overrides` (patrón de `test/conftest.py`); el contador de consultas se apoya en `app.state.engine`.

## 1. Lecturas de venta (`GET /ventas/` y `GET /ventas/{id}`)

- [x] 1.1 Escribir `test/test_ventas_api.py` en RED: `GET /ventas/` 200 con lista paginada de `VentaRead` (cliente + renglones con `titulo`/`subtotal`) y 422 con `limit`/`offset` fuera de rango; `GET /ventas/{id}` 200 con detalle y 404 con mensaje propio, y 422 con `id` no entero (C-01). Verificación: `pytest test/test_ventas_api.py` falla (las rutas no existen).
- [x] 1.2 Implementar `ventas/service.py`: extraer `obtener(session, venta_id)` (precarga `joinedload(Venta.cliente)` + `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`, `scalar_one_or_none()`, 404) y `listar(session, offset, limit)` (`order_by(Venta.id)` + `offset`/`limit`), reutilizando `_a_venta_read`; dejar que `crear` reutilice la misma precarga. Verificación: tests de 1.1 en verde.
- [x] 1.3 Implementar `ventas/router.py`: `GET /` con `response_model=list[VentaRead]` y `GET /{venta_id}` con `response_model=VentaRead`, ambos `async def` con `SessionDep` y `limit: Limit = 20, offset: Offset = 0` en el listado. Verificación: tests de 1.1 en verde por la app completa.

## 2. Contador de consultas y tests de N+1

- [x] 2.1 Crear el helper `test/contador_consultas.py` (o `test/conftest.py`) con un context manager que registra `event.listen(engine.sync_engine, "before_cursor_execute", ...)`, cuenta ejecuciones durante la petición y remueve el listener al salir. Verificación: un test unitario del helper cuenta correctamente una consulta conocida.
- [x] 2.2 Escribir `test/test_sin_n_plus_uno.py` en RED (parametrizado, AAA): `GET /libros/{id}` con 1 vs 3 autores → mismo conteo; `GET /ventas/{id}` con 1 vs 3 renglones → mismo conteo. Verificación: el test falla si el conteo difiere entre cardinalidades.
- [x] 2.3 Agregar los casos de listados al mismo archivo: `GET /ventas/` y `GET /clientes/{id}/ventas` con una página de varias ventas → el conteo no crece con la cantidad de ventas ni de renglones. Verificación: el test aserta conteo constante por página.

## 3. Auditoría y refactor de precarga existente

- [x] 3.1 Auditar todas las lecturas relacionales (`libros`, `editoriales`, `generos`, `autores`, `clientes`, `ventas`) y confirmar que ninguna usa carga perezosa; dejar constancia en el comentario de cada servicio. Verificación: `grep -R "lazy" app/` solo muestra `lazy="raise"` en los modelos; ningún `service.py` accede a una relación sin `joinedload`/`selectinload`.
- [x] 3.2 Normalizar `autores/service.py` `listar_libros` a `joinedload(LibroAutor.libro)` (relación a-uno) en lugar de `selectinload`, sin cambiar el conteo ni la respuesta. Verificación: `pytest test/test_autores_api.py` sigue en verde y el listado devuelve `rol`/`orden` y editorial.

## 4. Evidencia de consultas

- [x] 4.1 Correr la app con `SQL_ECHO=true` y capturar en `evidencia/C-07-consultas-libro.txt` la salida de `SELECT` del detalle de un libro con 1 y con 3 autores, mostrando que el número de consultas es el mismo. Verificación: el archivo existe y contiene ambos conteos.
- [x] 4.2 Capturar en `evidencia/C-07-consultas-venta.txt` la salida de `SELECT` del detalle de una venta con 1 y con 3 renglones, mostrando que el número de consultas es el mismo. Verificación: el archivo existe y contiene ambos conteos.

## 5. Integración y validación

- [x] 5.1 Test de integración (`@pytest.mark.integration`) que, con la base real y datos del seed, verifica `GET /ventas/` y `GET /ventas/{id}` devuelven `VentaRead` con `total` string decimal y fecha `Z`, y que el conteo de consultas no cambia con cardinalidad. Verificación: pasa con `DATABASE_URL` definida; skip sin ella.
- [x] 5.2 Correr la suite completa (`pytest -q`) y `openspec validate --strict --change "lecturas-sin-n-plus-uno"`. Verificación: todos los tests en verde, el change valida sin errores, y ningún error devuelve texto de la base ni trazas (RN-12).

## Workflow follow-up

- Verificar formalmente el change con `openspec-verify-change` contra proposal, design y specs.
- Archivar el change (`openspec-archive-change`) y sincronizar la delta a `openspec/specs/api-contracts/spec.md`.
- Marcar C-06 en `[x]` en `CHANGES.md` con su línea de cierre.
