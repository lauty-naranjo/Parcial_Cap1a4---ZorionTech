# Proposal

## Why

C-01 dejó la aplicación arrancando contra una base vacía: el `lifespan` ya importa los siete módulos de `models` y ejecuta `SQLModel.metadata.create_all`, pero esos módulos están vacíos, así que hoy no se crea ninguna tabla del dominio. Sin el esquema de datos no hay nada que los changes siguientes (CRUD en C-03, altas con relaciones en C-04, lecturas sin N+1 en C-06) puedan leer ni escribir.

Este change materializa las nueve tablas del modelo de datos de `knowledge-base/04_modelo_de_datos.md` con sus restricciones con nombre, índices y navegación bidireccional. Es el esquema que **todos** los demás changes referencian, por eso no se paraleliza con nada y su corrección condiciona el 22% de la nota.

## What Changes

- Se rellenan los `models.py` vacíos de los módulos `editoriales`, `generos`, `autores`, `libros`, `clientes` y `ventas` con las nueve tablas del dominio: `editorial`, `genero`, `autor`, `libro`, `libro_autor`, `cliente`, `perfil_cliente`, `venta` y `renglon_venta`.
- Cada tabla declara sus constraints **con nombre explícito** y convención estable (`uq_*`, `ck_*`, `fk_*`, `pk_*`), para que C-03/C-04 mapeen `IntegrityError` por nombre de constraint y nunca filtren texto de PostgreSQL (RN-12, DD-05).
- Los importes se modelan `Numeric` en la base y `Decimal` en Python (RN-G-01): `libro.precio Numeric(10,2)`, `venta.total Numeric(12,2)`, `renglon_venta.precio_unitario Numeric(10,2)`.
- Navegación bidireccional en los ocho pares de relación con `Relationship(back_populates=...)`, incluida la 1:1 `Cliente.perfil` (con `uselist=False`) y la composición `Venta.renglones` (`cascade="all, delete-orphan"`).
- Índices explícitos en toda FK y en `libro.titulo` (btree, RN-11); `libro.isbn` y `cliente.email` quedan UNIQUE.
- `libro_autor` como entidad de asociación propia (DD-01) con PK compuesta `(libro_id, autor_id)`, `rol` con CHECK de cuatro valores y `orden` con CHECK `>= 1`.
- `SQLModel.metadata.create_all` del lifespan pasa a crear las nueve tablas al arrancar sobre una base vacía (RN-G-05); no se agregan migraciones ni Alembic (DD-06).

## Capabilities

### New Capabilities

- `data-model`: el modelo de datos del dominio — tablas, columnas, restricciones con nombre, índices, integridad referencial y navegación ORM bidireccional entre las entidades de catálogo, clientes y ventas.

### Modified Capabilities

<!-- Ninguna: las specs `app-foundation` y `health-checks` no cambian su comportamiento a nivel de requisito. El lifespan ya ejecuta `create_all`; este change solo hace que el metadata registre tablas nuevas. -->

## Impact

- **Código**: `app/modules/{editoriales,generos,autores,libros,clientes,ventas}/models.py` (hoy vacíos) pasan a definir los modelos. `app/main.py` no cambia: ya importa esos módulos antes de `create_all`.
- **Base de datos**: al próximo arranque contra una base vacía se crean nueve tablas. Sobre una base ya creada, `create_all` no altera tablas existentes (RN-G-05).
- **Dependencias**: ninguna nueva; se usan `sqlmodel`, `sqlalchemy` y `decimal` del stdlib.
- **Tests**: se agrega cobertura de metadata (constraints, PK compuesta, FKs, índices, tipos `Numeric`), de `Cliente.perfil` como escalar, de composición de venta con renglones y de que los importes son siempre `Decimal`.
- **Riesgo principal**: la convención de nombres de constraints es contrato para C-03/C-04; un nombre mal elegido obliga a tocar código posterior. Se fija en `design.md` y se valida contra el metadata real en tests.
