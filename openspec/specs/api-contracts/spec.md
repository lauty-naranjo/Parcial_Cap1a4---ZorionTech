# api-contracts Specification

## Purpose
Define el contrato REST de la API de la librería: los DTO de entrada y salida separados de las tablas, los códigos HTTP por situación, la paginación de toda colección y el CRUD de referencia de editoriales, géneros, autores, clientes y libros (lectura y edición).

## Requirements

### Requirement: DTO de lectura separados de las tablas

El sistema SHALL exponer cada recurso a través de un DTO de lectura propio que incluya únicamente los campos del contrato, sin serializar columnas internas ni metadatos del ORM.

#### Scenario: Respuesta limitada al contrato de lectura

- **WHEN** se consulta un recurso del catálogo (editorial, género, autor, libro o cliente)
- **THEN** el cuerpo contiene solo los campos del contrato de lectura y ningún identificador interno ajeno a él

### Requirement: Importes monetarios como string decimal

Todo campo monetario (`precio`, `total`, `precio_unitario`) SHALL serializarse como string decimal con dos decimales y MUST NOT emitirse como número de punto flotante.

#### Scenario: Importe con dos decimales

- **WHEN** se responde un recurso que incluye un importe
- **THEN** el importe se serializa como string decimal con dos decimales (por ejemplo `"25000.00"`), no como `float`

### Requirement: Paginación obligatoria de toda colección

Todo listado SHALL aceptar `limit` (entero entre 1 y 100, por defecto 20) y `offset` (entero mayor o igual a 0, por defecto 0), y SHALL responder 422 cuando un parámetro está fuera de rango.

#### Scenario: Parámetros de paginación por defecto

- **WHEN** se invoca un listado sin `limit` ni `offset`
- **THEN** se devuelve hasta 20 elementos a partir del primero

#### Scenario: Paginación fuera de rango

- **WHEN** se invoca un listado con `limit` menor a 1 o mayor a 100, o con `offset` negativo
- **THEN** responde 422 con el detalle de validación, sin ejecutar la consulta

### Requirement: Contrato de errores con mensajes propios

El sistema SHALL responder 409 cuando la base rechaza una unicidad o clave foránea, 404 cuando falta un recurso en una lectura o `PATCH`, y 422 cuando el contrato o los parámetros de consulta son inválidos. MUST NOT devolver texto interno de la base, nombres de constraints ni trazas.

#### Scenario: Conflicto de unicidad o clave foránea

- **WHEN** la base rechaza una operación por unicidad o por referencia inexistente en un alta
- **THEN** responde 409 con un mensaje propio traducido por nombre de constraint, sin el texto de PostgreSQL

#### Scenario: Recurso inexistente en lectura o PATCH

- **WHEN** se lee o se edita parcialmente un recurso que no existe
- **THEN** responde 404 con el mensaje propio, nunca 500

#### Scenario: Contrato o parámetro inválido

- **WHEN** el cuerpo no cumple el contrato del DTO o un parámetro de ruta/consulta es inválido
- **THEN** responde 422 con el detalle de validación de Pydantic, sin trazas

#### Scenario: Sin texto interno en ningún error

- **WHEN** ocurre cualquier error controlado
- **THEN** la respuesta no contiene `str(exc)`, nombres de tablas ni de constraints, ni trazas

### Requirement: Alta de editorial

El sistema SHALL exponer `POST /editoriales/` que crea una editorial y responde 201 con su DTO de lectura, 409 si el nombre ya existe y 422 si el contrato es inválido.

#### Scenario: Alta válida

- **WHEN** se envía un cuerpo válido con `nombre` y `pais`
- **THEN** responde 201 con el `id`, `nombre` y `pais` de la editorial creada

#### Scenario: Nombre repetido

- **WHEN** se envía un `nombre` que ya existe
- **THEN** responde 409 con un mensaje propio de unicidad

### Requirement: Listado y detalle de editoriales

El sistema SHALL exponer `GET /editoriales/` que devuelve la colección paginada y `GET /editoriales/{id}` que devuelve una editorial, respondiendo 404 si el `id` no existe y 422 si el `id` no es un entero.

#### Scenario: Detalle existente y no existente

- **WHEN** se consulta una editorial por `id`
- **THEN** responde 200 con su DTO si existe, y 404 si no existe

#### Scenario: Id no entero

- **WHEN** se consulta `GET /editoriales/{id}` con un `id` que no es un entero
- **THEN** responde 422 sin ejecutar el handler

### Requirement: Edición parcial de editorial

El sistema SHALL exponer `PATCH /editoriales/{id}` que aplica únicamente los campos enviados y responde 200 con el DTO actualizado, 404 si no existe y 409 si el nuevo nombre colisiona.

#### Scenario: Parcial con campos enviados

- **WHEN** se envía un subconjunto de campos en `PATCH /editoriales/{id}`
- **THEN** responde 200 y solo cambian los campos enviados, conservando el resto

### Requirement: Libros de una editorial

El sistema SHALL exponer `GET /editoriales/{id}/libros` que devuelve la colección paginada de libros de una editorial y responde 404 si la editorial no existe.

#### Scenario: Libros de una editorial existente

- **WHEN** se consultan los libros de una editorial existente
- **THEN** responde 200 con la lista paginada de libros; si la editorial no existe, responde 404

### Requirement: Alta y listado de géneros

El sistema SHALL exponer `POST /generos/` (201, o 409 si el nombre ya existe) y `GET /generos/` que devuelve la colección paginada.

