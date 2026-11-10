# Tasks

> TDD estricto en el apply: cada grupo arranca con el test que falla (RED), sigue con la implementación mínima (GREEN) y refactoriza. Los tests de API usan `httpx.AsyncClient(transport=ASGITransport(app=app))` y `dependency_overrides` (patrón de `test/conftest.py`); los de integración (`@pytest.mark.integration`) corren contra PostgreSQL real si `DATABASE_URL` está definida y se saltean si no. La verificación de consultas usa `SQL_ECHO` / `event.listen(engine.sync_engine, "before_cursor_execute", ...)` para contar `SELECT` antes del alta.

## 1. DTO de venta y mapa de errores (autoría duplicada)

- [x] 1.1 Crear `app/modules/ventas/schemas.py` con `RenglonCreate` (`cantidad: int = Field(gt=0)`), `VentaCreate` (`renglones: list[RenglonCreate] = Field(min_length=1)` y validador que rechaza `libro_id` repetido) y mover `ClienteResumenRead`, `RenglonRead` y `VentaRead` desde `clientes/schemas.py`, agregando a `VentaRead` un `field_serializer("fecha")` que emite UTC ISO 8601 con microsegundos y sufijo `Z`. Reexportar los tres DTO desde `clientes/schemas.py`. Verificación: `import app.modules.ventas.schemas` y `from app.modules.clientes.schemas import VentaRead, RenglonRead` funcionan; `VentaRead(fecha=datetime.now(timezone.utc), ...).model_dump_json()` muestra `Z`.
- [x] 1.2 Escribir `test/test_ventas_schemas.py` en RED: `VentaCreate` rechaza `renglones` vacío, `cantidad <= 0` y `libro_id` repetido (422); `RenglonCreate` rechaza `cantidad=0`; `VentaRead.fecha` serializa con `Z`. Verificación: `pytest test/test_ventas_schemas.py` pasa tras la implementación de 1.1.
- [x] 1.3 Ampliar `app/core/errors.py` con `"libro_autor_pkey": "El autor ya está asociado a este libro"` y `test/test_errores.py` que aserte ese mapeo. Verificación: `pytest test/test_errores.py` en verde.

## 2. Alta de libro con autorías (`POST /libros/`)

- [x] 2.1 Escribir `test/test_libros_alta.py` en RED: `POST /libros/` 201 con editorial, género y autores (cada autoría con `autor_id`, `nombre`, `rol`, `orden`); 409 por ISBN repetido, editorial inexistente (C-04), autor inexistente (C-04) y género inexistente (RI-05); 422 por `precio <= 0`, `stock < 0`, `rol` inválido, `orden < 1` y `autor_id` repetido. Verificación: `pytest test/test_libros_alta.py` falla (la ruta no existe).
- [x] 2.2 Agregar `LibroCreate`/`AutorLibroCreate` a `app/modules/libros/schemas.py` (según `design.md` §1). Verificación: los tests de DTO de 2.1 pasan.
- [x] 2.3 Agregar `crear` a `app/modules/libros/service.py`: construye `Libro` con `editorial_id`/`genero_id` tal como llegan y `autorias=[LibroAutor(...) for a in datos.autores]`, un solo `commit`, `rollback` + `traducir_integrity_error` ante `IntegrityError`, y relee con `obtener` (precarga). Verificación: tests de 2.1 en verde (excepto los de ruta, que pasan con 2.4).
- [x] 2.4 Agregar `POST /libros/` a `app/modules/libros/router.py` (`response_model=LibroDetalleRead`, `status_code=201`). Verificación: `pytest test/test_libros_alta.py` completo en verde.

## 3. Registro de venta (`POST /ventas/`)

- [x] 3.1 Escribir `test/test_ventas_alta.py` en RED: `POST /ventas/` 201 con cliente y renglones (incluido `titulo` y `subtotal = cantidad × precio_unitario`); `total` igual a la suma; `fecha` con sufijo `Z`; 409 por cliente inexistente (C-05) y libro inexistente (C-05); 422 por `renglones` vacío, `cantidad <= 0` y `libro_id` repetido; el precio del renglón se copia y un cambio posterior del precio del libro no altera la venta. Verificación: `pytest test/test_ventas_alta.py` falla (ruta y módulo no existen).
- [x] 3.2 Crear `app/modules/ventas/service.py` con `crear` (según `design.md` §6): carga libros en una consulta (`WHERE id IN (...)`), 409 "El libro indicado no existe" si falta uno, copia `precio_unitario`, calcula `total` en `Decimal`, fija `fecha = datetime.now(timezone.utc)`, agrega renglones a `venta.renglones`, un solo `commit` con `rollback` + `traducir_integrity_error`, y relee con `joinedload(Venta.cliente)` + `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)` para armar `VentaRead`. Verificación: `pytest test/test_ventas_alta.py` en verde (con 3.3).
- [x] 3.3 Crear `app/modules/ventas/router.py` (`prefix="/ventas"`, `POST /` → 201 `VentaRead`) y registrarlo en `app/main.py`. Verificación: `pytest test/test_ventas_alta.py` completo en verde.

## 4. Integración y validación

- [x] 4.1 Test de integración (`@pytest.mark.integration`) en `test/test_altas_integracion.py`: contra la base real, alta de editorial/género/autores, `POST /libros/` 201, `POST /ventas/` con dos renglones 201 con total `"77000.00"` (seed de la consigna, C-06); editorial/autor inexistente → 409 (C-04) y cliente/libro inexistente → 409 (C-05). Verificación: pasa con `DATABASE_URL`; skip sin ella.
- [x] 4.2 Verificar con `SQL_ECHO` (o `event.listen` de `before_cursor_execute`) que el alta de libro no emite `SELECT` de existencia de editorial/género/autor antes del `INSERT`, y que la venta carga los libros en una sola consulta. Verificación: captura de SQL sin `SELECT` de existencia; contar consultas antes del alta.
- [x] 4.3 Correr la suite completa (`pytest -q`) y `openspec validate --strict --change "altas-con-relaciones"`. Verificación: todos los tests en verde, el change valida sin errores, y ningún error devuelve texto de la base ni trazas (RN-12).

## Workflow follow-up

- Verificar formalmente el change con `openspec-verify-change` contra proposal, design y specs.
- Archivar el change (`openspec-archive-change`) y sincronizar la delta a `openspec/specs/api-contracts/spec.md`.
- Marcar C-04 en `[x]` en `CHANGES.md` con su línea de cierre.
