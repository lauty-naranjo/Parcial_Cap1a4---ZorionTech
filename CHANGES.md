# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **ZorionTech — Librería de barrio** (Parcial Cap. 1 a 4, Programación III).
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**
> La consigna completa está en [`docs/consigna-parcial-cap1a4.md`](docs/consigna-parcial-cap1a4.md); la knowledge base operativa, en [`knowledge-base/`](knowledge-base/).

---

## Cómo usar este documento

1. Identificar el change a implementar y verificar que sus dependencias estén archivadas en `openspec/changes/archive/`. Si falta una, no arrancar.
2. Leer los archivos de `knowledge-base/` que figuran en **Leer antes**; son el contrato operativo. Si hay conflicto, manda la consigna original.
3. Ejecutar `/opsx:propose <nombre-del-change>` con el nombre kebab-case (sin el `C-NN`). Los artefactos se escriben en español; los encabezados estructurales y `SHALL`/`MUST` quedan en inglés (`openspec/config.yaml`).
4. Implementar, probar con `test/*.http` y los casos C/D que correspondan, y archivar con `/opsx:archive <nombre-del-change>`.
5. Marcar `[x]` en este archivo y adjuntar la salida a `evidencia/` cuando el change la produzca.

### Ponderación de la corrección

| Ejercicio | Criterio | Peso | Change |
|---|---|---|---|
| 1 | Proyecto, conexión y ciclo de vida | **8%** | C-01 |
| 2 | Modelos, restricciones y relaciones | **22%** | C-02 |
| 3 | Contratos y CRUD | **12%** | C-03 |
| 4 | Altas con relaciones | **17%** | C-04 |
| 5 | Lecturas sin N+1 | **8%** | C-06 |
| 6 | Asincronía sin bloqueos | **8%** | C-07 |
| 7 | Contenedor: la imagen | **15%** | C-08 |
| 8 | Despliegue en el VPS | **10%** | C-09 |
| — | Higiene: seed, pruebas, evidencia, README/entrega | 0% directo | C-05, C-10, C-11 |

### Fuera de alcance (no crear changes para esto)

- Autenticación y autorización, usuarios, tokens o RBAC (capítulo 5).
- Repositorios y Unit of Work (capítulo 6).
- Redis, colas de tareas o workers (capítulos 7 y 8).
- Docker Compose: el despliegue es de una sola imagen y la base no va en el paquete.
- Migraciones o Alembic: el esquema se crea con `SQLModel.metadata.create_all` al arrancar.
- Endpoints `DELETE` no listados; las ventas no tienen `PATCH` ni `PUT`.
- Frontend o interfaz web: el entregable es la API y su documentación.

### Reglas transversales

- Los nombres de tablas y columnas son obligatorios; se pueden agregar columnas, nunca quitar ni renombrar.
- El dinero va con `Decimal`/`Numeric` y se serializa como string decimal (`"25000.00"`), nunca `float`.
- Todos los handlers son `async def` y no ejecutan llamadas bloqueantes.
- La carga perezosa está prohibida: toda relación que se lee se precarga en la misma consulta.
- En altas, un id inexistente o un UNIQUE repetido se traduce a **409**; el **404** es solo para lecturas y `PATCH` de un recurso que no existe; el contrato inválido es **422**.
- Ninguna credencial en el código, el repositorio, la imagen ni el `.zip`.
- Las seis inconsistencias IN-01…IN-06 de `knowledge-base/10_preguntas_abiertas.md` están **resueltas (2026-11-09)**; no se reabren. RN-10 se aplica a **toda colección**: todo listado acepta `limit`/`offset` (default 20/0), aunque la matriz de la consigna no los muestre.

---

## Árbol de dependencias

```
C-01 proyecto-conexion-lifespan                    Ej. 1 · 8%
  └── C-02 modelos-restricciones-relaciones         Ej. 2 · 22%
        └── C-03 contratos-crud                     Ej. 3 · 12%
              └── C-04 altas-con-relaciones         Ej. 4 · 17%
                    │
                    ├── C-05 datos-iniciales-seed          higiene
                    │     └──────────────────────────────► C-09 (seed en el VPS)
                    │
                    └── C-06 lecturas-sin-n-plus-uno       Ej. 5 · 8%
                          └── C-07 asincronia-sin-bloqueos Ej. 6 · 8%
                                └── C-08 imagen-docker     Ej. 7 · 15%
                                      └── C-09 despliegue-vps  Ej. 8 · 10%
                                            └── C-10 casos-prueba-evidencia  higiene
                                                  └── C-11 readme-entrega   higiene
```

Dependencias cruzadas que el árbol resume con flechas:

- **C-05 → C-09**: el VPS se carga con el seed dentro del contenedor.
- **C-06 → C-10**: la evidencia C-07 sale del conteo fijo de consultas.
- **C-07 → C-10**: la evidencia D-07 sale del aviso en segundo plano.

### Paralelismo por fase

> Cada gate es un punto de sincronización. Los changes de un mismo grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 proyecto-conexion-lifespan              [Agente A]

GATE 1: C-01 ✓
  → C-02 modelos-restricciones-relaciones        [Agente A]

GATE 2: C-02 ✓
  → C-03 contratos-crud                          [Agente A]

GATE 3: C-03 ✓
  → C-04 altas-con-relaciones                    [Agente A]

GATE 4: C-04 ✓                                   ← PRIMER FORK (2 ramas; C-08 solo borrador)
  → C-05 datos-iniciales-seed                    [Agente B]
  → C-06 lecturas-sin-n-plus-uno                 [Agente A]
  → C-08 imagen-docker (borrador)                [Agente C — no cierra hasta C-07 ✓]