#### Scenario: Alta y listado de géneros

- **WHEN** se crea un género y luego se listan los géneros
- **THEN** el alta responde 201 (409 si el nombre se repite) y el listado responde 200 paginado

### Requirement: Libros de un género

El sistema SHALL exponer `GET /generos/{id}/libros` que devuelve la colección paginada de libros de un género y responde 404 si el género no existe.

#### Scenario: Libros de un género existente

- **WHEN** se consultan los libros de un género existente
- **THEN** responde 200 con la lista paginada de libros; si el género no existe, responde 404

### Requirement: Alta de autor

El sistema SHALL exponer `POST /autores/` que crea un autor y responde 201 con su DTO de lectura, o 422 si el contrato es inválido.

#### Scenario: Alta válida de autor

- **WHEN** se envía un cuerpo válido con `nombre` y `nacionalidad`
- **THEN** responde 201 con el `id`, `nombre` y `nacionalidad` del autor

### Requirement: Detalle y edición de autor

El sistema SHALL exponer `GET /autores/{id}` y `PATCH /autores/{id}`, respondiendo 200 con el DTO del autor, 404 si no existe y 422 si el `id` no es un entero o el contrato es inválido.

#### Scenario: Detalle, edición parcial y no existente

- **WHEN** se consulta o se edita parcialmente un autor
- **THEN** responde 200 si existe (el `PATCH` aplica solo los campos enviados), 404 si no existe y 422 si el contrato es inválido

### Requirement: Libros de un autor con rol y orden

El sistema SHALL exponer `GET /autores/{id}/libros` que devuelve la colección paginada de libros del autor, cada uno con su `rol` y `orden` de participación, y responde 404 si el autor no existe.

#### Scenario: Libros con rol y orden

- **WHEN** se consultan los libros de un autor existente
- **THEN** cada libro incluye el `rol` y el `orden` de la autoría; si el autor no existe, responde 404

### Requirement: Alta y edición de clientes

El sistema SHALL exponer `POST /clientes/` (201, 409 si el email ya existe, 422 si el contrato es inválido) y `PATCH /clientes/{id}` (200, 404, 409 o 422 según corresponda).

#### Scenario: Alta y edición de cliente

- **WHEN** se crea un cliente con `nombre` y `email` válidos o se edita parcialmente
- **THEN** el alta responde 201 (409 si el email se repite) y la edición responde 200 aplicando solo los campos enviados

### Requirement: Detalle de cliente con perfil

El sistema SHALL exponer `GET /clientes/{id}` que devuelve el cliente con su perfil como objeto o `null`, y responde 404 si el cliente no existe.

#### Scenario: Perfil como objeto o null

- **WHEN** se consulta un cliente por `id`
- **THEN** responde 200 con el cliente y su `perfil` como objeto único o `null`, nunca como lista; si no existe, responde 404

### Requirement: Alta de perfil uno a uno

El sistema SHALL exponer `POST /clientes/{id}/perfil` que crea el perfil de un cliente, responde 201 con el DTO del perfil, 404 si el cliente no existe y 409 si el cliente ya tiene perfil.

#### Scenario: Segundo perfil rechazado

- **WHEN** se intenta crear un segundo perfil para un cliente que ya tiene uno
- **THEN** responde 409 con un mensaje propio; el primer alta respondió 201

### Requirement: Ventas de un cliente

El sistema SHALL exponer `GET /clientes/{id}/ventas` que devuelve la colección paginada de ventas del cliente y responde 404 si el cliente no existe.

#### Scenario: Ventas de un cliente existente

- **WHEN** se consultan las ventas de un cliente existente
- **THEN** responde 200 con la lista paginada de ventas; si el cliente no existe, responde 404

### Requirement: Listado y búsqueda de libros

El sistema SHALL exponer `GET /libros/` con `limit`, `offset`, `titulo` y `genero_id`. La búsqueda por `titulo` SHALL ser parcial e insensible a mayúsculas mediante un parámetro ligado, y cada libro SHALL incluir su editorial y su género.

#### Scenario: Búsqueda parcial insensible a mayúsculas

- **WHEN** se filtra por parte del `titulo` en cualquier combinación de mayúsculas y minúsculas
- **THEN** responde 200 con los libros que contienen ese texto y su editorial y género

#### Scenario: Texto con caracteres SQL

- **WHEN** se filtra con un `titulo` como `' OR '1'='1`
- **THEN** responde 200 con lista vacía, nunca un error de SQL

### Requirement: Detalle de libro

El sistema SHALL exponer `GET /libros/{id}` que devuelve el libro con su editorial, su género y sus autores, y responde 404 si el libro no existe.

#### Scenario: Detalle con relaciones

- **WHEN** se consulta un libro por `id`
- **THEN** responde 200 con el libro y su editorial, género y autores; si no existe, responde 404

### Requirement: Edición parcial de libro con campos escalares

El sistema SHALL exponer `PATCH /libros/{id}` que actualiza únicamente los campos escalares enviados (`isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id`) y MUST NOT aceptar la edición de autorías. SHALL responder 200 con el detalle, 404 si no existe, 409 si el nuevo ISBN colisiona y 422 si el contrato es inválido.

#### Scenario: PATCH sin autorías

- **WHEN** se edita parcialmente un libro enviando solo campos escalares
- **THEN** responde 200 con el detalle actualizado y las autorías quedan intactas; un cuerpo con `autores` no se usa para modificar autorías
