# Proposal

## Why

El repositorio tiene la fundación documental completa (knowledge base, `CHANGES.md`, `AGENTS.md`) pero **no existe todavía ninguna aplicación**: no hay `app/`, `requirements.txt` ni punto de entrada. Sin un esqueleto FastAPI que arranque, cree su motor asincrónico en el `lifespan` y exponga healthchecks, ningún otro change del roadmap (C-02 en adelante) puede implementarse ni verificarse.

Este change materializa US-000 y las decisiones cerradas `DD-06` (`create_all` en el lifespan, sin migraciones), `DD-09` (`DATABASE_URL` obligatoria y sin default) e `IN-03`/`IN-06` (`/health/ready` y `SQL_ECHO`).

## What Changes

- Se crea la estructura obligatoria del proyecto: `app/main.py`, `app/core/config.py`, `app/core/database.py`, `app/modules/health/router.py`, los paquetes `app/modules/<módulo>/` con `__init__.py`, más `test/`, `scripts/`, `README.md` mínimo y `env.example`.
- Se agrega `requirements.txt` con exactamente el stack de la cátedra: `fastapi[standard]`, `sqlmodel>=0.0.24`, `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.30`, `python-dotenv>=1.0`. Sin Redis, sin Alembic, sin auth, sin `pydantic-settings`.
- Se implementa la configuración por entorno: `load_dotenv()`, `DATABASE_URL` obligatoria sin default (su ausencia hace **fallar el arranque** con mensaje claro, D-05) y `SQL_ECHO` booleano con default `false` (IN-06). `env.example` documenta la forma de ambas variables sin valores reales.
- Se implementa la capa de datos asincrónica: creación del `AsyncEngine` con `create_async_engine(..., echo=...)`, `async_sessionmaker(expire_on_commit=False)` y `get_session()` como generador asíncrono con `async with`.
- Se implementa el `lifespan` completo: crea motor y fábrica, los publica en `app.state.engine` y `app.state.session_factory`, importa explícitamente los `models` de todos los módulos antes de `SQLModel.metadata.create_all`, y en el apagado ejecuta `await engine.dispose()`.
- Se exponen los healthchecks: `GET /health/live` → 200 `{"estado": "vivo"}` sin tocar la base; `GET /health/ready` → 200 `{"estado": "listo", "base": "ok"}` ejecutando `SELECT 1`, y 503 `{"estado": "no_listo", "base": "error"}` con cuerpo propio y sin filtrar detalles internos cuando la base no responde (IN-03, RN-12).
- Se agrega la batería de pruebas mínima con `pytest` + `pytest-asyncio` + `httpx`: live sin base, ready 200/503 con sesión controlada y arranque sin `DATABASE_URL` fallando.
- `.gitignore` ya cubre `.env`, `.venv`, `__pycache__/` y `*.pyc`; se verifica y se completa solo si falta alguno.

**Fuera de alcance**: tablas de dominio y sus restricciones (C-02), endpoints de catálogo/clientes/ventas (C-03 en adelante), seed (C-05), `Dockerfile` y `.dockerignore` (C-08), despliegue (C-09), migraciones y autenticación (excluidas por la consigna).

## Capabilities

### New Capabilities

- `app-foundation`: arranque y ciclo de vida de la aplicación — configuración exclusiva por entorno con fallo temprano, estructura de paquetes obligatoria, motor y fábrica de sesiones asincrónicos creados en el `lifespan`, sesión por petición, creación del esquema con `SQLModel.metadata.create_all` y liberación del motor al apagar.
- `health-checks`: contrato de los endpoints de salud — liveness que no consulta la base y readiness que verifica la conexión con `SELECT 1` y responde 200/503 con un cuerpo estable y sin información interna.

### Modified Capabilities

Ninguna: `openspec/specs/` está vacío y este es el primer change del proyecto.

## Impact

- **Código nuevo**: `app/__init__.py`, `app/main.py`, `app/core/{__init__,config,database}.py`, `app/modules/health/{__init__,router}.py`, `app/modules/<módulo>/{__init__,models}.py` para `editoriales`, `generos`, `autores`, `libros`, `clientes` y `ventas` (paquetes vacíos, sin tablas), `test/`, `scripts/`, `requirements.txt`, `env.example`, `README.md`.
- **API**: se introducen `GET /health/live` y `GET /health/ready`; no se agrega ningún endpoint de dominio (la matriz de `11_contratos_api.md` se respeta).
- **Dependencias**: solo las cinco del stack oficial. No se incorporan librerías de migraciones, caché ni autenticación.
- **Configuración**: nuevas variables de entorno `DATABASE_URL` (obligatoria) y `SQL_ECHO` (opcional, default `false`). Requiere un PostgreSQL 16 accesible para que el arranque complete `create_all`.
- **Changes posteriores**: C-02 rellena los `models.py` ya importados por el `lifespan` y agrega las tablas; C-08 consume `/health/ready` desde el `HEALTHCHECK`; C-10 produce la evidencia D-05.
