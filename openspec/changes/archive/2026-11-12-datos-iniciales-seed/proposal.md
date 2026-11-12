# Proposal

## Why

La suite está en verde (215 tests) y el esquema y los endpoints ya existen, pero una base recién creada queda **vacía**: los casos de la consigna que referencian ids fijos (libro 1 «Rayuela», libro 4 «Respiración artificial», cliente 2 «Tomás Ríos» y venta 2 con total `77000.00`) no se pueden reproducir, la evidencia de D-03 no se puede generar y C-09 no tiene un comando para dejar la base del VPS en un estado conocido. C-05 cubre esa higiene y es prerequisito del despliegue.

## What Changes

- Se agrega `app/seed.py`, ejecutable con `python -m app.seed`, que crea el esquema faltante con `SQLModel.metadata.create_all`, abre una sesión desde `DATABASE_URL`, carga el conjunto inicial y libera el motor al terminar.
- El comando es **idempotente**: correrlo dos veces no duplica filas ni pisa datos existentes. Usa ids deterministas y `INSERT ... ON CONFLICT DO NOTHING` sobre la clave primaria.
- Tras insertar ids explícitos, **reposiciona las secuencias** con `setval(pg_get_serial_sequence(...), MAX(id))`, para que la primera alta real por la API no colisione con la PK.
- Carga datos compatibles con los ejemplos: editorial id 1, género id 1, cuatro autores (ids 1–4), cuatro libros (id 1 «Rayuela» `25000.00`, id 4 «Respiración artificial» `27000.00`), dos clientes (id 2 «Tomás Ríos» / `tomas@example.com`) y la venta id 2 con dos renglones (Rayuela ×2 + Respiración artificial ×1 = `77000.00`).
- Toma `DATABASE_URL` del entorno (nunca hardcodeada), falla con un mensaje claro si falta y **no imprime la URL ni credenciales**; la salida final solo muestra conteos por tabla.
- Documenta el comando en `README.md` y lo deja listo para `docker exec libreria python -m app.seed`.
- Agrega tests que ejecutan el seed dos veces, verifican conteos, comprueban que no se pisan datos, confirman que una alta por API funciona después del seed (prueba del `setval`), validan los cuatro libros en `GET /libros/` y reproducen el total `77000.00` de la venta 2.

**Fuera de alcance**: no se modifica el esquema ni los modelos, no se agregan ni cambian endpoints, no se crean perfiles de cliente, no se implementan migraciones, no se escribe la evidencia de C-10, no se toca el `Dockerfile` (lo hace C-08) y el `README.md` solo recibe la sección del seed (C-11 lo completa).

## Capabilities

### New Capabilities

- `seed-data`: comando de datos iniciales, contenido determinista compatible con los ejemplos, idempotencia sin sobrescritura, alineación de secuencias y ejecución local/contenedor sin credenciales en el código.

### Modified Capabilities

<!-- Ninguna: no cambia el contrato de la API, el esquema ni el ciclo de vida de la aplicación; el seed es una capacidad nueva de aprovisionamiento de datos. -->

## Impact

- **Código**: nuevo `app/seed.py`; no se modifica ningún módulo existente. El archivo viaja en la imagen porque C-08 ya hace `COPY app ./app`.
- **Base de datos**: se insertan filas con ids explícitos en `editorial`, `genero`, `autor`, `libro`, `libro_autor`, `cliente`, `venta` y `renglon_venta`; `perfil_cliente` queda vacía a propósito. No hay cambios de esquema. Las secuencias de las tablas con PK entera quedan en `MAX(id)`.
- **API**: sin cambios de contrato; los tests usan `GET /libros/`, `GET /ventas/{id}` y las altas existentes para verificar el estado sembrado.
- **Dependencias**: ninguna nueva; se usa el dialecto PostgreSQL de SQLAlchemy y los helpers `build_engine`/`build_session_factory` de C-01.
- **Tests**: nuevo `test/test_seed.py` con pruebas de doble ejecución, no sobrescritura, secuencias, catálogo y venta de ejemplo.
- **Documentación**: nueva sección «Datos iniciales (seed)» en `README.md`, con el comando local y el de `docker exec`.
- **Riesgo principal**: insertar ids explícitos sin reposicionar secuencias rompe la primera alta por la API con `duplicate key ... pkey`; el `setval` y su test son parte obligatoria del change.
