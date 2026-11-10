# Design

## Context

Ver `proposal.md` §Why. El repositorio es *greenfield* en lo que respecta a código: no existe `app/`, ni `requirements.txt`, ni pruebas. La knowledge base fija el stack y las reglas; `CHANGES.md` fija el alcance exacto de C-01 y su governance BAJO. Tres restricciones condicionan el diseño:

1. El motor y la fábrica de sesiones **deben** nacer en el `lifespan` y publicarse en `app.state` (US-000, Flujo 1), no al importar el módulo.
2. `create_all` debe correr con **todos** los modelos registrados; C-02 agregará las nueve tablas sin tocar el mecanismo de arranque.
3. `DATABASE_URL` no puede tener default (DD-09) y su ausencia debe fallar el arranque, no una petición posterior.

## Goals / Non-Goals

**Goals:**

- Un esqueleto ejecutable con `uvicorn app.main:app` que arranque, cree el esquema y se apague limpiamente.
- Configuración validada una sola vez por proceso, con errores legibles para el operador.
- Un único punto de creación del motor, reutilizable por C-02 en adelante sin reescribir el `lifespan`.
- Healthchecks con contrato exacto y verificables sin PostgreSQL real en la suite por defecto.

**Non-Goals:**

- Tablas, DTO y endpoints de dominio (C-02…C-04).
- Seed de datos (C-05), `Dockerfile` (C-08) y despliegue (C-09).
- Manejo genérico de errores HTTP de la API, `IntegrityError` → 409 y paginación: se implementan junto con los módulos que los necesitan.
- Migraciones, autenticación, caché y observabilidad avanzada: excluidos por la consigna.

## Decisions

### D-01 — `get_session` resuelve la fábrica desde `app.state`, no desde un global

`get_session(request: Request)` lee `request.app.state.session_factory` y entrega la sesión con `async with`. La fábrica y el motor se crean exclusivamente en el `lifespan`.

- **Por qué**: cumple literalmente "crear en el lifespan y guardar en `app.state`", evita motores huérfanos con `--reload` o al importar el módulo en pruebas, y deja un solo dueño del ciclo de vida.
- **Alternativas descartadas**: (a) motor y fábrica a nivel de módulo en `database.py` — más simple, pero contradice el requisito y crea conexiones al importar; (b) un contenedor de dependencias propio — estructura extra que la consigna no pide.
- **Consecuencia**: los tests inyectan sesiones con `app.dependency_overrides[get_session]`, el seam estándar de FastAPI.

### D-02 — Configuración con una clase plana y `get_settings()`, sin `pydantic-settings`

`config.py` llama a `load_dotenv()` una vez, define una clase `Settings` inmutable (dataclass) y una función `get_settings()` que construye y valida la instancia. `DATABASE_URL` ausente o vacía lanza una excepción propia de configuración con un mensaje en español que nombra la variable.

- **Por qué**: `pydantic-settings` no está en el `requirements.txt` aprobado y agregarla rompe el alcance. La validación en una función (no en constantes de import) permite probar el fallo de D-05 con `monkeypatch` sin trucos de recarga de módulos.
- **Alternativas descartadas**: constantes de módulo (`DATABASE_URL = os.environ["DATABASE_URL"]`) — falla en import con `KeyError` poco claro y es difícil de testear; `lru_cache` sobre `get_settings()` — contamina pruebas que cambian el entorno. Se documenta que `get_settings()` es pura y que el `lifespan` la invoca una sola vez.

### D-03 — Validar la forma de `DATABASE_URL`

Además de exigirla, `get_settings()` verifica que empiece con `postgresql+asyncpg://`. Si no, falla con un mensaje que explica el driver esperado.

- **Por qué**: una URL `postgresql://...` haría que SQLAlchemy busque un driver sincrónico y falle de forma confusa; la validación temprana evita además introducir por accidente un acceso bloqueante (RN-G-02).
- **Trade-off**: un entorno con otro nombre de driver queda rechazado; se documenta en `README.md` y `env.example`. Es coherente con el stack fijado por la cátedra.

### D-04 — Parseo estricto de `SQL_ECHO`

Valores aceptados como verdaderos: `1`, `true`, `yes`, `si`, `sí`, `on`; falsos: `0`, `false`, `no`, `off` y vacío; comparación sin distinguir mayúsculas ni espacios. Cualquier otro valor produce un error de configuración al arrancar.

- **Por qué**: `bool("false")` es `True` en Python; un parseo ingenuo activaría el log de SQL en producción. Fallar ante un valor desconocido es preferible a interpretarlo en silencio.
- **Alternativa descartada**: cualquier valor no vacío = verdadero — acepta `"false"` como activado.

### D-05 — `models.py` vacíos y bloque de importación explícito en `main.py`

C-01 crea `app/modules/<módulo>/models.py` vacío (solo docstring) para los seis dominios y un bloque de imports explícitos en `main.py` antes de `create_all`, con `# noqa: F401`. C-02 rellena esos archivos; el bloque no cambia.

- **Por qué**: el alcance pide "importar explícitamente los models de todos los módulos antes de `create_all`". Sin archivos que importar, ese requisito quedaría como un comentario y C-02 podría olvidar registrar un módulo (esquema incompleto, RN-G-05). Los archivos vacíos no crean tablas.
- **Alternativa descartada**: un `app/modules/registry.py` que centralice los imports — agrega un paquete fuera del árbol obligatorio sin beneficio en este tamaño.
- **Nota**: el bloque debe ejecutarse antes de `SQLModel.metadata.create_all`; se ubica en el tope de `main.py` y se documenta con un comentario que apunta a C-02.

