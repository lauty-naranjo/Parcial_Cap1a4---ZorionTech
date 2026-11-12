# Design

## Context

C-03/C-04 dejaron casi toda la lectura ya con carga anticipada, porque `lazy="raise"` (C-02) rompe en runtime cualquier acceso perezoso. Estado actual relevante:

- `ventas/service.py` tiene la precarga correcta pero **privada** en `_releer` (usada por `crear`); no existen `obtener` ni `listar` públicos, y `ventas/router.py` solo expone `POST /ventas/`.
- `clientes/service.py` ya implementa `listar_ventas` con `joinedload(Venta.cliente)` + `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`.
- `libros/service.py` ya resuelve `GET /libros/{id}` con `joinedload(Libro.editorial)` + `joinedload(Libro.genero)` + `selectinload(Libro.autorias).joinedload(LibroAutor.autor)`.
- `autores/service.py` usa `selectinload(LibroAutor.libro).joinedload(Libro.editorial)` (libro es a-uno; funciona y es de conteo fijo).
- Los DTO de salida de venta (`VentaRead`, `RenglonRead`, `ClienteResumenRead`) ya existen en `ventas/schemas.py` y se reexportan desde `clientes/schemas.py`.

Restricciones que condicionan el diseño: reglas duras A/B/C/D de `AGENTS.md`; RN-G-03 (precarga obligatoria, sin carga perezosa); RN-10 (paginación en toda colección); IN-04 resuelta (referencia 2 consultas, el criterio es "que no crezca").

## Goals / Non-Goals

**Goals:**

- Exponer `GET /ventas/` y `GET /ventas/{id}` reutilizando `VentaRead`/`RenglonRead`, sin DTO nuevos.
- Garantizar y **demostrar con tests** el número fijo de consultas en las lecturas relacionales.
- Producir la evidencia `evidencia/C-07-consultas-*.txt`.

**Non-Goals:**

- No se toca el esquema ni los modelos (`data-model`).
- No se cambian contratos ni códigos HTTP de endpoints existentes.
- No se implementa el aviso en segundo plano (C-07).
- No se aserta un número mágico absoluto de consultas; se aserta que **no crece** con la cardinalidad.

## Decisions

### 1. DTO de salida de las lecturas de venta

`GET /ventas/` → `list[VentaRead]`; `GET /ventas/{id}` → `VentaRead`. Se **reutiliza** el `VentaRead`/`RenglonRead`/`ClienteResumenRead` de C-04 (ya cumple el contrato de `11_contratos_api.md` §DTO de salida: `id`, `fecha`, `total`, `cliente`, `renglones` con `titulo`/`subtotal`). No se crea un `VentaResumenRead`: la consigna pide el mismo `VentaRead` para detalle y listado.

**Alternativa considerada**: un DTO de resumen sin `renglones` para `GET /ventas/`. Descartada: `CHANGES.md` C-06 pide "la misma precarga (cliente + renglones + libro) o un DTO de resumen", y reutilizar `VentaRead` mantiene un único contrato y evita duplicar lógica.

### 2. Funciones públicas de lectura en `ventas/service.py`

Extraer `obtener(session, venta_id) -> VentaRead` y `listar(session, offset, limit) -> list[VentaRead]`, reutilizando el mapeo `_a_venta_read` y la precarga de `_releer`. `obtener` usa `scalar_one_or_none()` y devuelve 404 si no existe; `listar` aplica `order_by(Venta.id).offset(offset).limit(limit)`. El `POST` existente sigue usando la misma precarga (refactor interno sin cambio de comportamiento).

### 3. Estrategia de precarga y número de consultas objetivo

- Detalle de libro (`GET /libros/{id}`): 1 consulta con `joinedload(editorial, genero)` + 1 con `selectinload(autorias).joinedload(autor)` → **2**.
- Detalle de venta (`GET /ventas/{id}`): 1 con `joinedload(cliente)` + 1 con `selectinload(renglones).joinedload(libro)` → **2**.
- Listados (`GET /ventas/`, `GET /clientes/{id}/ventas`): la página carga cliente en la consulta principal y renglones+libro en una sola `WHERE venta_id IN (...)` → **2**, independiente del tamaño de página y de renglones por venta.
- `GET /libros/` y `/{id}/libros` de editorial/género: `joinedload(editorial, genero)` en una sola consulta → **1**.

