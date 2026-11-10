# Tasks

> TDD estricto en el apply: cada grupo arranca con el test que falla (RED), sigue con la implementación mínima (GREEN) y refactoriza. Los tests de API usan `httpx.AsyncClient(transport=ASGITransport(app=app))` y `dependency_overrides` (patrón ya presente en `test/conftest.py`); los de integración (`@pytest.mark.integration`) corren contra PostgreSQL real si `DATABASE_URL` está definida y se saltean si no.

## 1. Helpers transversales (errores y paginación)

- [x] 1.1 Escribir `test/test_errores.py` en RED: `traducir_integrity_error` mapea por nombre de constraint (`uq_libro_isbn`, `uq_cliente_email`, `uq_perfil_cliente_cliente_id`, `fk_libro_editorial_id`) a un `HTTPException` 409 con el mensaje propio, y ante un constraint desconocido devuelve 409 genérico sin `str(exc)` ni texto de la base. Verificación: `pytest test/test_errores.py` falla (la función no existe).
- [x] 1.2 Implementar `app/core/errors.py` con el mapa `CONSTRAINT_MENSAJE` (tabla de `design.md` §3) y `traducir_integrity_error`, recorriendo `exc.orig` y `__cause__` para leer `diag.constraint_name` (asyncpg). Verificación: tests de 1.1 en verde.
- [x] 1.3 Crear `app/core/pagination.py` con `Limit = Annotated[int, Query(20, ge=1, le=100)]` y `Offset = Annotated[int, Query(0, ge=0)]`, y `test/test_pagination.py` que importe ambos alias y verifique defaults y límites. Verificación: `pytest test/test_pagination.py` pasa.

## 2. Editoriales

- [x] 2.1 Escribir `test/test_editoriales_api.py` en RED: `POST /editoriales/` 201 y 409 (nombre repetido); `GET /editoriales/` 200 paginado y 422 con `limit=0`; `GET /editoriales/{id}` 200/404 y 422 con `id` no entero (C-01); `PATCH /editoriales/{id}` parcial 200, 404 y 409 (nombre repetido); `GET /editoriales/{id}/libros` 200/404. Verificación: `pytest test/test_editoriales_api.py` falla (rutas no existen).
- [x] 2.2 Implementar `app/modules/editoriales/schemas.py` (`EditorialCreate` sin `id`, `EditorialUpdate` opcionales, `EditorialRead`). Verificación: los tests de DTO pasan.
- [x] 2.3 Implementar `app/modules/editoriales/service.py` (`create`, `listar` con `offset/limit`, `obtener`, `actualizar` con `model_dump(exclude_unset=True)` + `sqlmodel_update`, `listar_libros` con `joinedload(Libro.editorial)`) y `router.py` (`APIRouter` con `prefix="/editoriales"`, `tags`, handlers `async def`). Verificación: tests de 2.1 en verde.
- [x] 2.4 Registrar el router en `app/main.py` (`create_app`). Verificación: `import app.main` no falla y `GET /editoriales/` responde por la app completa.

## 3. Géneros

- [x] 3.1 Escribir `test/test_generos_api.py` en RED: `POST /generos/` 201 y 409 (nombre repetido); `GET /generos/` 200 paginado; `GET /generos/{id}/libros` 200/404. Verificación: `pytest test/test_generos_api.py` falla.
- [x] 3.2 Implementar `app/modules/generos/schemas.py` (`GeneroCreate`, `GeneroRead`) y `service.py` + `router.py` (`prefix="/generos"`; `GET /generos/{id}/libros` con `joinedload(Libro.genero)`). Verificación: tests de 3.1 en verde.

## 4. Autores