### D-06 — `/health/ready` devuelve `JSONResponse` y nunca `HTTPException`

El handler atrapa cualquier excepción de la verificación, la registra con el logger del servidor y devuelve `JSONResponse(status_code=503, content={"estado": "no_listo", "base": "error"})`.

- **Por qué**: `HTTPException(503, detail=...)` envuelve el cuerpo en `{"detail": ...}` y rompe el contrato exacto de IN-03. Además, dejar que una excepción de conexión escape produciría un 500, violando "falla controlada".
- **Trade-off**: se captura `Exception` de forma deliberadamente amplia en este endpoint; se justifica porque su única responsabilidad es traducir cualquier fallo de base a 503 sin filtrar detalles (RN-12).
- **Detalle**: `/health/live` no declara la dependencia de sesión, por lo que no puede tocar `app.state` ni la base.

### D-07 — Fábrica de aplicación `create_app()` con instancia a nivel de módulo

`main.py` expone `create_app() -> FastAPI` (que arma routers y lifespan) y `app = create_app()` para `uvicorn app.main:app`.

- **Por qué**: permite construir aplicaciones aisladas en pruebas y mantener explícita la composición; el `lifespan` cierra sobre funciones de `database.py` (`build_engine`, `build_session_factory`) que se pueden sustituir con `monkeypatch` para probar arranque y apagado sin PostgreSQL.
- **Alternativa descartada**: instancia única global sin fábrica — impide probar el `lifespan` con un motor falso.

### D-08 — Estrategia de pruebas

- `httpx.AsyncClient(transport=ASGITransport(app=app))`; el transporte ASGI **no** ejecuta el `lifespan`, lo que hace que el test de `/health/live` demuestre por construcción que no se abre base.
- `/health/ready` 200 y 503 se prueban con `app.dependency_overrides[get_session]`: una sesión falsa que devuelve `1` y otra que lanza `OperationalError`. Se afirman código y cuerpo exactos, y que el cuerpo del 503 no contiene texto de la excepción.
- El fallo por `DATABASE_URL` ausente se prueba sobre `get_settings()` y sobre la entrada del `lifespan` con `monkeypatch.delenv`.
- Se agrega un test de integración marcado, opt-in por presencia de `DATABASE_URL`, que arranca la app real y consulta `/health/ready`; se salta si no hay base para no romper la suite local.
- `pytest-asyncio` en modo estricto con `asyncio_mode = auto` o decoradores explícitos, según lo que resuelva la implementación al fijar la versión; se prefiere `asyncio_mode = auto` para reducir ruido.

### D-09 — Dependencias de prueba separadas del runtime

`requirements.txt` mantiene solo las cinco dependencias del stack aprobado. Las herramientas de prueba (`pytest`, `pytest-asyncio`, `httpx`) viven en `requirements-dev.txt`, y la configuración de pytest (`asyncio_mode = auto`) se declara en un `pyproject.toml` mínimo.

- **Por qué**: la spec exige que `requirements.txt` declare únicamente el stack oficial; mezclar herramientas de test en la imagen de producción contradice la regla de imagen mínima de C-08.
- **Alternativa descartada**: poner todo en `requirements.txt` — infla la imagen y rompe la verificación de la spec.

### D-10 — Registro de routers en la app, prefijo en el `APIRouter`

`health/router.py` declara `APIRouter(prefix="/health", tags=["Salud"])`; `main.py` solo hace `include_router(health_router)`.

- **Por qué**: convención del stack (`fastapi-templates`) y consistencia con los módulos que vendrán, que ya traerán su prefijo.

## Risks / Trade-offs

| Riesgo | Mitigación |
|---|---|
| La conexión a una base inalcanzable puede colgarse mucho más que un healthcheck si no se fija timeout | La firma exigida es `create_async_engine(url, echo=...)`; el `HEALTHCHECK` de C-08 acota la espera con `--timeout=5s`. Se deja documentado que agregar `connect_args={"timeout": N}` es una mejora localizada si aparece el problema. |
| `create_all` no altera tablas existentes (RN-G-05) | Se documenta en `README.md`; cualquier cambio de esquema posterior exige recrear la base o un `ALTER` manual. Es una limitación aceptada por la consigna (DD-06). |
| `get_session` dependiente de `app.state` falla si se invoca un handler sin `lifespan` | Es el comportamiento deseado (no hay motor); las pruebas inyectan la dependencia. |
| Los imports vacíos de `models.py` pueden parecer código muerto | Comentario en `main.py` que explica su función y referencia C-02; `# noqa: F401` evita ruido de linters. |
| Tests por defecto no ejercitan asyncpg ni PostgreSQL real | Test de integración opt-in cuando `DATABASE_URL` está presente; C-09/C-10 verifican contra el VPS. |
| Credenciales con caracteres especiales rompen la URL | `README.md` y `env.example` indican codificar la contraseña (percent-encoding) y nunca versionar `.env`. |
| Diferencia entre `+00:00` y `Z` en fechas | No aplica en C-01 (no hay fechas); se resuelve en C-03/C-04 según IN-05. |
