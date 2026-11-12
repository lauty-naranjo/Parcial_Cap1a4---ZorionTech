# Design

## Context

Ver `proposal.md` §Why para la motivación. Estado actual que condiciona el diseño:

- `app/main.py` define `create_app()` y el `lifespan` (motor y `session_factory` en `app.state`, `create_all`, `dispose`) y registra 7 routers. **No hay configuración de logging**: el proceso solo emite lo que uvicorn configura para sí mismo.
- `app/modules/ventas/router.py` expone `POST /ventas/` (`crear`, 201), `GET /ventas/` y `GET /ventas/{id}`; `crear` delega en `service.crear(session, datos)`.
- `app/modules/ventas/service.py::crear` carga los libros en una consulta, copia precios, calcula el `total` con `Decimal`, hace `commit` y **relee** la venta con `obtener()`; devuelve `VentaRead` con `cliente` (`ClienteResumenRead` con `email`) y `renglones` ya precargados.
- `app/core/database.py::get_session` entrega una sesión por petición y la cierra al salir del generador, antes de correr las `BackgroundTasks`.
- Auditoría de C-07 sobre `app/`: **todos los handlers son `async def`**; las únicas funciones síncronas son helpers puros (mapeos DTO, lectores de configuración, `utc_now`) sin I/O. No hay `time.sleep`, `requests`, `httpx` síncrono, `run_in_executor` ni acceso síncrono a la base. **No hace falta refactor de asincronía**; la auditoría se documenta y se cubre con un test de regresión.
- `test/conftest.py` provee `aplicacion` (`create_app()`), `cliente_bd` (ASGITransport + sesión real) y `sesion_bd`; el transporte ASGI **no corre el lifespan**.

## Goals / Non-Goals

**Goals:**

- Agendar el aviso de comprobante después del `commit` sin acoplar el servicio de dominio a FastAPI.
- Mantener intactos el contrato y los códigos HTTP de `POST /ventas/`.
- Dejar el mensaje del aviso en stdout para que `docker logs libreria` lo muestre (D-07).
- Probar de forma determinista: 201 < 0.5 s, log posterior a la respuesta y concurrencia sin bloqueo.

**Non-Goals:**

- No se agrega cola, worker, Redis, hilo ni `run_in_executor` (RN-G-02 y fuera de alcance de `CHANGES.md`).
- No se persiste ni se reintenta el aviso: es un efecto observable por log, no una entidad del dominio.
- No se toca el esquema ni se agregan/mueven endpoints.
- No se reconfiguran los loggers de uvicorn ni el formato de access log.

## Decisions

### 1. `avisar_comprobante` vive en `app/modules/ventas/tasks.py`

Se crea el módulo `app/modules/ventas/tasks.py` con la corrutina `avisar_comprobante(venta_id: int, email: str, total: Decimal) -> None`, que hace `await asyncio.sleep(0.5)` y luego `logger.info(...)` con el id de venta, el email y el total como string decimal. Atrapa excepciones con `logger.exception` para que un fallo del aviso no se propague al servidor después de enviada la respuesta.

**Alternativa considerada**: ponerla en `ventas/service.py`. Descartada porque `service.py` concentra lógica de dominio transaccional; la tarea de fondo es un efecto secundario sin base de datos y mezclarla obliga a importar `asyncio`/`logging` en el servicio y a mantener la tentación de pasarle la sesión.

**Alternativa considerada**: definirla en línea en el router. Descartada por testeo (importar la función permite un test unitario directo) y por reutilización futura.

### 2. El email sale del `VentaRead` ya precargado; `service.crear` no cambia de firma

`service.crear` devuelve `VentaRead`, cuyo `cliente.email` viene de la precarga `joinedload(Venta.cliente)` que ya existe. El router hace:

```python
venta = await service.crear(session, datos)
background_tasks.add_task(avisar_comprobante, venta.id, venta.cliente.email, venta.total)
return venta
```

Como `service.crear` hace el `commit` internamente y luego relee, cuando el router agenda la tarea el `commit` ya ocurrió y la respuesta está armada. Si el `commit` falla (409), el servicio lanza y **no se agenda ninguna tarea**. No se pasa la sesión ni el ORM.

**Alternativa considerada**: pasar `BackgroundTasks` a `service.crear` para agendar dentro del servicio. Descartada: acopla el dominio a `fastapi` y hace que el servicio dependa de un objeto de la capa HTTP; además complica los tests de servicio existentes (201 tests en verde) sin ganar nada.

**Alternativa considerada**: consultar el cliente dentro de la tarea para obtener el email. Descartada explícitamente por la KB: la sesión de la petición ya está cerrada y la tarea no debe abrir otra.

### 3. Logging a stdout en `app/core/logging.py`, invocado desde `create_app()`

`configurar_logging()` crea un `StreamHandler(sys.stdout)` con formatter `%(asctime)s %(levelname)s %(name)s %(message)s`, lo asocia al logger raíz con nivel `INFO` y es **idempotente** (marca el handler o verifica un atributo del root para no duplicarlo si se crean varias apps en el mismo proceso). Se llama una vez al comienzo de `create_app()`.

