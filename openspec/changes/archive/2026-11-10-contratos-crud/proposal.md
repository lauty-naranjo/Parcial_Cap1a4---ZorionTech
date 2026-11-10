# Proposal

## Why

C-02 dejó el esquema completo —las nueve tablas con constraints nombrados, índices y navegación ORM— pero ningún módulo expone todavía un endpoint de negocio: hoy solo existen `/health/live` y `/health/ready`, y editoriales, géneros, autores, libros y clientes no tienen DTO, router ni servicio. Sin el contrato REST no se puede dar de alta, listar ni editar el catálogo, que es lo que el Ejercicio 3 (12% de la nota) evalúa y lo que habilita los changes siguientes (C-04 altas con relaciones, C-06 lecturas sin N+1).

## What Changes

- Se agregan `schemas.py`, `service.py` y `router.py` en los módulos `editoriales`, `generos`, `autores`, `clientes` y `libros`, con DTO separados de las tablas: `Create` (sin `id`), `Update` (todos los campos opcionales) y `Read` (serializa `Decimal` como string decimal).
- Se agrega el helper transversal `app/core/errors.py`: mapa nombre de constraint → mensaje propio + 409, para traducir `IntegrityError` sin filtrar texto de PostgreSQL (RN-12).
- Se agrega un helper de paginación reutilizable con `limit=Query(20, ge=1, le=100)` y `offset=Query(0, ge=0)` (RN-10).
- Se implementa el CRUD de referencia de la matriz de `knowledge-base/11_contratos_api.md`: editoriales (alta, listado paginado, detalle, edición parcial y sus libros), géneros (alta, listado paginado y sus libros), autores (alta, detalle, edición parcial y sus libros con `rol`/`orden`), clientes (alta, detalle con perfil, edición parcial, alta de perfil y sus ventas) y libros (listado filtrable, detalle y edición parcial de campos escalares).
- `app/main.py` registra los routers nuevos; la sesión se inyecta con la dependencia `SessionDep`.
- Tests de contrato con `httpx.AsyncClient` + `ASGITransport` y `dependency_overrides`.

**Fuera de alcance**: `POST /libros/` y `POST /ventas/` (son C-04); ningún `DELETE` (SU-05); no se toca el esquema de datos ni se cambia el comportamiento de `/health/*`.

## Capabilities

### New Capabilities

- `api-contracts`: el contrato REST de la API — DTO de entrada y salida separados de las tablas, códigos HTTP por situación, paginación de toda colección y CRUD de referencia de editoriales, géneros, autores, clientes y libros.

### Modified Capabilities

<!-- Ninguna: `app-foundation`, `data-model` y `health-checks` no cambian su comportamiento a nivel de requisito. Este change solo agrega routers/servicios/DTO sobre el esquema ya definido. -->

## Impact

- **Código**: nuevos `schemas.py`, `service.py` y `router.py` en cinco módulos, `app/core/errors.py` y el registro de routers en `app/main.py`.
- **API**: se exponen 20 endpoints nuevos (los de lectura/edición/alta de referencia de la matriz); `POST /libros/` y `POST /ventas/` quedan diferidos a C-04.
- **Base de datos**: sin cambios de esquema; se lee y escribe sobre las tablas de C-02.
- **Dependencias**: ninguna nueva; se usan `fastapi`, `sqlmodel`, `sqlalchemy` y `decimal` del stdlib.
- **Tests**: casos C-01 (id no entero → 422), C-02 (ISBN/email repetido → 409), C-03 (segundo perfil → 409), C-08 (`' OR '1'='1` → 200 lista vacía), PATCH parcial y paginación fuera de rango → 422.
- **Riesgo principal**: el mapeo de `IntegrityError` por nombre de constraint es contrato con C-02 (nombres `uq_*`/`fk_*` ya fijados); un nombre mal referenciado rompe el 409.