- [x] 4.1 Escribir `test/test_autores_api.py` en RED: `POST /autores/` 201 y 422 (contrato inválido); `GET /autores/{id}` 200/404/422; `PATCH /autores/{id}` parcial 200, 404 y 422; `GET /autores/{id}/libros` 200 con `rol`/`orden` por autoría y 404. Verificación: `pytest test/test_autores_api.py` falla.
- [x] 4.2 Implementar `app/modules/autores/schemas.py` (`AutorCreate`, `AutorUpdate`, `AutorRead`, y el DTO de libro con `rol`/`orden`), `service.py` (`obtener`, `actualizar`, `listar_libros` con join a `LibroAutor` y `selectinload(LibroAutor.libro).joinedload(Libro.editorial)`) y `router.py` (`prefix="/autores"`). Verificación: tests de 4.1 en verde.

## 5. Clientes

- [x] 5.1 Escribir `test/test_clientes_api.py` en RED: `POST /clientes/` 201, 409 (email repetido, C-02) y 422; `GET /clientes/{id}` 200 con perfil objeto/`null` y 404; `PATCH /clientes/{id}` parcial 200, 404, 409 y 422; `POST /clientes/{id}/perfil` 201, 404 y 409 (segundo perfil, C-03); `GET /clientes/{id}/ventas` 200 paginado y 404. Verificación: `pytest test/test_clientes_api.py` falla.
- [x] 5.2 Implementar `app/modules/clientes/schemas.py` (`ClienteCreate`, `ClienteUpdate`, `ClienteRead` con `perfil`, `PerfilCreate`, `PerfilRead`, `VentaRead`/`RenglonRead` para las ventas del cliente), `service.py` (`crear`, `obtener` con `joinedload(Cliente.perfil)`, `actualizar`, `crear_perfil`, `listar_ventas` con `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`) y `router.py` (`prefix="/clientes"`). Verificación: tests de 5.1 en verde.

## 6. Libros (lectura y edición)

- [x] 6.1 Escribir `test/test_libros_api.py` en RED: `GET /libros/` 200 con editorial y género, filtro `titulo` parcial insensible a mayúsculas, filtro `genero_id`, `titulo=' OR '1'='1` → 200 lista vacía (C-08) y 422 con `limit`/`offset` fuera de rango; `GET /libros/{id}` 200 con editorial/género/autores y 404; `PATCH /libros/{id}` parcial 200 (solo escalares), 404, 409 (ISBN repetido y `editorial_id`/`genero_id` inexistente) y 422. Verificación: `pytest test/test_libros_api.py` falla.
- [x] 6.2 Implementar `app/modules/libros/schemas.py` (`LibroRead` listado con editorial/género, `LibroDetalleRead` con autores, `LibroUpdate` solo campos escalares `isbn`/`titulo`/`precio`/`stock`/`editorial_id`/`genero_id` — sin `autores`, IN-01), `service.py` (`listar` con `ilike(f"%{titulo}%")` ligado + `joinedload`, `obtener` con `selectinload` de autorías, `actualizar` con `exclude_unset`) y `router.py` (`prefix="/libros"`). Verificación: tests de 6.1 en verde.

## 7. Integración y validación

- [x] 7.1 Test de integración (`@pytest.mark.integration`) en `test/test_contratos_integracion.py`: con la base real, alta de editorial/género/autor/cliente, alta de perfil, y lectura de listados con `limit`/`offset`; verificar `precio` serializado como string decimal. Verificación: pasa con `DATABASE_URL` definida; skip sin ella.
- [x] 7.2 Correr la suite completa (`pytest -q`) y `openspec validate --strict --change "contratos-crud"`. Verificación: todos los tests en verde, el change valida sin errores, y ningún error devuelve texto de la base ni trazas (RN-12).

## Workflow follow-up

- Verificar formalmente el change con `openspec-verify-change` contra proposal, design y specs.
- Archivar el change (`openspec-archive-change`) y sincronizar la delta a `openspec/specs/api-contracts/spec.md`.
- Marcar C-03 en `[x]` en `CHANGES.md` con su línea de cierre.
