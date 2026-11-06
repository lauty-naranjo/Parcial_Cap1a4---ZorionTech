# Modelo de Datos

> **Regla dura de la consigna**: los nombres de tablas y columnas son obligatorios —los usan los casos de prueba y la corrección—. Se pueden agregar columnas, pero **no quitar ni renombrar** las indicadas.

## Dominios

| Dominio | Entidades | Descripción |
|---|---|---|
| Catálogo | `editorial`, `genero`, `autor`, `libro`, `libro_autor` | Libros y sus clasificaciones; autorías con rol y orden |
| Clientes | `cliente`, `perfil_cliente` | Datos del comprador y su perfil uno a uno |
| Ventas | `venta`, `renglon_venta` | Hecho de venta inmutable y sus renglones (composición) |

## ERD

```
                 ┌───────────────┐
                 │   editorial   │
                 │ id (PK)       │
                 │ nombre UNIQUE │
                 │ pais          │
                 └──────┬────────┘
                        │ 1
                        │        agregación (FK editorial_id, NOT NULL)
                        │ N
┌───────────────┐   ┌───▼────────────────────────┐   ┌───────────────┐
│    genero     │   │           libro            │   │    autor      │
│ id (PK)       │   │ id (PK)                    │   │ id (PK)       │
│ nombre UNIQUE │   │ isbn UNIQUE                │   │ nombre        │
└───────┬───────┘   │ titulo                     │   │ nacionalidad  │
        │ 0..1      │ precio NUMERIC(10,2) >0    │   └───────┬───────┘
        │           │ stock >=0                  │           │
        │           │ editorial_id (FK, NOT NULL)│           │
        └──────────►│ genero_id (FK, NULL)       │           │
   agregación       └───┬────────────────────┬───┘           │
   opcional             │ 1                  │ 1             │
                        │                    │               │
                        │ N                  │ N             │ N
                   ┌────▼────────────────────▼───────────────▼────┐
                   │                 libro_autor                   │
                   │ PK (libro_id, autor_id)                       │
                   │ rol  CHECK: autor|coautor|traductor|ilustrador │
                   │ orden CHECK >= 1                              │
                   └───────────────────────────────────────────────┘
                        muchos a muchos CON DATOS de relación

┌───────────────┐        ┌──────────────────────┐
│   cliente     │ 1    0..1 ┌──────────────────┐│
│ id (PK)       ├───────────►│  perfil_cliente  ││
│ nombre        │            │ id (PK)          ││
│ email UNIQUE  │            │ cliente_id UNIQUE││
└───────┬───────┘            │ telefono         ││
        │ 1                  │ direccion        ││
        │                    └──────────────────┘│
        │ N  asociación (FK cliente_id)          │
┌───────▼──────────────────────────────┐         │
│               venta                  │         │
│ id (PK)                              │         │
│ cliente_id (FK)                      │         │
│ fecha TIMESTAMPTZ                    │         │
│ total NUMERIC(12,2) CHECK >= 0       │         │
└───────┬──────────────────────────────┘         │
        │ 1  composición (FK venta_id, ON DELETE CASCADE) │
        │ N                                       │
┌───────▼──────────────────────────────┐         │
│           renglon_venta              │         │
│ id (PK)                              │         │
│ venta_id (FK)                        │         │
│ libro_id (FK) ───────────────────────┼─────────┘  asociación con libro
│ cantidad CHECK > 0                   │
│ precio_unitario NUMERIC(10,2) > 0    │
└──────────────────────────────────────┘
```

## Entidades

### `editorial`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | Integer | PK, autoincremental |
| `nombre` | String | **UNIQUE**, NOT NULL |
| `pais` | String | NOT NULL |

- Relaciones: `libros: list[Libro]` ← `Libro.editorial` (`back_populates="editorial"`).
- Semántica: **agregación**. La editorial existe por sí misma; el libro incorpora su `id`.

### `genero`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | Integer | PK, autoincremental |
| `nombre` | String | **UNIQUE**, NOT NULL |

- Relaciones: `libros: list[Libro]` ← `Libro.genero`.
- Semántica: **agregación opcional** desde el lado del libro.

