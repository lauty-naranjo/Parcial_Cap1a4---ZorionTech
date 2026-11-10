# Spec Delta

## Purpose

Define el esquema de datos del dominio de la librería: las nueve tablas, sus columnas, restricciones con nombre, índices, integridad referencial y la navegación ORM bidireccional entre catálogo, clientes y ventas.

## ADDED Requirements

### Requirement: Tablas del catálogo

El sistema SHALL definir las tablas `editorial`, `genero` y `autor` con columnas `id` entera autoincremental como clave primaria. `editorial.nombre` SHALL ser UNIQUE y NOT NULL, `editorial.pais` SHALL ser NOT NULL, `genero.nombre` SHALL ser UNIQUE y NOT NULL, y `autor.nombre` y `autor.nacionalidad` SHALL ser NOT NULL.

#### Scenario: Columnas obligatorias del catálogo

- **WHEN** se inspecciona el metadata del esquema
- **THEN** existen `editorial` (id, nombre, pais), `genero` (id, nombre) y `autor` (id, nombre, nacionalidad), con unicidad en `editorial.nombre` y `genero.nombre`

### Requirement: Libro y sus restricciones

El sistema SHALL definir `libro` con `isbn` UNIQUE y NOT NULL, `titulo` NOT NULL, `precio` con CHECK `> 0`, `stock` con CHECK `>= 0`, `editorial_id` FK NOT NULL y `genero_id` FK nullable. El precio SHALL almacenarse como `Numeric(10,2)`.

#### Scenario: ISBN único y precio/stock válidos

- **WHEN** se inspecciona el metadata de `libro`
- **THEN** `isbn` es UNIQUE y NOT NULL, y existen CHECK que rechazan `precio <= 0` y `stock < 0`

### Requirement: Autoría como entidad de asociación

El sistema SHALL definir `libro_autor` con clave primaria compuesta `(libro_id, autor_id)`, `rol` restringido a los valores `autor`, `coautor`, `traductor` e `ilustrador`, y `orden` con CHECK `>= 1`. Ambas columnas SHALL ser FK hacia `libro` y `autor`.

#### Scenario: PK compuesta y rol restringido

- **WHEN** se inspecciona el metadata de `libro_autor`
- **THEN** la clave primaria es `(libro_id, autor_id)` y el CHECK de `rol` solo acepta los cuatro valores permitidos

### Requirement: Cliente y perfil uno a uno

El sistema SHALL definir `cliente` con `email` UNIQUE y NOT NULL, y `perfil_cliente` con `cliente_id` FK UNIQUE y NOT NULL. La relación SHALL ser uno a uno de modo que un cliente tenga como máximo un perfil.

#### Scenario: Un perfil por cliente

- **WHEN** se inspecciona el metadata de `perfil_cliente`
- **THEN** `cliente_id` es UNIQUE y NOT NULL, y la relación expone el perfil como objeto único y no como lista

### Requirement: Venta y renglones por composición

El sistema SHALL definir `venta` con `cliente_id` FK NOT NULL, `fecha` con zona horaria por defecto en UTC, `total Numeric(12,2)` con CHECK `>= 0`, y `renglon_venta` con `venta_id` FK con `ON DELETE CASCADE`, `libro_id` FK, `cantidad` con CHECK `> 0` y `precio_unitario Numeric(10,2)` con CHECK `> 0`.

#### Scenario: Venta con renglones persistidos

- **WHEN** se persiste una venta con sus renglones por composición
- **THEN** los renglones se guardan junto con la venta y se eliminan en cascada al borrar la venta

### Requirement: Restricciones con nombre explícito

Toda restricción UNIQUE, CHECK y FK del esquema SHALL declararse con un nombre explícito y estable que no dependa del autogenerado por el motor, para poder identificar el rechazo de la base sin exponer texto interno.

#### Scenario: Nombres de constraint predecibles

- **WHEN** se inspecciona el metadata de las nueve tablas
- **THEN** las restricciones UNIQUE, CHECK y FK tienen nombres de la convención `uq_*`, `ck_*` y `fk_*`, no autogenerados

### Requirement: Índices en claves foráneas y búsqueda por título

Toda columna FK del esquema SHALL tener índice explícito, y `libro.titulo` SHALL tener un índice btree para búsqueda parcial. `libro.isbn` y `cliente.email` SHALL estar cubiertos por su unicidad.

#### Scenario: FKs indexadas

- **WHEN** se inspecciona el metadata de índices
- **THEN** cada FK tiene su índice y `libro.titulo` tiene un índice btree

### Requirement: Navegación bidireccional

Las relaciones del modelo SHALL exponerse en ambos extremos, de modo que se pueda navegar de `Editorial` a sus `libros`, de `Libro` a sus `autorias` y de cada `LibroAutor` a su `autor`, de `Cliente` a su `perfil` y `ventas`, y de `Venta` a sus `renglones` y de cada `RenglonVenta` a su `libro`.

#### Scenario: Navegación libro-autor

- **WHEN** se recorre `libro.autorias[i].autor` con las relaciones cargadas
- **THEN** se obtiene el autor correspondiente de cada autoría sin consultas adicionales por fila

### Requirement: Importes y fechas sin pérdida de precisión

Los importes monetarios SHALL almacenarse como `Numeric` en la base y manipularse como `Decimal` en Python, nunca como punto flotante. La fecha de la venta SHALL ser con zona horaria y por defecto en UTC.

#### Scenario: Importes siempre Decimal

- **WHEN** se asigna o se lee `precio`, `total` o `precio_unitario`
- **THEN** el valor en Python es de tipo `Decimal`, no `float`

### Requirement: Creación idempotente del esquema

Al arrancar, el sistema SHALL crear las nueve tablas en una base vacía sin ejecutar migraciones y SHALL dejar intactas las tablas ya existentes.

#### Scenario: Base vacía

- **WHEN** la aplicación arranca contra una base accesible sin tablas del dominio
- **THEN** las nueve tablas quedan creadas y la aplicación comienza a atender peticiones
