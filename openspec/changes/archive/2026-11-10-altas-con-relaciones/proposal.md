# Proposal

## Why

C-03 dejó el CRUD de referencia completo, pero las dos altas que el Ejercicio 4 evalúa quedaron fuera de alcance: `POST /libros/` y `POST /ventas/` hoy no existen. Sin ellas no se puede crear un libro con su editorial, género y autorías, ni registrar una venta con sus renglones copiando el precio y calculando el total, que es lo que cierra el dominio de catálogo y ventas y habilita el seed (C-05) y las lecturas sin N+1 (C-06).

## What Changes

- Se agrega `LibroCreate` (con `autores: list[AutorLibroCreate]`) y `POST /libros/`, que crea un `Libro` con `editorial_id`/`genero_id` tal como llegan, agrega un `LibroAutor` por autoría y hace un único `commit`, sin consultar previamente la existencia de editorial/género/autor (RN-01, RI-01, RI-02, RI-05).
- Se crea el módulo `ventas` completo (`schemas.py`, `service.py`, `router.py`) —hoy solo tiene `models.py` de C-02— con `VentaCreate` (con `renglones: list[RenglonCreate]`) y `POST /ventas/`, que carga los libros en una sola consulta, copia `precio_unitario`, calcula `total`, fija `fecha` en UTC y persiste los renglones por composición (RN-04…RN-07, RN-G-06).
- El DTO de salida de la venta (`VentaRead`) serializa `fecha` en ISO 8601 UTC con microsegundos y sufijo `Z` (IN-05 resuelto) y expone `titulo` y `subtotal` por renglón.
- Validación en el borde: `rol` ∈ cuatro valores y `orden >= 1` en `AutorLibroCreate`; `cantidad > 0`, `min_length=1` y rechazo de `libro_id` repetido en la venta (422). El cuerpo de la venta no acepta `precio_unitario`, `total` ni `fecha`.
- Errores: ISBN repetido, editorial/género/autor/cliente/libro inexistente o autoría duplicada → 409 con mensaje propio mapeado por nombre de constraint, nunca 500 ni texto interno (RN-12).

**Fuera de alcance**: no hay `PATCH`/`PUT`/`DELETE` de ventas (RN-08, DD-03) ni alta de renglones por separado (RN-04). `GET /ventas/` y `GET /ventas/{id}` son C-06. Sin cambios de esquema ni de endpoints ya existentes de C-03.

## Capabilities

### New Capabilities

<!-- Ninguna: el contrato REST ya vive en `api-contracts`. Este change amplía esa capability. -->

### Modified Capabilities

- `api-contracts`: se agregan los requisitos de `POST /libros/` (alta de libro con autorías) y `POST /ventas/` (registro de venta con renglones, precio copiado, total calculado y fecha UTC con sufijo `Z`).

## Impact

- **Código**: nuevos `schemas.py`, `service.py` y `router.py` en `ventas`; `LibroCreate`/`AutorLibroCreate` y `crear` en `libros/schemas.py`, `libros/service.py` y `libros/router.py`; ajuste del serializador de `fecha` en el DTO de salida de venta; registro del router de ventas en `app/main.py`.
- **API**: dos endpoints nuevos (`POST /libros/` 201/409/422, `POST /ventas/` 201/409/422). El `fecha` de `VentaRead` pasa a emitirse con sufijo `Z` (afecta también a `GET /clientes/{id}/ventas`, ya coherente con IN-05).
- **Base de datos**: sin cambios de esquema; se escribe sobre las tablas y constraints de C-02 (`fk_libro_editorial_id`, `fk_libro_genero_id`, `fk_libro_autor_autor_id`, `fk_venta_cliente_id`, `fk_renglon_venta_libro_id`, PK compuesta de `libro_autor`).
- **Dependencias**: ninguna nueva; `datetime.timezone`, `decimal` y SQLAlchemy asincrónico ya presentes.
- **Tests**: C-04 (editorial/autor inexistente → 409), C-05 (cliente/libro inexistente → 409), C-06 (venta con dos renglones → 201, total `"77000.00"`); verificación con `SQL_ECHO` de que no hay `SELECT` de existencia antes del alta y de que el precio copiado no cambia si el libro cambia después.
- **Riesgo principal**: el mapeo de la autoría duplicada (PK compuesta de `libro_autor`) y de las FK a 409 depende de los nombres de constraint de C-02; un nombre mal referenciado degrada a 409 genérico o rompe el contrato.
