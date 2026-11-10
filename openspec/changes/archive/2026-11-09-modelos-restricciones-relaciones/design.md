# Design

## Context

C-01 dejó el `lifespan` importando siete módulos `models` vacíos y ejecutando `SQLModel.metadata.create_all` contra una base sin tablas del dominio. La motivación está en `proposal.md`. Este diseño fija **cómo** se mapean las nueve tablas de `knowledge-base/04_modelo_de_datos.md` a SQLModel/SQLAlchemy 2.0 con las reglas duras del proyecto.

Restricciones que condicionan el diseño:

- Los nombres de tablas y columnas son **obligatorios** (los usa la corrección): solo se agregan columnas, no se renombran ni quitan.
- Los constraints deben tener **nombre explícito** para que C-03/C-04 mapeen `IntegrityError` por nombre y nunca filtren texto de PostgreSQL (RN-12, DD-05).
- Sin Alembic: `create_all` en el lifespan (DD-06, RN-G-05).
- Dinero siempre `Numeric`/`Decimal`, nunca `float` (RN-G-01).
- Prohibida la carga perezosa (RN-G-03): las relaciones se precargan en la misma consulta.

## Goals / Non-Goals

**Goals:**

- Mapear las nueve tablas con tipos exactos, nullability y restricciones de `04_modelo_de_datos.md`.
- Fijar una convención de nombres de constraints estable y predecible, lista completa incluida.
- Navegación ORM bidireccional en los ocho pares de relación, con `Cliente.perfil` como objeto (no lista) y `Venta.renglones` por composición.
- Importes `Decimal`, fecha con zona horaria en UTC.

**Non-Goals:**

- No hay DTO, schemas, routers, servicios ni seed (C-03/C-04/C-05).
- No se agrega borrado de recursos ni lógica de negocio.
- No se cambia `app/main.py` ni el `lifespan` (ya importa los módulos y ejecuta `create_all`).

## Decisions

### 1. Constraints con nombre explícito en `__table_args__`, sin naming convention global

**Decisión**: declarar cada UNIQUE, CHECK y FK explícitamente con `name=...` (o `sa.ForeignKeyConstraint`/`sa.ForeignKey(..., name=...)`), en lugar de depender de `Field(unique=True)`/`Field(ge=...)` (que generan nombres autogenerados) o de una `naming_convention` sobre `SQLModel.metadata`.

**Razón**: `Field(unique=True)` produce `uq_<tabla>` (no distingue columnas) y `Field(ge=...)` produce un CHECK sin nombre útil; una `naming_convention` exige reasignar `SQLModel.metadata` antes de importar cualquier modelo, lo que es frágil con la estructura actual. Lo explícito es determinista e independiente del orden de import.

**Alternativa considerada**: `naming_convention` global. Descartada por la fragilidad del orden de import y porque su plantilla FK (`..._%(column_0_name)s_%(referred_table_name)s`) no produce `fk_libro_editorial_id` como pide `CHANGES.md`.

**Patrón de implementación (para el apply):**

- Columna FK nombrada: `editorial_id: int = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("editorial.id", name="fk_libro_editorial_id"), nullable=False, index=True))`.
- UNIQUE: `__table_args__ = (sa.UniqueConstraint("nombre", name="uq_editorial_nombre"),)`.
- CHECK: `sa.CheckConstraint("precio > 0", name="ck_libro_precio_positivo")`.
- PK compuesta: `libro_id`/`autor_id` con `primary_key=True` y `sa_column=sa.Column(sa.Integer, sa.ForeignKey("libro.id", name="fk_libro_autor_libro_id"), primary_key=True)`. El nombre de la PK compuesta no es relevante para el mapeo de errores (la unicidad de autor por libro la anticipa el DTO en C-04); se acepta el default del motor.

### 2. Convención y lista completa de nombres

Convención: `uq_<tabla>_<columna>`, `ck_<tabla>_<motivo>`, `fk_<tabla>_<columna>`; índices `ix_<tabla>_<columna>` (auto al usar `index=True`).

| Tabla | Tipo | Nombre | Definición |
|---|---|---|---|
| `editorial` | PK | — | `id` |
| `editorial` | UNIQUE | `uq_editorial_nombre` | `nombre` |
| `genero` | UNIQUE | `uq_genero_nombre` | `nombre` |
| `libro` | UNIQUE | `uq_libro_isbn` | `isbn` |
| `libro` | CHECK | `ck_libro_precio_positivo` | `precio > 0` |
| `libro` | CHECK | `ck_libro_stock_no_negativo` | `stock >= 0` |
| `libro` | FK | `fk_libro_editorial_id` | `editorial_id → editorial.id` |
| `libro` | FK | `fk_libro_genero_id` | `genero_id → genero.id` (nullable) |
| `libro_autor` | CHECK | `ck_libro_autor_rol` | `rol IN ('autor','coautor','traductor','ilustrador')` |
| `libro_autor` | CHECK | `ck_libro_autor_orden` | `orden >= 1` |
| `libro_autor` | FK | `fk_libro_autor_libro_id` | `libro_id → libro.id` (parte de PK) |
| `libro_autor` | FK | `fk_libro_autor_autor_id` | `autor_id → autor.id` (parte de PK) |
| `cliente` | UNIQUE | `uq_cliente_email` | `email` |
| `perfil_cliente` | UNIQUE | `uq_perfil_cliente_cliente_id` | `cliente_id` |
| `perfil_cliente` | FK | `fk_perfil_cliente_cliente_id` | `cliente_id → cliente.id` |
| `venta` | CHECK | `ck_venta_total_no_negativo` | `total >= 0` |
| `venta` | FK | `fk_venta_cliente_id` | `cliente_id → cliente.id` |
| `renglon_venta` | CHECK | `ck_renglon_venta_cantidad_positiva` | `cantidad > 0` |
| `renglon_venta` | CHECK | `ck_renglon_venta_precio_positivo` | `precio_unitario > 0` |
| `renglon_venta` | FK | `fk_renglon_venta_venta_id` | `venta_id → venta.id` (`ON DELETE CASCADE`) |
| `renglon_venta` | FK | `fk_renglon_venta_libro_id` | `libro_id → libro.id` |

