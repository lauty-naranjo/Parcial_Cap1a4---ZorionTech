# Tasks

## 1. Esqueleto del proyecto y dependencias

- [x] 1.1 Crear la estructura de paquetes: `app/__init__.py`, `app/core/__init__.py`, `app/main.py` (vacío por ahora), `app/modules/__init__.py` y, por cada dominio (`health`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`), `app/modules/<módulo>/__init__.py` más un `models.py` con solo un docstring. Crear también `test/` y `scripts/` con un archivo de resguardo. Verificación: `python -c "import app, app.core, app.modules, app.modules.health"` funciona y `Get-ChildItem app/modules -Directory` lista los siete módulos con su `__init__.py`.
- [x] 1.2 Crear `requirements.txt` con `fastapi[standard]`, `sqlmodel>=0.0.24`, `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.30`, `python-dotenv>=1.0`, y `requirements-dev.txt` con `pytest`, `pytest-asyncio` y `httpx`. Verificación: `pip install -r requirements.txt -r requirements-dev.txt` termina sin error y `python -c "import fastapi, sqlmodel, sqlalchemy, asyncpg, dotenv, pytest, httpx"` importa todo.
- [x] 1.3 Crear un `pyproject.toml` mínimo con `[tool.pytest.ini_options]` (por ejemplo `asyncio_mode = "auto"` y `testpaths = ["test"]`). Verificación: `pytest --collect-only` detecta el rootdir y no falla por configuración inexistente.
- [x] 1.4 Revisar `.gitignore` y completarlo si falta alguno de `.env`, `.venv`, `__pycache__/` o `*.pyc`. Verificación: `git check-ignore -v .env .venv/lib/x __pycache__/modulo.pyc` devuelve una regla para cada ruta.

## 2. Configuración por entorno (TDD)

- [x] 2.1 Escribir `test/test_config.py` con casos que fallen: `get_settings()` sin `DATABASE_URL` lanza una excepción de configuración cuyo mensaje menciona `DATABASE_URL`; `SQL_ECHO` ausente resuelve `False`; `SQL_ECHO=true` resuelve `True`; un valor de `SQL_ECHO` desconocido falla; una `DATABASE_URL` que no empieza con `postgresql+asyncpg://` falla. Verificación: `pytest test/test_config.py` falla en rojo por la razón esperada (módulo inexistente o atributo faltante), no por errores de sintaxis.
- [x] 2.2 Implementar `app/core/config.py`: `load_dotenv()`, clase `Settings` inmutable, `get_settings()` con validación de obligatoriedad, forma de la URL y parseo estricto de `SQL_ECHO`, y una excepción de configuración con mensaje legible. Verificación: `pytest test/test_config.py` pasa en verde y ningún mensaje de error incluye el valor de `DATABASE_URL`.
- [x] 2.3 Crear `env.example` con `DATABASE_URL=postgresql+asyncpg://usuario:password@host:5432/base` y `SQL_ECHO=false`, y documentar en `README.md` cómo copiarlo a `.env` y que la contraseña debe ir codificada si tiene caracteres especiales. Verificación: `env.example` no contiene credenciales reales ni hosts de producción y `get_settings()` acepta sus valores con un `.env` de prueba.

## 3. Capa de datos y sesión por petición (TDD)

- [x] 3.1 Escribir `test/test_database.py` con casos que fallen: `build_engine(settings)` devuelve un motor asincrónico con el `echo` pedido; `build_session_factory(engine)` produce una fábrica con `expire_on_commit=False`; `get_session` entrega una sesión obtenida de `app.state.session_factory` y la cierra al salir del generador. Verificación: `pytest test/test_database.py` falla en rojo por ausencia de las funciones esperadas.
- [x] 3.2 Implementar `app/core/database.py` con `build_engine(settings)` usando `create_async_engine(settings.database_url, echo=settings.sql_echo)`, `build_session_factory(engine)` usando `async_sessionmaker(engine, expire_on_commit=False)` y `get_session(request)` como generador asíncrono con `async with` sobre la fábrica de `app.state`. Verificación: `pytest test/test_database.py` pasa en verde sin necesitar un PostgreSQL real.
- [x] 3.3 Verificar que no hay acceso bloqueante ni motor global: una prueba `grep` sobre `app/core` no encuentra `time.sleep`, `requests`, `sessionmaker(` sincrónico ni `create_engine(` sincrónico. Verificación: el comando de búsqueda no devuelve coincidencias.

## 4. Lifespan y fábrica de aplicación (TDD)

- [x] 4.1 Escribir `test/test_lifespan.py` con casos que fallen: entrar al `lifespan` sin `DATABASE_URL` lanza la excepción de configuración; con `build_engine` y `build_session_factory` sustituidos por dobles, el arranque deja `app.state.engine` y `app.state.session_factory` poblados; al salir del contexto se invoca `dispose()` del motor; `create_all` se ejecuta contra una conexión del motor. Verificación: `pytest test/test_lifespan.py` falla en rojo por la ausencia de `create_app`/`lifespan`.
- [x] 4.2 Implementar `create_app()` y el `lifespan` en `app/main.py`: imports explícitos de todos los `models` (con `# noqa: F401` y comentario que referencia C-02), creación de motor y fábrica, publicación en `app.state`, `SQLModel.metadata.create_all` mediante `async with engine.begin()` + `run_sync`, `yield`, y `await engine.dispose()` en el apagado; exponer `app = create_app()`. Verificación: `pytest test/test_lifespan.py` pasa en verde y `python -c "import app.main"` no crea conexiones al importar.
- [x] 4.3 Confirmar que el `lifespan` no altera tablas existentes ni ejecuta migraciones: revisar que el único mecanismo de esquema es `SQLModel.metadata.create_all` y que no se agregaron dependencias de migración. Verificación: `grep -R "alembic\|create_engine(" app` no devuelve coincidencias relevantes.

## 5. Healthchecks (TDD)

- [x] 5.1 Escribir `test/conftest.py` con un cliente `httpx.AsyncClient(transport=ASGITransport(app=...))` y helpers para sustituir `get_session` con una sesión que responde `1` y otra que lanza `OperationalError`. Escribir `test/test_health.py` con casos que fallen: `/health/live` responde 200 `{"estado": "vivo"}` sin que el `lifespan` haya corrido; `/health/ready` responde 200 `{"estado": "listo", "base": "ok"}` con la sesión buena; con la sesión que falla responde 503 `{"estado": "no_listo", "base": "error"}` y el cuerpo no contiene el texto de la excepción. Verificación: `pytest test/test_health.py` falla en rojo por rutas inexistentes (404), no por errores de importación.
- [x] 5.2 Implementar `app/modules/health/router.py` con un `APIRouter(prefix="/health", tags=["Salud"])`: `/live` sin dependencia de sesión y `/ready` con `SELECT 1`, devolviendo `JSONResponse` con el cuerpo exacto y 503 ante cualquier fallo de base, registrando la causa solo en el log. Registrarlo con `include_router` en `create_app()`. Verificación: `pytest test/test_health.py` pasa en verde y la suite completa `pytest` queda en verde.
- [x] 5.3 Documentar en `README.md` los comandos de instalación, arranque (`uvicorn app.main:app --reload`), variables de entorno y la tabla de endpoints de salud con sus códigos y cuerpos. Verificación: se ejecuta cada comando documentado desde un entorno limpio y `/health/live` responde 200 mientras `/health/ready` responde 200 con base y 503 sin base.

## 6. Integración y verificación de la entrega

- [x] 6.1 Ejecutar la suite completa con `pytest -q` y confirmar que todos los tests pasan y que los tests de integración opt-in se saltan cuando no hay `DATABASE_URL`. Verificación: salida en verde, sin errores ni avisos de configuración de pytest.
- [x] 6.2 Reproducir D-05: arrancar `uvicorn app.main:app` en un entorno sin `DATABASE_URL` y confirmar que el proceso termina con error y un mensaje claro que menciona `DATABASE_URL`, sin trazas internas ni credenciales. Verificación: salida del comando capturada para la futura evidencia D-05.
- [x] 6.3 Con un PostgreSQL accesible, arrancar la aplicación con un `.env` real y comprobar `GET /health/live` → 200 y `GET /health/ready` → 200; luego cortar el acceso a la base y comprobar `GET /health/ready` → 503 con el cuerpo exacto. Verificación: 200/503 observados contra PostgreSQL 18 local (proxy TCP cortado en caliente); la corrida contra PostgreSQL 16 del VPS queda para C-09/C-10.
- [x] 6.4 Revisar el diff completo contra el alcance de C-01: no hay tablas de dominio, ni endpoints fuera de `/health/*`, ni dependencias fuera del stack, ni `float` para dinero, ni credenciales versionadas. Verificación: `git diff --stat` solo toca los archivos listados en el proposal y `git grep -n "redis\|alembic\|float("` no devuelve coincidencias en `app/`.

## Workflow follow-up

- Ejecutar `openspec verify` contra los artefactos y la implementación antes de archivar.
- Archivar el change con `openspec archive` y marcar `[C-01]` como completado en `CHANGES.md`.