GATE 5: C-05 + C-06 ✓
  → C-07 asincronia-sin-bloqueos                 [Agente A]
  → C-10 casos-prueba-evidencia (borrador)       [Agente B — .http C-01…C-08]

GATE 6: C-07 ✓
  → C-08 imagen-docker (build y verificación)    [Agente C]

GATE 7: C-08 + C-05 ✓
  → C-09 despliegue-vps                          [Agente C]

GATE 8: C-09 ✓
  → C-10 casos-prueba-evidencia (cierre)         [Agente B]

GATE 9: C-10 ✓
  → C-11 readme-entrega                          [Agente C]
```

### Camino crítico (10 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-04 → C-06 → C-07 → C-08 → C-09 → C-10 → C-11
```

C-05 corre en paralelo y es prerequisito de C-09, pero no alarga el camino: la rama C-06 → C-07 → C-08 es más larga.

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend núcleo) │ Agente B (Datos y calidad) │ Agente C (Infra y entrega)
─────┼───────────────────────────┼────────────────────────────┼──────────────────────────────
  1  │ C-01 fundación            │ —                          │ —
  2  │ C-02 modelos              │ —                          │ —
  3  │ C-03 CRUD                 │ —                          │ —
  4  │ C-04 altas                │ —                          │ —
  5  │ C-06 N+1                  │ C-05 seed                  │ C-08 Dockerfile (borrador)
  6  │ C-07 asincronía           │ C-10 test/*.http (borrador)│ —
  7  │ —                         │ —                          │ C-08 build + healthy
  8  │ —                         │ —                          │ C-09 despliegue
  9  │ —                         │ C-10 evidencia final       │ —
 10  │ —                         │ —                          │ C-11 README/entrega
```

---

## FASE 0 — Cimientos: proyecto, conexión y modelos · Ejercicios 1 y 2 · 30%

> C-01 y C-02 son secuenciales. C-02 define el esquema que todos los demás changes referencian; no se paraleliza.

### [C-01] `proyecto-conexion-lifespan`
- **Estado**: `[x]` completado
- **Scope**: Proyecto FastAPI con estructura obligatoria, configuración por entorno y ciclo de vida completo.
  - Estructura: `app/main.py`, `app/core/config.py`, `app/core/database.py`, `app/modules/health/router.py` y carpetas `app/modules/<módulo>/` con `__init__.py`; `test/`, `scripts/`, `requirements.txt`, `env.example`, `.gitignore`, `README.md` mínimo.
  - `requirements.txt` con `fastapi[standard]`, `sqlmodel>=0.0.24`, `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.30`, `python-dotenv>=1.0`; nada de Redis, Alembic ni auth.
  - `config.py`: `load_dotenv()`; `DATABASE_URL` obligatoria y sin default (si falta, el arranque falla con mensaje claro); `SQL_ECHO` booleano con default `false`.
  - `database.py`: `create_async_engine(settings.database_url, echo=settings.sql_echo)`, `async_sessionmaker(engine, expire_on_commit=False)` y `get_session()` como generador asíncrono con `async with`.
  - `lifespan` en `main.py`: crea motor y fábrica, los guarda en `app.state.engine` y `app.state.session_factory`; importa explícitamente los `models` de todos los módulos antes de `SQLModel.metadata.create_all`; al apagar ejecuta `await engine.dispose()`.
  - `GET /health/live` → 200 `{"estado": "vivo"}` sin tocar la base; `GET /health/ready` → 200 `{"estado": "listo", "base": "ok"}` ejecutando `SELECT 1`, y 503 `{"estado": "no_listo", "base": "error"}` con mensaje propio si la base no responde (IN-03 resuelto; el `HEALTHCHECK` de C-08 depende del código HTTP, no del cuerpo).
  - `env.example` con la forma de `DATABASE_URL` (`postgresql+asyncpg://usuario:password@host:5432/base`) y `SQL_ECHO=false`, sin valores reales; `.gitignore` con `.env`, `.venv`, `__pycache__/`, `*.pyc`.
  - Tests: `/health/live` sin base; `/health/ready` 200 con base y falla controlada sin base; arranque sin `DATABASE_URL` falla (D-05).
  - No crear tablas de dominio acá: C-02 las agrega y las importa en el mismo `lifespan`.
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 0, US-000
  - `knowledge-base/07_flujos_principales.md` §Flujo 1 (lifespan), §Flujo 6 (healthchecks)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Capa de datos, §Variables de entorno
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/12_devops_y_despliegue.md` §Variables de entorno del contenedor
- **Cierre**: verificado y archivado el 2026-11-09; 38 tests en verde; `/health/live` 200 y `/health/ready` 200/503 verificados contra PostgreSQL real.

---

### [C-02] `modelos-restricciones-relaciones`
- **Estado**: `[x]` completado
- **Scope**: Las nueve tablas del dominio, con restricciones, índices y navegación bidireccional.
  - `editoriales/models.py`: `Editorial` (`__tablename__ = "editorial"`; `id`, `nombre` UNIQUE NOT NULL, `pais` NOT NULL; `libros` con `back_populates`).
  - `generos/models.py`: `Genero` (`__tablename__ = "genero"`; `nombre` UNIQUE NOT NULL; `libros`).
  - `autores/models.py`: `Autor` (`__tablename__ = "autor"`; `nombre`, `nacionalidad`; `autorias`).
  - `libros/models.py`: `Libro` y `LibroAutor` (`__tablename__ = "libro"` y `"libro_autor"`); columnas exactas, `precio Numeric(10,2)`, `stock`, `editorial_id` FK NOT NULL indexada, `genero_id` FK nullable indexada; `LibroAutor` con PK compuesta `(libro_id, autor_id)`, `rol` CHECK de cuatro valores, `orden` CHECK `>= 1`, FKs indexadas y relaciones `libro`/`autor`.
  - `clientes/models.py`: `Cliente` y `PerfilCliente` (`__tablename__ = "cliente"` y `"perfil_cliente"`); `email` UNIQUE; `perfil_cliente.cliente_id` FK UNIQUE NOT NULL indexada; `Cliente.perfil` con `uselist=False` para que devuelva objeto y no lista.
  - `ventas/models.py`: `Venta` y `RenglonVenta` (`__tablename__ = "venta"` y `"renglon_venta"`); `fecha DateTime(timezone=True)` con default UTC, `total Numeric(12,2)` CHECK `>= 0`; `renglon_venta.venta_id` FK `ondelete="CASCADE"` indexada, `libro_id` FK indexada, `cantidad` CHECK `> 0`, `precio_unitario Numeric(10,2)` CHECK `> 0`; `Venta.renglones` con `cascade="all, delete-orphan"`.
  - Constraints con nombre explícito y convención estable (`uq_editorial_nombre`, `ck_libro_precio_positivo`, `fk_libro_editorial_id`, etc.) para que C-03/C-04 mapeen `IntegrityError` por nombre sin filtrar texto de PostgreSQL.
  - Índices explícitos en cada FK y en `libro.titulo` (btree) para RN-11; `libro.isbn` y `cliente.email` ya son UNIQUE.
  - Navegación en los dos extremos con `Relationship(back_populates=...)`: `Editorial.libros`/`Libro.editorial`, `Genero.libros`/`Libro.genero`, `Autor.autorias`/`LibroAutor.autor`, `Libro.autorias`/`LibroAutor.libro`, `Cliente.perfil`/`PerfilCliente.cliente`, `Cliente.ventas`/`Venta.cliente`, `Venta.renglones`/`RenglonVenta.venta`, `Libro.renglones`/`RenglonVenta.libro`.
  - `SQLModel.metadata.create_all` crea las nueve tablas en una base vacía; sin Alembic ni migraciones.
  - Tests: metadata con UNIQUE/CHECK/FK/PK compuesta; `Cliente.perfil` escalar; venta con renglones persistida por composición; importes siempre `Decimal`.
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Entidades, §Índices, §Reglas de mapeo relacional
  - `knowledge-base/05_reglas_de_negocio.md` §RN-01, RN-02, RN-03, RN-09, §Excepciones globales
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01, DD-02, SU-01, SU-02
  - `knowledge-base/08_arquitectura_propuesta.md` §Capa de datos
  - `knowledge-base/07_flujos_principales.md` §Flujo 2 (navegación `libro.autorias[i].autor`)
- **Cierre**: verificado y archivado el 2026-11-09; 75 tests en verde; 20 constraints con nombre (5 UNIQUE + 7 CHECK + 8 FK) verificados en la base real; composición/cascada verificada contra PostgreSQL.

---

## FASE 1 — Contratos y CRUD · Ejercicio 3 · 12%

> C-03 deja el contrato base y los CRUD de referencia. Los schemas de alta anidados se completan en C-04 y el conteo fijo de consultas se cierra en C-06.

### [C-03] `contratos-crud`
- **Estado**: `[x]` completado
- **Scope**: DTO separados de las tablas, códigos HTTP correctos, paginación y CRUD de referencia.
  - `schemas.py` en cada módulo con `Create` (sin `id`), `Update` (todos los campos opcionales) y `Read`; los `Read` serializan `Decimal` como string (`"25000.00"`).
  - Helper `app/core/errors.py` con mapa nombre de constraint → mensaje propio + 409; helper de paginación con `limit=Query(20, ge=1, le=100)` y `offset=Query(0, ge=0)`.
  - Editoriales: `POST /editoriales/` 201/409/422; `GET /editoriales/` paginado 200/422; `GET /editoriales/{id}` 200/404/422; `PATCH /editoriales/{id}` 200/404/409 con `exclude_unset`; `GET /editoriales/{id}/libros` 200/404.
  - Géneros: `POST /generos/` 201/409; `GET /generos/` paginado 200; `GET /generos/{id}/libros` 200/404. No agregar `GET /generos/{id}` ni `PATCH`: no están en la tabla de referencia.
  - Autores: `POST /autores/` 201/422; `GET /autores/{id}` 200/404/422; `PATCH /autores/{id}` 200/404/422; `GET /autores/{id}/libros` 200/404 con `rol` y `orden`.
  - Clientes: `POST /clientes/` 201/409/422; `GET /clientes/{id}` 200/404 con perfil (`joinedload`); `PATCH /clientes/{id}` 200/404/409/422; `POST /clientes/{id}/perfil` 201/404/409; `GET /clientes/{id}/ventas` 200/404.
  - Libros (lectura y edición): `GET /libros/` con `limit`, `offset`, `titulo` y `genero_id` (200/422; editorial y género con `joinedload`; búsqueda `ilike` con parámetro ligado); `GET /libros/{id}` 200/404 con editorial, género y autores; `PATCH /libros/{id}` 200/404/409/422 con `exclude_unset`, solo campos escalares: las autorías **no** se editan por PATCH (IN-01 resuelto; documentarlo en `README.md`).
  - Todos los endpoints que devuelven una colección (`GET /editoriales/`, `/generos/`, `/editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros`, `/libros/` y, en C-06, `/ventas/` y `/clientes/{id}/ventas`) aceptan `limit` y `offset` con los defaults de RN-10 (20/0) y los validan con 422. Que la matriz de la consigna no los liste en un endpoint no lo exime: RN-10 dice "todo listado".
  - `POST /libros/` y `POST /ventas/` no se implementan acá: son C-04. Tampoco hay `DELETE` (SU-05).
  - Errores: `IntegrityError` por UNIQUE/FK → 409 con mensaje propio; recurso inexistente en lectura/PATCH → 404; contrato o query inválidos → 422; nunca `str(exc)`, nombres de constraints ni trazas (RN-12).
  - Tests: C-01 (id no entero → 422), C-02 (ISBN/email repetido → 409), C-03 (segundo perfil → 409), C-08 (`' OR '1'='1` → 200 lista vacía), PATCH parcial y paginación fuera de rango → 422.
- **Dependencias**: C-02
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/11_contratos_api.md` §Matriz de endpoints, §DTO de entrada, §DTO de salida, §Paginación y filtros, §Errores y mensajes
  - `knowledge-base/06_funcionalidades.md` §US-010 a US-014, US-016, US-020 a US-022
  - `knowledge-base/05_reglas_de_negocio.md` §RN-10, RN-11, RN-12
  - `knowledge-base/07_flujos_principales.md` §Flujo 5 (perfil uno a uno)
  - `knowledge-base/10_preguntas_abiertas.md` §IN-01 (PATCH de autores), §IN-03 (cuerpo de `/health/ready`)
- **Cierre**: verificado y archivado el 2026-11-10; 158 tests en verde (75 baseline + 83 nuevos); 20 endpoints de CRUD de referencia verificados contra PostgreSQL real; `Decimal` serializado como string; RN-10 en toda colección; IN-01 (PATCH escalar) documentado.

---

## FASE 2 — Altas con relaciones · Ejercicio 4 · 17%

> C-04 es el change más pesado después de C-02. No dividirlo sin romper la correspondencia 1:1 con el Ejercicio 4.

### [C-04] `altas-con-relaciones`
- **Estado**: `[x]` completado
- **Scope**: Altas de libro y venta con ids de entidades existentes y datos propios de la relación.
  - `LibroCreate` con `isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id` opcional y `autores: list[AutorLibroCreate]` (`autor_id`, `rol`, `orden`); `AutorLibroCreate` valida `rol` ∈ cuatro valores y `orden >= 1`.
  - `libros/service.py`: crear `Libro` con los ids tal como llegan, sin `SELECT` previo de editorial/género/autor; crear un `LibroAutor` por elemento y agregarlo a `libro.autorias`; un solo `commit`.
  - `POST /libros/` → 201 con el detalle releído (editorial, género y autores) usando precarga; ISBN repetido, editorial/género/autor inexistente o autoría duplicada → 409 con mensaje propio mapeado por constraint (RN-01, RI-01, RI-02, RI-05).
  - `VentaCreate` con `cliente_id` y `renglones: list[RenglonCreate]` (`libro_id`, `cantidad > 0`, `min_length=1`); validador que rechaza `libro_id` repetido → 422 (RN-05); no aceptar `precio_unitario`, `total` ni `fecha` en el cuerpo.
  - `ventas/service.py`: cargar los libros involucrados en **una** consulta (`WHERE id IN (...)`); si falta un libro → 409 "El libro indicado no existe"; copiar `precio_unitario = libro.precio` (RN-06); calcular `total = sum(cantidad × precio_unitario)` (RN-07); `fecha = datetime.now(timezone.utc)`, serializada en ISO 8601 UTC con microsegundos y sufijo `Z` (`"2026-10-08T21:14:11.751581Z"`, IN-05 resuelto); agregar los renglones a `venta.renglones` y commitear por composición.
  - `POST /ventas/` → 201 con cliente y renglones (incluido `titulo` y `subtotal` calculado en el DTO); cliente inexistente → 409 (RI-03); libro inexistente → 409 (RI-04); nunca 500 por `IntegrityError`.
  - No hay `PATCH`/`PUT`/`DELETE` de ventas (RN-08, DD-03); los renglones no tienen alta por separado (RN-04).
  - Tests: C-04 (editorial/autor inexistente → 409), C-05 (cliente/libro inexistente → 409), C-06 (venta con dos renglones → 201, precios copiados y total 77000.00 con el seed); verificar con `SQL_ECHO` que no hay `SELECT` de existencia antes del alta y que cambiar el precio del libro después no altera la venta.
- **Dependencias**: C-03
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 2 (alta de libro), §Flujo 3 (registro de venta)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-04 a RN-07, §Reglas de integridad referencial (RI-01 a RI-05)
  - `knowledge-base/11_contratos_api.md` §DTO de entrada, §Ejemplos canónicos
  - `knowledge-base/04_modelo_de_datos.md` §`libro_autor`, §`venta`, §`renglon_venta`
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-03, DD-04, DD-05
- **Cierre**: verificado y archivado el 2026-11-10; 186 tests en verde (158 baseline + 28 nuevos); `POST /libros/` y `POST /ventas/` con autorías y renglones anidados verificados contra PostgreSQL real; precio copiado y total en `Decimal`; fecha ISO 8601 `Z` (IN-05); sin `SELECT` previo de existencia (una consulta `WHERE id IN (...)`).

---

## FASE 3 — Datos iniciales · Higiene (habilita C-06 y D-03)

> El seed se ejecuta después de C-04 porque necesita las nueve tablas y datos de venta/renglón. Es prerequisito de C-09.

### [C-05] `datos-iniciales-seed`
- **Estado**: `[x]` completado
- **Scope**: Comando idempotente que deja la base en un estado inicial conocido.
  - `app/seed.py` (o `scripts/seed.py`; elegir uno y usarlo en README y Dockerfile) ejecutable con `python -m app.seed`: crea el motor desde `DATABASE_URL`, ejecuta `create_all` y abre una sesión.
  - Datos compatibles con los ejemplos: editorial id 1, género id 1, al menos cuatro autores (ids 1 a 4; los ids 3 y 4 se usan como coautores), cuatro libros (id 1 "Rayuela" a 25000.00, id 4 "Respiración artificial" a 27000.00, e ids 2 y 3 a elección), dos clientes (id 2 "Tomás Ríos" / tomas@example.com e id 1 a elección) y, opcional, venta id 2 con dos renglones (Rayuela ×2 + Respiración artificial ×1 = 77000.00).
  - Idempotente: `ON CONFLICT DO NOTHING`, `session.merge` o get-or-create; correrlo dos veces no duplica filas ni pisa datos existentes.
  - Sin credenciales hardcodeadas: toma `DATABASE_URL` del entorno y falla con mensaje claro si falta; no imprime la URL ni la clave.
  - Documentar el comando en `README.md` y dejarlo listo para `docker exec libreria python -m app.seed` (lo usa C-09).
  - Tests: correr el seed dos veces y verificar conteos; `GET /libros/` devuelve los cuatro libros; el caso C-06/D-03 reproduce el total 77000.00.
- **Dependencias**: C-04
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Seed data inicial
  - `knowledge-base/12_devops_y_despliegue.md` §Seed de datos
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-10, SU-06
  - `knowledge-base/06_funcionalidades.md` §US-041
  - `knowledge-base/10_preguntas_abiertas.md` §Preguntas abiertas (datos del seed)
- **Cierre**: verificado y archivado el 2026-11-12; 227 tests en verde; `app/seed.py` (`python -m app.seed`) idempotente con ids deterministas, `ON CONFLICT DO NOTHING` por PK y `setval` de secuencias (alta por API post-seed → id 5); datos del seed: 4 libros (Rayuela 25000.00, Respiración artificial 27000.00), 2 clientes (Tomás Ríos id 2), venta id 2 = 77000.00, sin perfil; `SQL_ECHO` forzado a `false`; sin credenciales en salida; README documenta el comando.

---

## FASE 4 — Lecturas sin N+1 · Ejercicio 5 · 8%

> C-06 toca los mismos servicios que C-04. No paralelizarlo con C-07: ambos modifican `ventas/service.py` y `ventas/router.py`.

### [C-06] `lecturas-sin-n-plus-uno`
- **Estado**: `[x]` completado
- **Scope**: Toda lectura relacional con carga anticipada y número fijo de consultas.
  - `libros/service.py`: `GET /libros/{id}` con `joinedload(Libro.editorial)`, `joinedload(Libro.genero)` y `selectinload(Libro.autorias).joinedload(LibroAutor.autor)`; **un número fijo de consultas** (la referencia son 2: una con los `joinedload` y otra con el `selectinload`), independiente de la cantidad de autores.
  - `ventas/service.py`: `GET /ventas/{id}` con `joinedload(Venta.cliente)` y `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`; **un número fijo de consultas** (referencia: 2), independiente de la cantidad de renglones.
  - `GET /ventas/` y `GET /clientes/{id}/ventas` con la misma precarga (cliente + renglones + libro) o un DTO de resumen, **paginados con `limit`/`offset` (RN-10, 20/0, 422 fuera de rango)**: son listados y RN-10 aplica a toda colección aunque la matriz de la consigna no muestre los parámetros en esas rutas. No disparar consultas por fila.
  - `GET /libros/`, `GET /editoriales/{id}/libros` y `GET /generos/{id}/libros` con `joinedload` de editorial/género; `GET /autores/{id}/libros` con join a `LibroAutor` y precarga de `Libro` (rol y orden en la respuesta).
  - `GET /clientes/{id}` con `joinedload(Cliente.perfil)`; el perfil sigue siendo objeto o `null`, nunca lista.
  - Regla: ninguna lectura usa carga perezosa. Opcional como red de seguridad en tests: `lazy="raise"` en las relaciones para que un acceso perezoso falle en vez de esconderse.
  - Tests: contador de consultas con `event.listen(engine.sync_engine, "before_cursor_execute", ...)`; pedir el detalle con 1 y con 3 autores/renglones y comparar que el número no cambia; guardar la salida de `SQL_ECHO=true` en `evidencia/C-07-consultas-libro.txt` y `evidencia/C-07-consultas-venta.txt`.
  - Refactorizar cualquier lectura de C-03/C-04 que haya quedado con carga perezosa; no cambiar contratos ni códigos HTTP.
- **Dependencias**: C-04
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 4 (detalle sin N+1)
  - `knowledge-base/04_modelo_de_datos.md` §`libro`, §`venta`, §Índices
  - `knowledge-base/05_reglas_de_negocio.md` §RN-G-03
  - `knowledge-base/11_contratos_api.md` §DTO de salida (`LibroDetalleRead`, `VentaRead`)
  - `knowledge-base/10_preguntas_abiertas.md` §IN-04 (cantidad exacta de consultas)
- **Cierre**: verificado y archivado el 2026-11-11; 201 tests en verde; `GET /ventas/` y `GET /ventas/{id}` agregados reutilizando `VentaRead`; número fijo de consultas verificado con contador (libro detalle 2, venta detalle 2, listados 2-3, sin crecimiento entre 1 y 3 relaciones); evidencia `SQL_ECHO` en `evidencia/C-07-consultas-libro.txt` y `evidencia/C-07-consultas-venta.txt`; refactor de autores `selectinload` → `joinedload`; sin cambios de contrato.

---

## FASE 5 — Asincronía sin bloqueos · Ejercicio 6 · 8%

> C-07 espera C-06 para no pisar `ventas/service.py`. No agregar colas, Redis ni hilos.

### [C-07] `asincronia-sin-bloqueos`
- **Estado**: `[x]` completado
- **Scope**: Handlers asíncronos y aviso de comprobante en segundo plano.
  - Auditar todos los handlers: `async def`; sin `time.sleep`, `requests`, `httpx` síncrono ni acceso síncrono a la base.
  - `avisar_comprobante(venta_id, email, total)` en `ventas/service.py` o `ventas/tasks.py`: `await asyncio.sleep(0.5)` y `logger.info(...)` con id de venta y email; no recibe la sesión de la petición (se cierra al responder) ni hace consultas.
  - `POST /ventas/`: después del `commit`, `background_tasks.add_task(avisar_comprobante, ...)`; la respuesta 201 sale antes de que termine el aviso (FastAPI ejecuta la tarea después de enviar la respuesta).
  - Configurar el logger a stdout para que el aviso aparezca en `docker logs libreria` (D-07).
  - Tests: medir que el 201 llega en menos de 0.5 s; verificar el log después de la respuesta; lanzar dos ventas concurrentes con `asyncio.gather` y comprobar que el servidor atiende la segunda mientras corre el primer aviso.
  - No usar `run_in_executor` ni hilos; el alcance es `BackgroundTasks` + `asyncio.sleep` (RN-G-02).
- **Dependencias**: C-06
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 3 (pasos 8 a 11), §Flujo 6
  - `knowledge-base/06_funcionalidades.md` §US-032
  - `knowledge-base/05_reglas_de_negocio.md` §RN-G-02
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados (BackgroundTasks)
  - `knowledge-base/12_devops_y_despliegue.md` §Evidencia (D-07)
- **Cierre**: verificado y archivado el 2026-11-12; 215 tests en verde; `POST /ventas/` agenda `avisar_comprobante` con `BackgroundTasks` + `asyncio.sleep(0.5)` después del `commit` (cuerpo 201 en ~38 ms, log ~516 ms después, dos ventas concurrentes en ~537 ms); tarea sin sesión del request ni SQL; logger a stdout idempotente para `docker logs`; auditoría: 26 rutas async y cero llamadas bloqueantes; sin cambios de contrato.

---

## FASE 6 — Contenedor: la imagen · Ejercicio 7 · 15%

> El Dockerfile se puede escribir en paralelo con C-05/C-06, pero el build y la verificación final esperan C-07.

### [C-08] `imagen-docker`
- **Estado**: `[x]` completado
- **Scope**: Imagen Alpine sin secretos, con usuario no root y healthcheck propio.
  - `Dockerfile` con `FROM python:3.12-alpine`; `WORKDIR /app`; `COPY requirements.txt .`; `RUN pip install --no-cache-dir -r requirements.txt`; `COPY app ./app`; `COPY scripts ./scripts` (o la ruta del seed elegida en C-05); `RUN adduser -D -H -u 1000 appuser`; `USER appuser`; `EXPOSE 8000`.
  - `HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1`; usar `127.0.0.1`, nunca `localhost` (Alpine resuelve IPv6 y uvicorn escucha IPv4).
  - `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
  - `.dockerignore` con `.env`, `.venv`, `.git`, `__pycache__`, `*.pyc`, `.pytest_cache`, `knowledge-base`, `docs`, `evidencia`, `openspec`, `test`; no excluir el directorio del seed.
  - Build local: `docker build -t libreria .`; run con `--env-file .env.docker` (archivo local no versionado) y `-p 8000:8000`; verificar `docker ps` healthy y `docker logs` con el arranque y las tablas creadas.
  - Casos D-01 (imagen base <100 MB), D-02 (build/run/ps/logs), D-05 (sin `DATABASE_URL` el contenedor termina con error), D-06 (`docker exec libreria id` no es root); guardar salidas en `evidencia/`.
  - Iniciar `DEPLOY.md` con los cambios que hicieron falta para que corra en el contenedor (se completa en C-09).
  - Coordinar con C-05 (ruta del seed) y C-07 (logger a stdout para D-07).
- **Dependencias**: C-01, C-07
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_devops_y_despliegue.md` §Imagen Docker, §Ejecución, §Variables de entorno del contenedor, §Verificación del healthcheck
  - `knowledge-base/06_funcionalidades.md` §US-040
  - `knowledge-base/05_reglas_de_negocio.md` §RN-G-04
  - `knowledge-base/08_arquitectura_propuesta.md` §Decisiones de infraestructura
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-07, DD-08, DD-09
- **Cierre**: verificado y archivado el 2026-11-12; 249 tests en verde; Dockerfile Alpine con capas en orden, `appuser` uid 1000, HEALTHCHECK sobre `127.0.0.1:8000/health/ready` y `CMD` en `0.0.0.0:8000`; build real (BUILD_EXIT=0, wheels musllinux), contenedor `healthy`, seed dentro del contenedor y `GET /libros/` con 4 libros; evidencia D-01, D-02, D-05 (exit 3 sin `DATABASE_URL`), D-06 (uid 1000) y D-07 (aviso en logs) capturada con salida real; D-03 y D-04 quedan pendientes de C-09; base `python:3.12-alpine` 74.8 MB (<100 MB); sin secretos en la imagen.

---

## FASE 7 — Despliegue en el VPS · Ejercicio 8 · 10%

> C-09 requiere el seed (C-05) y la imagen verificada (C-08). No hay Compose ni base dentro del contenedor.

### [C-09] `despliegue-vps`
- **Estado**: `[x]` completado
- **Scope**: Puesta en línea en el VPS, carga inicial y documentación de despliegue.
  - Elegir y documentar el camino: build en el VPS o build local + transferencia de la imagen; usar los datos de acceso y la base que provee la cátedra.
  - `docker build -t libreria .` en el servidor; `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo> libreria`; si PostgreSQL corre en el host, agregar `--add-host=host.docker.internal:host-gateway` y usar esa dirección; nunca `localhost` dentro del contenedor.
  - `--env-file` con `DATABASE_URL` (`postgresql+asyncpg://...`) y `SQL_ECHO=false`; el archivo vive en el servidor, fuera del repositorio y de la imagen, y no va al zip.
  - Cargar los datos iniciales dentro del contenedor: `docker exec libreria python -m app.seed` (C-05).
  - Verificar desde afuera: `GET /health/ready` 200; `GET /libros/` 200 con los libros del seed; `POST /ventas/` con el cuerpo del caso C-06 → 201 con precios copiados y total 77000.00 (D-03); guardar comandos y salidas en `evidencia/`.
  - Probar `docker rm -f libreria` + el mismo `docker run` → vuelve healthy y los datos siguen (D-04, porque `create_all` solo crea tablas faltantes); `docker logs libreria` muestra el aviso del comprobante después de la respuesta (D-07).
  - Completar `DEPLOY.md`: URL pública, día y hora, comandos `docker build`/`docker run` completos con el nombre del archivo de variables y sin su contenido, cambios hechos y procedimiento de actualización (build → `docker rm -f` → `docker run`).
  - Dejar el despliegue en línea hasta que se publiquen las notas; si algo no responde, corregir y anotarlo en `DEPLOY.md`.
- **Dependencias**: C-05, C-08
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_devops_y_despliegue.md` §DEPLOY.md, §Actualización, §Evidencia
  - `knowledge-base/07_flujos_principales.md` §Flujo 7 (actualización del despliegue)
  - `knowledge-base/06_funcionalidades.md` §US-041
  - `knowledge-base/10_preguntas_abiertas.md` §Preguntas abiertas (puerto y `DATABASE_URL` del VPS)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-06 (`create_all` sobre base existente)
- **Cierre**: verificado y archivado el 2026-11-12; 299 tests + 3 skipped; desplegado en el VPS 46.202.151.202 (Ubuntu 24.04.4, Docker 29.7.1) con `docker run` standalone en el puerto 8000: contenedor `libreria-zoriontech`, base `libreria-zoriontech-db` (postgres:16-alpine) con volumen propio y red `libreria-zoriontech-net`; build en el servidor (`BUILD_EXIT=0`, 264 MB) y seed dentro del contenedor; URL pública `http://46.202.151.202:8000` con `/health/ready` 200, 4 libros y `POST /ventas/` 201 con total 77000.00; D-03, D-04 y D-07 verificados con salida real; D-01/D-02/D-05/D-06 locales con entorno declarado; el servidor es compartido y el contenedor `libreria` de otro grupo quedó intacto; los scripts exigen nombres propios y rechazan ese contenedor.

---

## FASE 8 — Pruebas, evidencia y entrega · Higiene

> C-10 y C-11 cierran la entrega. No agregan funcionalidades nuevas.

### [C-10] `casos-prueba-evidencia`
- **Estado**: `[x]` cerrado
- **Scope**: Archivos `.http`, evidencia de los casos C y D y pruebas de regresión.
  - `test/health.http`, `editoriales.http`, `generos.http`, `autores.http`, `libros.http`, `clientes.http`, `ventas.http` y `casos-C.http`; cada request con el resultado esperado y el código de caso (C-01…C-08 / D-xx) en un comentario.
  - Cubrir C-01 (id no entero → 422), C-02 (ISBN/email repetido → 409), C-03 (segundo perfil → 409), C-04 (editorial/autor inexistente → 409), C-05 (cliente/libro inexistente → 409), C-06 (venta con dos renglones → 201 con total 77000.00), C-07 (detalle con cantidad fija de consultas), C-08 (`' OR '1'='1` → 200 lista vacía).
  - Ejecutar la suite contra local y contra la URL pública; guardar en `evidencia/` la salida de C-07 y de D-01…D-07 con los comandos usados.
  - Evidencia D: `D-01-docker-images.txt`, `D-02-build-run-ps.txt`, `D-03-endpoints-publicos.txt`, `D-04-restart.txt`, `D-05-sin-database-url.txt`, `D-06-usuario.txt`, `D-07-background.txt`; no inventar casos fuera de la consigna.
  - Tests automáticos mínimos (pytest + httpx) para regresiones: health, 404, 409 por UNIQUE/FK, PATCH parcial, paginación, venta con renglones y conteo fijo de consultas; complementan los `.http`, no los reemplazan.
  - Verificar que ningún error devuelva texto de la base ni trazas (RN-12) y que los importes salgan como string decimal.
- **Dependencias**: C-04, C-06, C-07, C-09
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/11_contratos_api.md` §Casos de prueba mínimos (`.http` en `test/`)
  - `knowledge-base/12_devops_y_despliegue.md` §Evidencia (carpeta `evidencia/`)
  - `knowledge-base/07_flujos_principales.md` §Flujo 4, §Flujo 6
  - `knowledge-base/05_reglas_de_negocio.md` §Matriz regla → caso de prueba
  - `knowledge-base/06_funcionalidades.md` §US-041
- **Cierre**: verificado y archivado el 2026-11-12; 405 tests + 3 skipped; 8 archivos `.http` en `test/` (health, editoriales, generos, autores, libros, clientes, ventas, casos-C) con `# Caso:` y `# Esperado:` por bloque; parser `test/http_runner.py` y replay automático que ejecuta cada request contra la app real y falla si la expectativa no coincide (probado por mutación); cubre C-01…C-08 (C-07 documentado como comando con evidencia); regresiones RN-12 por HTTP, C-01 con cero consultas, paginación en 8 colecciones e importes string decimal; smoke público de solo lectura contra http://46.202.151.202:8000 (health 200, libros 200, C-08 200 `[]`); sin cambios en `app/` ni en la evidencia.

---

### [C-11] `readme-entrega`
- **Estado**: `[x]` cerrado
- **Scope**: README reproducible, revisión de secretos y armado del `.zip`.
  - `README.md` final con nombres y apellidos de los integrantes, requisitos, creación del venv, `pip install -r requirements.txt`, copia de `env.example` a `.env`, arranque con `uvicorn app.main:app --reload`, comando del seed y cómo correr los `.http`.
  - Revisar `env.example`: solo la forma de `DATABASE_URL` y `SQL_ECHO=false`, sin usuario/clave/host reales.
  - Revisar `DEPLOY.md` contra la checklist de C-09: URL, fecha y hora, comandos completos, cambios y actualización.
  - Armar `Parcial_Cap1a4_<NombreDelGrupo>.zip` con una sola carpeta y **exactamente** el contenido que pide la consigna: `app/`, el directorio del seed (`app/seed.py` o `scripts/`), `requirements.txt`, `env.example`, `test/`, `Dockerfile`, `.dockerignore`, `README.md`, `DEPLOY.md` y `evidencia/`. Excluir `.venv`, `__pycache__`, `.env`, archivos temporales, `*.zip`, y también `.git/`, `docs/`, `knowledge-base/`, `openspec/`, `.atl/`, `AGENTS.md` y `CLAUDE.md` (decisión 2026-11-09: el formato de entrega enumera el contenido, el historial de `.git` se revisa y no se exponen notas internas).
  - Generar el `.zip` desde una copia limpia, no desde la raíz con `.git`, y verificar antes de comprimir que no haya `.env` ni credenciales en las carpetas que entran (revisar también archivos sin trackear: `git status` no alcanza).
  - Verificar que no haya credenciales en el repositorio, la imagen ni el zip (RN-G-04); documentar la limitación de `create_all` (DD-06) en README/DEPLOY.
  - Cerrar con el checklist de entrega de `12_devops_y_despliegue.md` y una última corrida de los casos C/D sobre la URL pública.
- **Dependencias**: C-10
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/12_devops_y_despliegue.md` §Checklist de entrega
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/06_funcionalidades.md` §US-041
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance v1.0, §Fuera de alcance
  - `knowledge-base/10_preguntas_abiertas.md` §Preguntas abiertas (¿se incluye `.git`?)
- **Cierre**: verificado y archivado el 2026-11-12; 405 tests + 3 skipped; `README.md` final con grupo ZorionTech e integrantes Lautaro Naranjo y Martin Escudero, requisitos, venv, `.env`, arranque, seed, `.http` y `pytest`; `env.example` solo con la forma de `DATABASE_URL` y `SQL_ECHO=false`, sin la IP del VPS; `DEPLOY.md` revisado contra la checklist (URL, fecha y hora, comandos con el nombre de `/root/libreria-zoriontech.env` sin su contenido, cambios y actualización, sin anexo de EasyPanel); `Parcial_Cap1a4_ZorionTech.zip` (137.6 KB, 111 entradas, con `.gitignore`) armado desde una copia limpia con una sola raíz `Parcial_Cap1a4_ZorionTech/` y el contenido exacto (sin `.env`, `.env.docker`, `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `openspec`, `docs`, `knowledge-base`, `.atl`, `AGENTS.md` ni `CLAUDE.md`); revisión de secretos sin coincidencias (sin credenciales, claves privadas, tokens ni `libreria*.env`); despliegue en línea: `GET http://46.202.151.202:8000/health/ready` → 200 `{"estado": "listo", "base": "ok"}`; auditoría final (96/100) cerrada: `.gitignore` incluido en el paquete (111 entradas; 258 passed + 150 skipped al descomprimir), el test de `git ls-files` se salta fuera del repositorio, comentarios de `app/main.py` y `health/models.py` corregidos sin cambio de comportamiento, `evidencia/C-07-*` regenerada sobre el seed real (4 libros, libro 2 con 2 autores, venta 2 con 2 renglones; 2 SELECT fijos) y `.dockerignore` ampliado con `*.zip`, `.atl`, `.opencode` y `design-system`.

---

### Tabla resumen y primer paso

| ID | Change | Ejercicio / peso | Depende de | Governance |
|---|---|---|---|---|
| C-01 | `proyecto-conexion-lifespan` | 1 · 8% | — | BAJO |
| C-02 | `modelos-restricciones-relaciones` | 2 · **22%** | C-01 | CRITICO |
| C-03 | `contratos-crud` | 3 · 12% | C-02 | MEDIO |
| C-04 | `altas-con-relaciones` | 4 · **17%** | C-03 | ALTO |
| C-05 | `datos-iniciales-seed` | higiene | C-04 | BAJO |
| C-06 | `lecturas-sin-n-plus-uno` | 5 · 8% | C-04 | MEDIO |
| C-07 | `asincronia-sin-bloqueos` | 6 · 8% | C-06 | MEDIO |
| C-08 | `imagen-docker` | 7 · **15%** | C-01, C-07 | ALTO |
| C-09 | `despliegue-vps` | 8 · 10% | C-05, C-08 | ALTO |
| C-10 | `casos-prueba-evidencia` | higiene | C-04, C-06, C-07, C-09 | BAJO |
| C-11 | `readme-entrega` | higiene | C-10 | MEDIO |

**Primer change recomendado**: `C-01` (`proyecto-conexion-lifespan`).

Para arrancar: `/opsx:propose proyecto-conexion-lifespan`.
