# Design

## Context

C-04 está archivado y la suite tiene 215 tests en verde. El esquema de las nueve tablas, la configuración (`app/core/config.py`: `get_settings()` con `DATABASE_URL` obligatoria y carga de `.env`), la capa de datos (`build_engine`, `build_session_factory`) y los fixtures de PostgreSQL (`url_bd_test`, `motor_bd`, `fabrica_sesion_bd`, `cliente_bd`) ya existen. No hay ningún comando de seed y el `README.md` no lo documenta.

Restricciones que condicionan el diseño:

- Reglas duras de `AGENTS.md`: `Decimal` para dinero (A.1), sin credenciales en el repositorio (D.11), handlers/servicios asincrónicos y sin bloqueos (C.9), esquema con `create_all` y sin migraciones (A.4).
- `CHANGES.md` C-05: comando idempotente, datos compatibles con los ejemplos, sin credenciales hardcodeadas, documentado para `docker exec`.
- DD-10: seed como módulo ejecutable, mismo camino en local y en producción.
- SU-06: el seed debe reproducir «Rayuela» `25000.00`, «Respiración artificial» `27000.00`, editorial/género id 1, autores id 3 y 4 y cliente id 2 «Tomás Ríos».
- C-08 todavía no existe; su `Dockerfile` hará `COPY app ./app`. El seed debe vivir en `app/` para no necesitar otra instrucción `COPY`.

## Goals / Non-Goals

**Goals:**

- Dejar la base en un estado inicial determinista que reproduzca los ids de los ejemplos y el total `77000.00` de la venta 2.
- Ser seguro de re-ejecutar sin duplicar ni pisar datos.
- Evitar que los ids explícitos rompan las secuencias y la primera alta real por la API.
- Permitir que los tests apunten a `url_bd_test` sin tocar la base real ni depender de `.env`.
- Mantener el comando utilizable en local y en `docker exec`, sin secretos en la salida.

**Non-Goals:**

- No se modifica el esquema, los modelos ni los endpoints.
- No se crean perfiles de cliente ni datos adicionales fuera del conjunto acordado.
- No se implementan migraciones, borrado, `TRUNCATE` ni reseteo de la base.
- No se produce la evidencia de C-10 ni se completa el `README.md` de entrega (C-11).
- No se toca el `Dockerfile` (C-08); solo se deja el seed en la ruta que la imagen ya copia.

## Decisions

### 1. Ubicación `app/seed.py` y ejecución `python -m app.seed`

El seed vive en `app/seed.py` y se ejecuta con `python -m app.seed`. El `Dockerfile` de C-08 ya copia `app/`, así que el mismo archivo viaja en la imagen y se invoca con `docker exec libreria python -m app.seed`, sin una instrucción `COPY scripts` ni un archivo SQL externo.

**Alternativas consideradas**:

- `scripts/seed.py`: obliga a agregar `COPY scripts ./scripts` al Dockerfile y a mantener dos rutas de importación. Descartada porque el `Dockerfile` aprobado no necesita cambios.
- Un `.sql` externo: no es un módulo ejecutable, no reutiliza `Settings`/`build_engine` y no permite testear la función contra `url_bd_test`. Descartada.

### 2. Contenido exacto y determinista

El seed inserta ids explícitos para que los ejemplos y los casos D sean reproducibles. Los ids son identificadores, no un contador: la venta sembrada es la 2 y no se inventa una venta 1.

| Tabla | id | Valores |
|---|---|---|
| `editorial` | 1 | `nombre="Sudamericana"`, `pais="Argentina"` |
| `genero` | 1 | `nombre="Novela"` |
| `autor` | 1 | `nombre="Julio Cortázar"`, `nacionalidad="Argentina"` |
| `autor` | 2 | `nombre="Ricardo Piglia"`, `nacionalidad="Argentina"` |
| `autor` | 3 | `nombre="Gabriel García Márquez"`, `nacionalidad="Colombia"` |
| `autor` | 4 | `nombre="Mario Vargas Llosa"`, `nacionalidad="Perú"` |
| `libro` | 1 | `isbn="978-950-00-0001-1"`, `titulo="Rayuela"`, `precio=25000.00`, `stock=10`, `editorial_id=1`, `genero_id=1` |
| `libro` | 2 | `isbn="978-950-00-0002-8"`, `titulo="Antología del cuento latinoamericano"`, `precio=22000.00`, `stock=6`, `editorial_id=1`, `genero_id=1` |
| `libro` | 3 | `isbn="978-950-00-0003-5"`, `titulo="La ciudad y los perros"`, `precio=24000.00`, `stock=5`, `editorial_id=1`, `genero_id=1` |
| `libro` | 4 | `isbn="978-950-00-0004-2"`, `titulo="Respiración artificial"`, `precio=27000.00`, `stock=8`, `editorial_id=1`, `genero_id=1` |
| `libro_autor` | (1, 1) | `rol="autor"`, `orden=1` |
| `libro_autor` | (2, 3) | `rol="autor"`, `orden=1` |
| `libro_autor` | (2, 4) | `rol="coautor"`, `orden=2` |
| `libro_autor` | (3, 4) | `rol="autor"`, `orden=1` |
| `libro_autor` | (4, 2) | `rol="autor"`, `orden=1` |
| `cliente` | 1 | `nombre="Ana Gómez"`, `email="ana@example.com"` |
| `cliente` | 2 | `nombre="Tomás Ríos"`, `email="tomas@example.com"` |
| `venta` | 2 | `cliente_id=2`, `fecha=2026-11-01T12:00:00Z`, `total=77000.00` |
| `renglon_venta` | 1 | `venta_id=2`, `libro_id=1`, `cantidad=2`, `precio_unitario=25000.00` |
| `renglon_venta` | 2 | `venta_id=2`, `libro_id=4`, `cantidad=1`, `precio_unitario=27000.00` |