Los módulos usan `logging.getLogger(__name__)` (p. ej. `app.modules.ventas.tasks`) y **no** fijan `propagate=False`, de modo que: (a) en producción el mensaje sube al handler de stdout, y (b) `caplog` lo captura en los tests. `StreamHandler` hace `flush()` tras cada emisión, así que el mensaje no queda en un buffer de bloque y aparece en `docker logs`.

**Alternativa considerada**: configurar el logging en el `lifespan`. Descartada porque el `ASGITransport` de los tests **no ejecuta el lifespan**, y los tests de esta change necesitan el logger real activo; además `create_app()` también corre en producción, así que un solo punto cubre ambos.

**Alternativa considerada**: `logging.basicConfig(stream=sys.stdout)`. Descartada porque es difícil de hacer idempotente de forma explícita y de testear; un handler propio con marca es más predecible.

**Alternativa considerada**: `dictConfig` completo. Descartada por sobredimensionada: no se reconfiguran uvicorn ni el access log en esta change.

### 4. Medición de latencia y orden en los tests: observador ASGI, no el retorno de `httpx`

Con `httpx.ASGITransport` el `await cliente.post(...)` retorna **después** de que la app termina, incluidas las `BackgroundTasks`; medir ahí daría siempre ≥ 0.5 s y no probaría nada. Por eso el test monta un middleware ASGI mínimo que:

- registra `time.perf_counter()` al recibir el mensaje `http.response.start` y el mensaje `http.response.body` final (`more_body` falso) — el instante en que la respuesta se considera enviada;
- registra `time.time()` en ese mismo instante para compararlo con `LogRecord.created` (epoch) del registro capturado con `caplog`.

Aserciones: (a) `body_ts - inicio < 0.5`; (b) `record.created >= body_wall_ts` (el log es posterior a la respuesta); (c) el mensaje contiene el id y el email.

**Alternativa considerada**: levantar un uvicorn real en un puerto efímero y medir con `httpx` HTTP. Descartada para el test de regresión: agrega arranque de red, puertos y flakiness; queda como verificación manual en C-08/C-09 con `docker logs` (D-07).

### 5. Concurrencia con `asyncio.gather`

Dos `POST /ventas/` concurrentes sobre el mismo `cliente_bd`, midiendo el tiempo total: si el aviso duerme con `asyncio.sleep`, ambos `sleep` se solapan y el total ronda 0.5 s; si algo bloqueara el loop (p. ej. `time.sleep`), el total sería ~1.0 s. Se aserta `total < 0.9` y que ambas respuestas son 201 con ids distintos. El orden entre líneas de log se valida además por intersección de los dos registros, sin exigir un orden entre ventas.

### 6. Auditoría de asincronía como test de regresión

Un test recorre los routers registrados en `create_app()` y verifica que cada `endpoint` sea una función de corrutina (`inspect.iscoroutinefunction`). Complementa la auditoría manual (que hoy no encuentra bloqueantes) y evita que un handler nuevo se escriba síncrono.

## Risks / Trade-offs

- **Una excepción en la tarea de fondo se propaga al servidor después de la respuesta** → mitigación: `avisar_comprobante` envuelve su cuerpo en `try/except` y registra con `logger.exception`, sin relanzar.
- **Handlers de logging duplicados al crear varias apps en un proceso (tests)** → mitigación: `configurar_logging()` idempotente con marca en el handler/root y test que crea dos apps y verifica un único handler de stdout.
- **`caplog` no captura si algún módulo pone `propagate=False`** → mitigación: la convención es `getLogger(__name__)` con propagación por defecto; el test de orden falla si no captura.
- **Umbral de 0.5 s en CI lento** → mitigación: el handler hace 2-3 consultas locales; el umbral coincide con la duración del `sleep` y deja margen amplio. No se mide el retorno del cliente ASGI (ver Decisión 4).
- **El aviso no se reintenta si falla** → aceptado: la consigna pide un efecto observable por log (D-07), no entrega garantizada; agregar reintentos o colas está fuera de alcance (capítulos 7 y 8).
- **El log incluye el email del cliente** → aceptado por la KB (dato de contacto del aviso); se prohíbe registrar `DATABASE_URL` u otras credenciales (RN-G-04).

## Migration Plan

Cambio aditivo y sin migración de datos ni de esquema. Se despliega con el flujo normal de C-08/C-09 (`docker build` + `docker run`). Rollback: revertir el commit; las ventas ya registradas no dependen del aviso. La evidencia D-07 se captura en C-08/C-09 con `docker logs libreria` y el procedimiento queda descrito en `DEPLOY.md`.

## Open Questions

Ninguna que cambie specs, enfoque o desglose de tareas. La única ambigüedad de la consigna —dónde vive `avisar_comprobante`— quedó resuelta por `CHANGES.md` C-07 ("`ventas/service.py` o `ventas/tasks.py`") y se elige `tasks.py` por la separación descrita en la Decisión 1.
