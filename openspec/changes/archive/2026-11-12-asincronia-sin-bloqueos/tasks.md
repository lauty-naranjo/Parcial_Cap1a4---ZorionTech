# Tasks

> TDD estricto en el apply: cada grupo arranca con el test que falla (RED), sigue con la implementación mínima (GREEN) y refactoriza. Los tests usan `httpx.AsyncClient(transport=ASGITransport(app=app))` y los fixtures de `test/conftest.py` (`cliente_bd`, `sesion_bd`). Regla de la change: `BackgroundTasks` + `asyncio.sleep`, sin hilos ni `run_in_executor`; la tarea de fondo recibe solo escalares y nunca la sesión del request.

## 1. Tests en RED del aviso y del no-bloqueo

- [x] 1.1 Crear `test/test_asincronia.py` con el test unitario de `avisar_comprobante(venta_id, email, total)` en RED: mide con `time.perf_counter()` que tarda al menos 0.5 s y verifica con `caplog.at_level(logging.INFO, logger="app.modules.ventas.tasks")` un registro con el id de venta y el email. Verificación: `pytest test/test_asincronia.py -k avisar` falla porque el módulo no existe.
- [x] 1.2 Agregar al mismo archivo el test de latencia y orden en RED: envuelve la app con un observador ASGI que registra `perf_counter()` y `time.time()` en el mensaje final `http.response.body`, hace `POST /ventas/` con datos de `sesion_bd`, y aserta `body_ts - inicio < 0.5` y que el `LogRecord.created` del aviso es mayor o igual a `body_wall_ts`. Verificación: falla porque hoy no se agenda ningún aviso ni hay logger a stdout.
- [x] 1.3 Agregar el test de concurrencia en RED: dos `POST /ventas/` con `asyncio.gather`, aserta 201 en ambas, ids distintos y tiempo total `< 0.9` s (los dos `asyncio.sleep(0.5)` se solapan). Verificación: el test falla o no demuestra solapamiento hasta implementar el aviso.
- [x] 1.4 Agregar el test de regresión de asincronía en VERDE: recorre las rutas de `create_app()` y aserta `inspect.iscoroutinefunction(ruta.endpoint)` para cada una; agrega una búsqueda sobre `app/` que falla si aparece `time.sleep(`, `requests.`, `httpx.` síncrono o `run_in_executor`. Verificación: pasa hoy y falla si se introduce un handler síncrono o una llamada bloqueante.

## 2. Tarea de fondo y logging a stdout

- [x] 2.1 Crear `app/modules/ventas/tasks.py` con `async def avisar_comprobante(venta_id: int, email: str, total: Decimal) -> None`: `await asyncio.sleep(0.5)`, `logger.info(...)` con id, email y total como string decimal (`f"{total:.2f}"`), y `try/except` con `logger.exception` para no relanzar. Sin sesión, sin consultas, sin `run_in_executor`. Verificación: el test 1.1 pasa y `grep -n "session\|execute\|run_in_executor" app/modules/ventas/tasks.py` no devuelve nada.
- [x] 2.2 Crear `app/core/logging.py` con `configurar_logging()` idempotente: `StreamHandler(sys.stdout)`, formatter con asctime/nivel/logger/mensaje, nivel `INFO` en el root, sin `propagate=False`. Verificación: test nuevo que llama dos veces a la función (y crea dos apps) y aserta un único `StreamHandler` de stdout en el root, sin duplicados.
- [x] 2.3 Invocar `configurar_logging()` al inicio de `create_app()` en `app/main.py`, sin tocar el `lifespan` ni el registro de routers. Verificación: el test de logging de 2.2 pasa y `docker logs` queda preparado para D-07 (la evidencia real se captura en C-08/C-09).
- [x] 2.4 Confirmar que ningún logger registra `DATABASE_URL` ni credenciales: revisar las llamadas de log de `tasks.py`/`logging.py` y dejar solo id de venta, email y total. Verificación: el mensaje del test 1.1 no contiene `postgresql://` ni la clave de la URL.

## 3. Agendado del aviso en `POST /ventas/`