`perfil_cliente` queda vacía a propósito para que el caso D-05 pueda comprobar que `GET /clientes/{id}` devuelve `perfil: null`. La autoría `(2, 4)` con `rol="coautor"` ejercita el rol de coautor que usan los ejemplos.

Los autores 3 y 4 existen con ids fijos porque los ejemplos de la consigna los usan como coautores; en el seed también participan en el libro 2 para que el rol `coautor` quede representado.

### 3. Idempotencia con ids deterministas y `ON CONFLICT DO NOTHING`

Cada tabla se inserta en una sola sentencia multfila con `sqlalchemy.dialects.postgresql.insert(...).values([...]).on_conflict_do_nothing(index_elements=[...])`:

- Tablas con PK simple: `index_elements=["id"]`.
- `libro_autor`: `index_elements=["libro_id", "autor_id"]`.

El conflicto se declara **contra la PK** y no contra cualquier restricción. Así, un rerun sobre una base ya sembrada no duplica ni pisa, y cualquier choque de unicidad fuera del estado esperado (por ejemplo, un ISBN o un email ya usados por otra fila con otro id) aborta la transacción y se informa como error, en lugar de dejar referencias rotas silenciosamente.

Todas las inserciones, el reposicionamiento de secuencias y el `commit` ocurren en una sola transacción: si algo falla, se hace `rollback` y la base queda como estaba.

**Alternativas consideradas**:

- `session.merge`: inserta o **actualiza** la fila existente; un rerun pisaría cambios hechos por la API. Descartada.
- `SELECT` previo + `INSERT` condicional: agrega consultas, tiene ventana de carrera y complica el caso multfila. Descartada.
- `ON CONFLICT DO NOTHING` sin objetivo: silencia también conflictos de unicidad ajenos a la PK y puede dejar filas referenciadas sin insertar. Descartada.

### 4. Reposicionamiento obligatorio de secuencias con `setval`

Después de insertar ids explícitos, las secuencias `SERIAL` de PostgreSQL siguen en 1. Sin reposicionarlas, la primera alta real por la API intentaría usar un id ya sembrado y fallaría con `duplicate key value violates unique constraint ... pkey`.

Por cada tabla con PK entera (`autor`, `editorial`, `genero`, `libro`, `cliente`, `perfil_cliente`, `venta`, `renglon_venta`) se ejecuta:

```sql
SELECT setval(
    pg_get_serial_sequence('<tabla>', 'id'),
    COALESCE((SELECT MAX(id) FROM <tabla>), 1),
    (SELECT MAX(id) FROM <tabla>) IS NOT NULL
)
```

El tercer argumento (`is_called`) evita saltar el id 1 en una tabla vacía como `perfil_cliente`: con `is_called = false` el próximo `nextval` devuelve 1; con filas, devuelve `MAX(id) + 1`. `libro_autor` no tiene columna `id` ni secuencia y se omite.

Los nombres de tabla se intercalan desde una tupla constante y cerrada del módulo; no provienen de entrada del usuario. `setval` no es transaccional, por lo que un fallo posterior al `setval` puede dejar un hueco en la secuencia, pero nunca un id duplicado.

### 5. API del módulo y testeabilidad

`app/seed.py` expone:

```python
async def sembrar(url: str | None = None) -> dict[str, int]:
    ...

def main() -> int:
    ...

if __name__ == "__main__":
    raise SystemExit(main())
```

- `sembrar(url=None)`: si `url` es `None`, usa `get_settings().database_url`; en todos los casos crea el motor con `Settings(database_url=url, sql_echo=False)`, así que no hereda `SQL_ECHO` y, cuando recibe una URL, no lee `.env`. `main` resuelve `DATABASE_URL` y le pasa la URL explícita.
- `create_all` se ejecuta antes de la sesión, porque la base del VPS puede estar vacía.
- El motor se libera con `await engine.dispose()` en un `finally`.
- `sembrar` devuelve un diccionario `{tabla: conteo}` para que el CLI lo imprima y los tests puedan contrastarlo. Las excepciones se propagan para que los tests las vean; `main` las traduce a códigos de salida.
- Solo `main` usa `asyncio.run`; `sembrar` es `async def`.

