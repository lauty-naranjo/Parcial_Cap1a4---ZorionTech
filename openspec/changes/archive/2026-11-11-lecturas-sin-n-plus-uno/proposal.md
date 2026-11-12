# Proposal

## Why

El Ejercicio 5 (8% de la nota) evalúa que **toda lectura relacional use carga anticipada y un número fijo de consultas** (sin N+1): el detalle de un libro o de una venta debe costar lo mismo tenga 1 o 3 autores/renglones (IN-04, caso C-07 de la consigna). C-03 y C-04 ya precargan la mayoría de las lecturas con `joinedload`/`selectinload` para no romper `lazy="raise"`, pero todavía **faltan las lecturas de venta** (`GET /ventas/` y `GET /ventas/{id}`) y **no existe ninguna prueba que garantice** que el número de consultas no crece con la cardinalidad de las relaciones. Sin eso, el N+1 puede reaparecer silenciosamente y la evidencia pedida por la consigna no se puede producir.

## What Changes

- Se agregan los dos endpoints de lectura de venta que faltan, reutilizando el `VentaRead`/`RenglonRead` ya definido en C-04:
  - `GET /ventas/` → lista paginada de `VentaRead` (RN-10: `limit`/`offset` default 20/0, 422 fuera de rango).
  - `GET /ventas/{id}` → `VentaRead` con cliente + renglones + libro; 404 si no existe.
- Se extraen en `ventas/service.py` las funciones públicas `listar` y `obtener`, reutilizando la precarga que hoy vive privada en `_releer` (`joinedload(Venta.cliente)` + `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`).
- Se garantiza el **número fijo de consultas** en toda lectura relacional (libro, venta, editoriales/géneros/autores/clientes/ventas), con `joinedload` para relaciones a uno y `selectinload(...).joinedload(...)` para colecciones. Referencia resuelta (IN-04): **2 consultas** para `GET /libros/{id}` y `GET /ventas/{id}`; **2** para `GET /ventas/` y `GET /clientes/{id}/ventas`; **1** para `GET /libros/` y `/{id}/libros` de editorial/género.
- Se agregan tests de conteo de consultas con `event.listen(engine.sync_engine, "before_cursor_execute", ...)` que comparan el detalle con 1 vs 3 autores (libro) y 1 vs 3 renglones (venta) y asertan que el número **no cambia** (AAA, parametrizado).
- Se genera la evidencia `evidencia/C-07-consultas-libro.txt` y `evidencia/C-07-consultas-venta.txt` a partir de la salida con `SQL_ECHO=true`.
- Se revisa que ninguna lectura haya quedado con carga perezosa; si la hay, se refactoriza **sin cambiar contratos ni códigos HTTP**.

**Fuera de alcance**: no se toca el esquema (`data-model` no cambia), no se agregan `PATCH`/`PUT`/`DELETE` de ventas (RN-08, DD-03), no se cambia el cuerpo ni los códigos de los endpoints ya existentes, y el aviso de comprobante en segundo plano sigue siendo C-07.

## Capabilities

### New Capabilities

<!-- Ninguna: las lecturas de venta y la regla de carga anticipada extienden el contrato REST ya cubierto por `api-contracts`. -->

### Modified Capabilities

- `api-contracts`: se agregan los requisitos de lectura de ventas (`GET /ventas/` paginado y `GET /ventas/{id}` con detalle) y el requisito transversal de lecturas relacionales con número fijo de consultas (sin N+1).

## Impact

- **Código**: `app/modules/ventas/router.py` (dos `GET` nuevos) y `app/modules/ventas/service.py` (`listar`/`obtener` públicos, reutilizando la precarga de `_releer`). Sin cambios en el esquema ni en los DTO de salida.
- **API**: dos endpoints nuevos (`GET /ventas/`, `GET /ventas/{id}`) con el mismo `VentaRead`/`RenglonRead` de C-04; ningún código HTTP de endpoints existentes cambia.
- **Base de datos**: sin cambios de esquema; se lee sobre las tablas de C-02 con precarga explícita.
- **Dependencias**: ninguna nueva; se usan `sqlalchemy.orm.joinedload`/`selectinload` y el evento `before_cursor_execute` ya disponibles.
- **Tests**: contador de consultas por endpoint de detalle (libro y venta) con 1 vs 3 relaciones; regresión de que los listados paginados no disparan consultas por fila.
- **Evidencia**: `evidencia/C-07-consultas-libro.txt` y `evidencia/C-07-consultas-venta.txt` (los nombres `C-07-*` siguen el número de **caso de la consigna** "C-07 — cantidad fija de consultas", no el change `C-07 asincronia-sin-bloqueos`).
- **Riesgo principal**: el conteo exacto de consultas depende del comportamiento del emisor de SQLAlchemy/asyncpg; por eso IN-04 fija el criterio como "que **no crezca**", y el número real se registra en `evidencia/` en vez de asertarse como número mágico.
