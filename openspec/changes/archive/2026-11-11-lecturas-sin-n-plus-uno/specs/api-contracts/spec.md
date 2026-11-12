# Spec Delta

## ADDED Requirements

### Requirement: Listado de ventas

El sistema SHALL exponer `GET /ventas/` que devuelve la colección paginada de ventas, cada una con su cliente y sus renglones (con el título del libro). SHALL aceptar `limit` y `offset` con los defaults de RN-10 (20/0) y responder 422 si están fuera de rango.

#### Scenario: Listado paginado de ventas

- **WHEN** se consulta `GET /ventas/` sin parámetros
- **THEN** responde 200 con hasta 20 ventas a partir de la primera, cada una con `cliente` y `renglones`

#### Scenario: Paginación fuera de rango

- **WHEN** se consulta `GET /ventas/` con `limit` menor a 1 o mayor a 100, o con `offset` negativo
- **THEN** responde 422 con el detalle de validación, sin ejecutar la consulta

### Requirement: Detalle de venta

El sistema SHALL exponer `GET /ventas/{id}` que devuelve una venta con su cliente y sus renglones (incluido `titulo` y `subtotal`), respondiendo 404 si la venta no existe y 422 si el `id` no es un entero.

#### Scenario: Detalle existente y no existente

- **WHEN** se consulta una venta por `id`
- **THEN** responde 200 con su `VentaRead` si existe, y 404 con mensaje propio si no existe

### Requirement: Lecturas relacionales con número fijo de consultas

Toda lectura que devuelve relaciones SHALL precargarlas en la misma ejecución (sin carga perezosa) y SHALL resolver el detalle de un libro o de una venta en un número fijo de consultas, independiente de la cantidad de autores o renglones. MUST NOT disparar una consulta adicional por cada relación.

#### Scenario: Detalle de libro con cardinalidad variable

- **WHEN** se consulta `GET /libros/{id}` para libros con 1 y con 3 autores
- **THEN** el número de consultas emitidas es el mismo en ambos casos (referencia: 2)

#### Scenario: Detalle de venta con cardinalidad variable

- **WHEN** se consulta `GET /ventas/{id}` para ventas con 1 y con 3 renglones
- **THEN** el número de consultas emitidas es el mismo en ambos casos (referencia: 2)

#### Scenario: Listados sin consulta por fila

- **WHEN** se consulta `GET /ventas/` o `GET /clientes/{id}/ventas` con una página de varias ventas
- **THEN** el número de consultas no crece con la cantidad de ventas ni de renglones de la página