`app/seed.py` importa explícitamente los seis módulos de `models` antes de `create_all`, igual que `app/main.py`, para que `SQLModel.metadata` tenga las nueve tablas. Se acepta esa duplicación mínima: crear un registro compartido en `app/core/` obligaría a tocar código de C-01/C-02 y queda fuera del alcance de C-05.

### 6. Salida, errores y credenciales

`main` imprime una sola línea con los conteos, por ejemplo:

```
Seed aplicado: editorial=1 genero=1 autor=4 libro=4 libro_autor=5 cliente=2 perfil_cliente=0 venta=1 renglon_venta=2
```

Nunca imprime `DATABASE_URL`, usuario, contraseña ni host. Los errores se escriben en `stderr` con mensajes genéricos y códigos de salida distintos de 0:

- `ConfigurationError` (falta `DATABASE_URL`): código 2, mensaje que nombra la variable.
- `IntegrityError` (datos incompatibles con los ids del seed): código 1, mensaje que sugiere revisar el estado de la base, sin traza ni texto de constraints.
- `SQLAlchemyError`/error de conexión: código 1, mensaje genérico de conexión.

No se usa `SQL_ECHO` en el seed para no volcar SQL ni parámetros a la salida.

### 7. Estrategia de tests

Nuevo `test/test_seed.py`, marcado `@pytest.mark.integration`, usando la fixture `url_bd_test` (se salta sin `DATABASE_URL`) y las fixtures existentes `motor_bd`, `sesion_bd` y `cliente_bd`:

1. **Doble ejecución**: `await sembrar(url_bd_test)` dos veces y comparar conteos de las nueve tablas; deben ser iguales a los esperados (`editorial=1`, `genero=1`, `autor=4`, `libro=4`, `libro_autor=5`, `cliente=2`, `perfil_cliente=0`, `venta=1`, `renglon_venta=2`).
2. **No sobrescritura**: sembrar, cambiar `libro 1.stock` a 99 por una sesión y volver a sembrar; el stock debe seguir en 99. Agregar una editorial extra y comprobar que el rerun no la borra.
3. **Secuencias**: sembrar y luego `POST /editoriales/` → id 2, `POST /libros/` → id 5 y `POST /ventas/` → id 3; todas deben responder 201, sin `duplicate key`.
4. **Catálogo**: `GET /libros/` devuelve cuatro libros con ids 1–4, «Rayuela» a `"25000.00"` y «Respiración artificial» a `"27000.00"`.
5. **Venta de ejemplo**: `GET /ventas/2` devuelve `total == "77000.00"`, dos renglones con cantidades 2 y 1, y subtotales `50000.00` y `27000.00`.
6. **Sin `DATABASE_URL`**: `monkeypatch.delenv("DATABASE_URL")` y `main()` devuelve 2 con un mensaje que menciona la variable y no contiene credenciales.

El test 3 es la prueba explícita del `setval`: sin el reposicionamiento falla con clave duplicada.

### 8. Documentación en `README.md`

Se agrega una sección «Datos iniciales (seed)» con:

```powershell
.venv\Scripts\python.exe -m app.seed
```

```bash
python -m app.seed
docker exec libreria python -m app.seed
```

Indica que requiere `DATABASE_URL`, que es idempotente y que no imprime la URL. C-11 completará el resto del README de entrega; C-05 no reescribe las secciones existentes.

## Risks / Trade-offs

- **Conflicto de unicidad fuera de los ids del seed** (otra fila ya usa el ISBN o el email) → la transacción aborta con un mensaje claro. Es el comportamiento buscado: el seed asume una base vacía o ya sembrada, no un estado arbitrario. Se documenta en el README.
- **`setval` sobre una tabla vacía** → se usa `is_called = false` para que el próximo id sea 1 y no 2.
- **`setval` no es transaccional** → un fallo posterior puede dejar un hueco en la secuencia, nunca un duplicado; los huecos no afectan a la API.
- **Dependencia de que las PK enteras sean `SERIAL`** → es el esquema de C-02; si alguna vez cambia a `IDENTITY` con otra secuencia, el test de secuencias lo detecta.
- **Duplicación del registro de modelos entre `app/main.py` y `app/seed.py`** → se limita a seis imports y evita tocar el arranque de C-01; si aparece un tercer consumidor, se podrá extraer un registro compartido.
- **Fecha fija de la venta** (`2026-11-01T12:00:00Z`) → hace la evidencia reproducible; no pretende ser la fecha real de ejecución.
- **Ids no contiguos** (no hay venta 1) → los ids son identificadores; D-03 usa la venta 2 y no depende de que exista la 1.

## Migration Plan

No hay migración de esquema ni de datos. El seed es aditivo y se ejecuta una vez sobre la base local o del VPS (C-09) después de construir la imagen. Si se necesita revertir, se restauran las filas sembradas desde un respaldo o se eliminan solo esas filas por id; el seed no borra datos existentes. Los cambios son compatibles con los tests y endpoints actuales.

## Open Questions

Ninguna que cambie las specs, el enfoque o el desglose de tareas. El contenido exacto, la ruta, la estrategia de idempotencia, el `setval` y la inclusión de la venta 2 quedan resueltos en este documento.