### `autor`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | Integer | PK, autoincremental |
| `nombre` | String | NOT NULL |
| `nacionalidad` | String | NOT NULL |

- Relaciones: `autorias: list[LibroAutor]` ← `LibroAutor.autor`.
- Sin restricciones extra (no hay unicidad de nombre).

### `libro`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | Integer | PK, autoincremental |
| `isbn` | String | **UNIQUE**, NOT NULL (RN-01) |
| `titulo` | String | NOT NULL; indexado para búsqueda |
| `precio` | `Numeric(10, 2)` | **CHECK `precio > 0`** (RN-03) |
| `stock` | Integer | **CHECK `stock >= 0`** (RN-03) |
| `editorial_id` | Integer | **FK → `editorial.id`**, NOT NULL, **indexado** |
| `genero_id` | Integer | **FK → `genero.id`**, NULL permitido, **indexado** |

- Relaciones:
  - `editorial: Editorial` ↔ `Editorial.libros` — `joinedload`.
  - `genero: Genero | None` ↔ `Genero.libros` — `joinedload`.
  - `autorias: list[LibroAutor]` ↔ `LibroAutor.libro` — `selectinload`; se navega `libro.autorias[i].autor`.
  - `renglones: list[RenglonVenta]` ↔ `RenglonVenta.libro`.
- Semántica: agregación (editorial) y agregación opcional (género). **No** es composición: borrar un libro no debe borrar su editorial.

### `libro_autor` (objeto de asociación, no `link_model`)

| Columna | Tipo | Restricciones |
|---|---|---|
| `libro_id` | Integer | **FK → `libro.id`**, parte de la PK compuesta, indexado |
| `autor_id` | Integer | **FK → `autor.id`**, parte de la PK compuesta, indexado |
| `rol` | String / Enum | **CHECK** ∈ {`autor`, `coautor`, `traductor`, `ilustrador`} |
| `orden` | Integer | **CHECK `orden >= 1`** |

- **PK compuesta `(libro_id, autor_id)`**: un autor no puede repetirse en el mismo libro.
- Relaciones: `libro: Libro`, `autor: Autor` (ambas `back_populates`).
- Se modela como entidad propia porque `rol` y `orden` **no son ni del libro ni del autor**: son de la relación. Una relación muchos a muchos con `link_model` escondería esos datos.

### `cliente`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | Integer | PK, autoincremental |
| `nombre` | String | NOT NULL |
| `email` | String | **UNIQUE**, NOT NULL (RN-02) |

- Relaciones:
  - `perfil: PerfilCliente | None` ↔ `PerfilCliente.cliente` — **uno a uno**, `joinedload`. Debe devolver un objeto, **no una lista**.
  - `ventas: list[Venta]` ↔ `Venta.cliente`.

### `perfil_cliente`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | Integer | PK, autoincremental |
| `cliente_id` | Integer | **FK → `cliente.id`**, **UNIQUE**, NOT NULL, indexado (RN-09) |
| `telefono` | String | NOT NULL |
| `direccion` | String | NOT NULL |

- Relaciones: `cliente: Cliente` ↔ `Cliente.perfil`.
- Semántica: **uno a uno**. El `UNIQUE` sobre `cliente_id` es lo que garantiza "como máximo un perfil" en la base, no una consulta previa.

### `venta`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | Integer | PK, autoincremental |
| `cliente_id` | Integer | **FK → `cliente.id`**, NOT NULL, indexado |
| `fecha` | `DateTime(timezone=True)` | NOT NULL, por defecto UTC `now()` |
| `total` | `Numeric(12, 2)` | **CHECK `total >= 0`** (RN-07) |

- Relaciones:
  - `cliente: Cliente` ↔ `Cliente.ventas` — asociación, `joinedload`.
  - `renglones: list[RenglonVenta]` ↔ `RenglonVenta.venta` — composición, `selectinload`, `cascade="all, delete-orphan"`.
- Semántica: **asociación** con cliente (la venta conoce al cliente, ninguno es parte del otro) y **composición** con renglones.