`joinedload` para relaciones a-uno, `selectinload(...).joinedload(...)` para colecciones (evita explosión cartesiana y dispara una sola `IN` para la colección).

**Nota de coherencia**: `07_flujos_principales.md` §Flujo 4 menciona "3 para el libro", pero IN-04 (resuelta) y `CHANGES.md` fijan la referencia en **2**. Se sigue IN-04/CHANGES; el criterio operativo es que el conteo **no crezca** entre 1 y 3 autores/renglones, y el número real queda registrado en `evidencia/`.

### 4. Contador de consultas en tests

Helper en `test/` que registra `event.listen(engine.sync_engine, "before_cursor_execute", ...)` sobre el motor expuesto en `app.state.engine`, cuenta las ejecuciones durante una petición y restaura el listener. Los tests parametrizan la cardinalidad (1 vs 3 autores; 1 vs 3 renglones) y asertan `count == count`. Se usa el motor síncrono (`sync_engine`) porque el evento de cursor es del `Engine` subyacente de SQLAlchemy, igual para el motor asíncrono.

**Alternativa considerada**: asertar un número absoluto. Descartada por IN-04 ("no un número mágico") y por fragilidad frente a cambios de versión del driver.

### 5. Evidencia con `SQL_ECHO=true`

Los nombres de archivo `evidencia/C-07-consultas-libro.txt` y `evidencia/C-07-consultas-venta.txt` siguen el número de **caso de la consigna** "C-07 — cantidad fija de consultas" (no el change `C-07 asincronia-sin-bloqueos`). Se generan corriendo la app con `SQL_ECHO=true` y capturando la salida del `SELECT` para el detalle con 1 y 3 relaciones. La evidencia la completa/copia el change C-10; C-06 deja el archivo y el procedimiento.

### 6. Refactor de lecturas con carga perezosa

Auditoría del código actual: **no se encontró** ninguna lectura con carga perezosa; todas usan `joinedload`/`selectinload` explícitos. El único ajuste de consistencia opcional es normalizar `GET /autores/{id}/libros` de `selectinload(LibroAutor.libro)` a `joinedload(LibroAutor.libro)` (relación a-uno), sin cambiar el conteo ni la respuesta. No hay contrato ni código HTTP que cambie.

## Risks / Trade-offs

- **El conteo real puede diferir del "2" de referencia por comportamiento de SQLAlchemy/asyncpg** → mitigación: los tests asertan "no crece" (IN-04); el número real se documenta en `evidencia/`.
- **Un acceso perezoso olvidado lanza `InvalidRequestError` en runtime** → mitigación: `lazy="raise"` ya es la red de seguridad (C-02) y la auditoría confirma precarga total; los tests de conteo ejercitan los endpoints relacionales.
- **`selectinload` en listados grandes** → mitigación: paginación RN-10 limita el tamaño de página; la `IN` de renglones se limita a las ventas de la página.
- **Duplicación del mapeo `_venta_a_read` entre `ventas` y `clientes`** → mitigación: se mantiene el propietario único en `ventas/schemas.py` y `clientes` lo reexporta (ya vigente); C-06 no introduce una segunda copia.

## Migration Plan

Sin migración de datos ni de esquema. Los endpoints nuevos son aditivos; los refactors internos (`obtener`/`listar` públicos, normalización de `autores`) son de comportamiento equivalente y los cubren los tests de contrato existentes + los nuevos de conteo. Sin rollback de datos; ante un error se revierte el commit y se redeploya.

## Open Questions

Ninguna que cambie specs, enfoque o desglose de tareas. La única ambigüedad (nomenclatura `C-07-*` de la evidencia y el "3" de Flujo 4 vs "2" de IN-04) queda resuelta arriba por IN-04 y `CHANGES.md`; no se reabren las inconsistencias cerradas el 2026-11-09.