### 3. Importes y fechas

- `libro.precio` → `sa.Column(sa.Numeric(10, 2), nullable=False)`; `venta.total` → `sa.Numeric(12, 2)` con default Python `Decimal("0.00")`; `renglon_venta.precio_unitario` → `sa.Numeric(10, 2)`. `sa.Numeric` entrega `decimal.Decimal` (`asdecimal=True` por defecto).
- `venta.fecha` → `sa.Column(sa.DateTime(timezone=True), nullable=False, default=utc_now)` con `utc_now()` que devuelve `datetime.now(timezone.utc)` (tz-aware, coherente con IN-05). Sin `server_default`: la fecha la pone el servidor de aplicación (RN-G-06), no el reloj de la base.

### 4. Navegación y estrategia de carga perezosa

- Relaciones en ambos extremos con `Relationship(back_populates=...)` y referencias por **string** (`"Libro"`, `"LibroAutor"`) + `from __future__ import annotations` para romper los imports circulares entre módulos.
- **`lazy="raise"` en todas las relaciones** para hacer cumplir RN-G-03 de forma estricta: cualquier acceso a una relación no precargada lanza `InvalidRequestError` en lugar de ejecutar una consulta perezosa. Los servicios (C-04/C-06) cargan explícitamente con `joinedload`/`selectinload`, que es lo que da el número fijo de consultas (IN-04).
  - `Libro.genero` y `Cliente.perfil` son opcionales; con `joinedload` devuelven `None` correctamente cuando no hay fila.
- `Cliente.perfil`: `uselist=False` + `back_populates="cliente"`; la unicidad real la da `uq_perfil_cliente_cliente_id` en la base (DD-02).
- `Venta.renglones`: `cascade="all, delete-orphan"`, `passive_deletes=True` y `ondelete="CASCADE"` en la FK. `passive_deletes` delega el borrado en el `ON DELETE CASCADE` de la base (un solo `DELETE` sobre `venta`, sin N+1 de renglones). El `delete-orphan` sigue vigente para renglones descolgados de la colección.

**Alternativa considerada**: `lazy="selectin"` como default seguro. Descartada porque ocultaría un olvido de precarga y haría menos predecible el conteo de consultas que C-06 debe demostrar. El costo (`raise` si se olvida el eager load) es deliberado y lo capturan los tests.

### 5. Índices

- Toda FK lleva `index=True` en su `sa.Column` (auto `ix_<tabla>_<columna>`). En `libro_autor`, `libro_id` queda cubierto por el prefijo de la PK compuesta; `autor_id` lleva `index=True` explícito (`ix_libro_autor_autor_id`) para `/autores/{id}/libros`.
- `libro.titulo` con `sa.Index("ix_libro_titulo", "titulo")` (btree por defecto) para RN-11.
- `libro.isbn` y `cliente.email` ya están cubiertos por su UNIQUE.

### 6. Longitudes y tipos de texto

Sin especificación en la KB; se fijan longitudes conservadoras: `sa.String(255)` para nombres, `titulo`, `email`, `isbn`, `nacionalidad`, `pais`, `direccion`, `telefono`; `sa.String(20)` para `rol`. `isbn` sin longitud rígida (la corrección valida unicidad, no formato). Detalle de implementación, no contrato.

## Risks / Trade-offs

- **Olvido de `joinedload`/`selectinload` rompe en runtime (`InvalidRequestError`)** → mitigación: tests de C-02/C-06 siempre leen con eager load; el fallo es ruidoso y localizable, no un N+1 silencioso.
- **Nombre de constraint mal escrito obliga a tocar C-03/C-04** → mitigación: tests de metadata en C-02 asertan los nombres exactos de la tabla de la Decisión 2.
- **`create_all` no migra tablas ya creadas** (RN-G-05) → mitigación: sobre una base con tablas previas incompatibles hay que recrearla; documentado y fuera de alcance (sin Alembic por decisión de cátedra).
- **`passive_deletes=True` depende del `ON DELETE CASCADE` real en la FK** → mitigación: se declara `ondelete="CASCADE"` en `fk_renglon_venta_venta_id` y el test de cascada lo verifica contra la base.
- **`rol` como `String` + CHECK** (no Enum Python) → si C-03/C-04 quieren validación 422 temprana, usarán `Literal` en el DTO; el CHECK de base queda como última defensa.

## Migration Plan

No hay migración de datos: el esquema se crea al arrancar sobre base vacía (DD-06). En un entorno con la base ya creada por C-01 (que no creó tablas de dominio), el próximo arranque crea las nueve tablas nuevas sin tocar nada existente.

## Open Questions

Ninguna: las decisiones de este change están cerradas por `knowledge-base/04_modelo_de_datos.md`, `09_decisiones_y_supuestos.md` y `CHANGES.md`.