### `renglon_venta`

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | Integer | PK, autoincremental |
| `venta_id` | Integer | **FK → `venta.id`**, NOT NULL, indexado, `ON DELETE CASCADE` |
| `libro_id` | Integer | **FK → `libro.id`**, NOT NULL, indexado |
| `cantidad` | Integer | **CHECK `cantidad > 0`** |
| `precio_unitario` | `Numeric(10, 2)` | **CHECK `precio_unitario > 0`** |

- Relaciones: `venta: Venta`, `libro: Libro`.
- `subtotal` **no es columna**: se calcula en el DTO de salida como `cantidad × precio_unitario`.
- Semántica: composición con la venta (nace y muere con ella) y asociación con el libro (referencia un libro existente).

## Índices

| Índice | Motivo |
|---|---|
| `libro.isbn` UNIQUE | RN-01, búsqueda por ISBN |
| `cliente.email` UNIQUE | RN-02 |
| `perfil_cliente.cliente_id` UNIQUE | RN-09 (uno a uno) |
| `libro_autor` PK `(libro_id, autor_id)` | Unicidad de la autoría y acceso por libro |
| `libro_autor.autor_id` | Acceso por autor (`/autores/{id}/libros`) |
| `libro.editorial_id`, `libro.genero_id` | Filtros y listados por editorial/género |
| `venta.cliente_id` | `/clientes/{id}/ventas` |
| `renglon_venta.venta_id`, `renglon_venta.libro_id` | Composición y detalle |
| `libro.titulo` (recomendado, btree) | Búsqueda por parte del título |

> PostgreSQL **no crea índices automáticamente** para las claves foráneas: cada FK del esquema lleva su índice explícito.

## Reglas de mapeo relacional (justificación del lado de cada FK)

| Relación | Tipo | Dónde va la FK | Por qué |
|---|---|---|---|
| Libro–Editorial | Agregación | `libro.editorial_id` | Un libro tiene una editorial; una editorial tiene muchos libros. La FK va del lado "muchos". |
| Libro–Género | Agregación opcional | `libro.genero_id` (nullable) | Un libro puede no tener género; el género no depende del libro. |
| Libro–Autor | M2M con datos | Tabla intermedia `libro_autor` | Ambos lados son "muchos" y la relación tiene atributos propios (`rol`, `orden`). |
| Cliente–Perfil | Uno a uno | `perfil_cliente.cliente_id` UNIQUE | El perfil depende funcionalmente del cliente; el UNIQUE lo hace 1:1 y permite `perfil` nulo. |
| Venta–Cliente | Asociación | `venta.cliente_id` | La venta conoce a su cliente; el cliente no es parte de la venta. |
| Venta–Renglón | Composición | `renglon_venta.venta_id` | El renglón no existe sin la venta: la FK va del lado "parte" y cascadea. |
| Renglón–Libro | Asociación | `renglon_venta.libro_id` | El renglón referencia un libro ya existente; el libro no depende del renglón. |

## Seed data inicial

El proyecto debe incluir un script o comando que deje la base en un estado inicial conocido (lo invoca también `docker exec libreria …` en el VPS). Contenido mínimo coherente con los ejemplos de la consigna:

| Tabla | Datos de ejemplo |
|---|---|
| `editorial` | al menos 1 (ej. id 1, usada por el libro de ejemplo) |
| `genero` | al menos 1 (ej. id 1) |
| `autor` | al menos 4 (ids 3 y 4 usados como coautores en el ejemplo) |
| `libro` | al menos 4 (ids 1 "Rayuela" a 25000.00, id 4 "Respiración artificial" a 27000.00) |
| `cliente` | al menos 2 (id 2 "Tomás Ríos" / tomas@example.com) |
| `venta` + `renglon_venta` | opcional; el ejemplo de la consigna crea la venta id 2 |

> El script debe ser **idempotente o re-ejecutable** sobre una base vacía, y no debe requerir credenciales hardcodeadas: toma `DATABASE_URL` del entorno. Los datos exactos son una decisión abierta (ver `10_preguntas_abiertas.md`).