- [x] 3.1 Modificar `app/modules/ventas/router.py::crear` para recibir `background_tasks: BackgroundTasks`, llamar a `service.crear(session, datos)` y, **después** de que retorne (el `commit` ocurre dentro del servicio), hacer `background_tasks.add_task(avisar_comprobante, venta.id, venta.cliente.email, venta.total)` antes del `return`. `service.crear` conserva su firma y su `VentaRead`. Verificación: los tests 1.1, 1.2 y 1.3 pasan; `pytest test/test_ventas_alta.py` sigue en verde.
- [x] 3.2 Verificar por código que si el servicio lanza (409 de cliente/libro inexistente) no se agenda la tarea y la respuesta no espera el `sleep`: agregar al archivo de tests el caso 409 sin línea de log de aviso. Verificación: el nuevo caso pasa junto con `test_ventas_alta.py`.
- [x] 3.3 Actualizar el docstring de `ventas/router.py::crear` para indicar que la tarea se agenda tras el `commit` y que la sesión no se pasa. Verificación: `grep -n "BackgroundTasks" app/modules/ventas/router.py` muestra el agendado posterior al servicio.

## 4. Integración y validación de la change

- [x] 4.1 Test de integración (`@pytest.mark.integration`) que con la base real y datos del seed registra una venta, verifica 201 < 0.5 s (observador ASGI), el log posterior con id y email, y dos ventas concurrentes sin bloqueo. Verificación: pasa con `DATABASE_URL` definida y se salta sin ella.
- [x] 4.2 Correr la suite completa (`pytest -q`) y confirmar que los 201 tests previos siguen verdes más los nuevos. Verificación: sin fallos y sin warnings de corrutinas no esperadas.
- [x] 4.3 Ejecutar `openspec validate --strict asincronia-sin-bloqueos`. Verificación: sin errores ni warnings; los encabezados y `SHALL`/`MUST` en inglés y el resto en español.
- [x] 4.4 Registrar en `tasks.md` el resultado de la auditoría de asincronía (todos los handlers `async def`, sin llamadas bloqueantes) y dejar anotado el procedimiento de evidencia D-07 para C-08/C-09 (`docker logs libreria` con el aviso después de la respuesta). Verificación: la nota existe y coincide con el test 1.4.

## Nota de apply (C-07)

- **Auditoría de asincronía (2026-11-12)**: `test_todos_los_handlers_son_corrutinas` aplana los 7 routers incluidos en `create_app()` (26 rutas, sin las internas de docs) y confirma `inspect.iscoroutinefunction` en todos los endpoints. `test_app_no_contiene_llamadas_bloqueantes` recorre `app/**/*.py` y no encuentra `time.sleep(`, `requests.`, `httpx.` ni `run_in_executor`; las únicas funciones síncronas son helpers puros sin I/O.
- **Medición observada** (observador ASGI + `caplog`, PostgreSQL local): una venta devuelve el cuerpo del `201` a los **38.2 ms**; el aviso se registra **515.8 ms después del cuerpo** (retorno del cliente ASGI 548.3 ms, porque espera la tarea de fondo). Dos ventas concurrentes con `asyncio.gather`: total **536.7 ms** y cuerpos a 13.3 y 55.5 ms, es decir los dos `asyncio.sleep(0.5)` se solapan.
- **Evidencia D-07 para C-08/C-09**: con el contenedor corriendo (`docker run --name libreria ...`), registrar una venta con `POST /ventas/` y capturar `docker logs libreria > evidencia/D-07-background.txt`; la línea `Aviso de comprobante enviado: venta=<id> email=<email> total=<total>` debe aparecer después de la línea de la respuesta. El logger escribe a stdout vía `app/core/logging.py` (`flush` por mensaje).

## Workflow follow-up

- Verificar formalmente la change con `openspec-verify-change` contra proposal, design y specs.
- Archivar la change (`openspec-archive-change`) y sincronizar las deltas a `openspec/specs/api-contracts/spec.md` y `openspec/specs/app-foundation/spec.md`.
- Marcar C-07 en `[x]` en `CHANGES.md` con su línea de cierre y dejar la evidencia D-07 para C-08/C-09.
