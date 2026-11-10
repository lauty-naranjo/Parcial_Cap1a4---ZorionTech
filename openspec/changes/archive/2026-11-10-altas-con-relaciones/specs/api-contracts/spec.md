# Spec Delta

## ADDED Requirements

### Requirement: Fecha de venta en UTC ISO 8601 con sufijo Z

El sistema SHALL serializar la fecha de una venta en UTC, en formato ISO 8601 con microsegundos y sufijo `Z`, y MUST NOT emitirla con el desfase `+00:00` ni sin zona horaria.

#### Scenario: Fecha con microsegundos y sufijo Z

- **WHEN** se responde una venta creada
- **THEN** el campo `fecha` tiene la forma `"AAAA-MM-DDTHH:MM:SS.ffffffZ"` (por ejemplo `"2026-10-08T21:14:11.751581Z"`), sin `+00:00`

### Requirement: Alta de libro con autorías

El sistema SHALL exponer `POST /libros/` que crea un libro con `editorial_id`, `genero_id` opcional y una lista de autorías. SHALL responder 201 con el detalle del libro (editorial, género y autores), 409 si el ISBN ya existe o si la editorial, el género o un autor no existen, y 422 si el contrato es inválido.

#### Scenario: Alta válida de libro con autorías

- **WHEN** se envía un cuerpo válido con `isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id` y una lista de `autores` con `rol` y `orden`
- **THEN** responde 201 con el libro, su editorial, su género y sus autores, cada autoría con su `autor_id`, `nombre`, `rol` y `orden`

#### Scenario: Editorial, género o autor inexistente

- **WHEN** el alta referencia una editorial, un género o un autor que no existe
- **THEN** responde 409 con el mensaje propio correspondiente, sin texto interno de la base

#### Scenario: ISBN repetido

- **WHEN** el alta usa un `isbn` ya registrado
- **THEN** responde 409 con el mensaje propio de unicidad

### Requirement: Validación de la autoría en el alta de libro

Cada autoría del alta SHALL validar que `rol` pertenezca a los valores `autor`, `coautor`, `traductor` o `ilustrador` y que `orden` sea mayor o igual a 1. Un mismo `autor_id` repetido dentro del alta SHALL rechazarse como contrato inválido.

#### Scenario: Rol u orden inválido

- **WHEN** una autoría tiene un `rol` fuera de los cuatro valores o un `orden` menor a 1
- **THEN** responde 422 con el detalle de validación, sin persistir el libro

#### Scenario: Autor duplicado en el mismo alta

- **WHEN** el alta incluye dos autorías con el mismo `autor_id`
- **THEN** responde 422 con un mensaje propio de autoría duplicada

### Requirement: Registro de venta con renglones

El sistema SHALL exponer `POST /ventas/` que crea una venta con `cliente_id` y `renglones` anidados. SHALL responder 201 con el cliente y los renglones (incluido `titulo` y `subtotal`), 409 si el cliente o un libro no existe, y 422 si el contrato es inválido. El cuerpo MUST NOT aceptar `precio_unitario`, `total` ni `fecha`.

#### Scenario: Venta válida con renglones

- **WHEN** se envía `cliente_id` y una lista de renglones con `libro_id` y `cantidad` mayor a 0
- **THEN** responde 201 con el cliente y los renglones, copiando `precio_unitario` del libro y calculando `total` como la suma de `cantidad × precio_unitario`

#### Scenario: Cliente o libro inexistente

- **WHEN** la venta referencia un cliente o un libro que no existe
- **THEN** responde 409 con el mensaje propio correspondiente, nunca 500

#### Scenario: Campos de importe y fecha no aceptados

- **WHEN** el cuerpo incluye `precio_unitario`, `total` o `fecha`
- **THEN** esos valores no se usan para fijar el precio, el total ni la fecha de la venta

### Requirement: Validación de renglones en la venta

Una venta SHALL tener al menos un renglón, cada renglón SHALL tener `cantidad` mayor a 0, y un mismo `libro_id` MUST NOT aparecer en dos renglones.

#### Scenario: Sin renglones o cantidad no positiva

- **WHEN** el cuerpo tiene una lista vacía de renglones o un renglón con `cantidad` menor o igual a 0
- **THEN** responde 422 con el detalle de validación

#### Scenario: Libro repetido en dos renglones

- **WHEN** el cuerpo incluye dos renglones con el mismo `libro_id`
- **THEN** responde 422 con un mensaje propio de libro repetido

### Requirement: Renglón de venta con título y subtotal calculado

Cada renglón de la respuesta de una venta SHALL incluir el `titulo` del libro y el `subtotal` calculado como `cantidad × precio_unitario`, serializado como string decimal.

#### Scenario: Subtotal y título por renglón

- **WHEN** se responde una venta con renglones
- **THEN** cada renglón incluye `titulo`, `precio_unitario` y `subtotal` como string decimal, con `subtotal` igual a `cantidad × precio_unitario`
