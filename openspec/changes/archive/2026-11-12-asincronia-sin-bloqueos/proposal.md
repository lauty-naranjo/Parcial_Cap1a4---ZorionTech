# Proposal

## Why

El Ejercicio 6 (8% de la nota) evalúa que la API **no bloquee el event loop** y que el aviso de comprobante de una venta corra **después** de responder: el `201` de `POST /ventas/` debe salir antes de que el aviso termine y el servidor debe seguir atendiendo otras peticiones mientras el aviso duerme (RN-G-02, US-032, D-07). Hoy el registro de venta no agenda ninguna tarea de fondo, no hay logger configurado (por lo tanto el aviso no puede verse en `docker logs` para la evidencia D-07) y no existe ninguna prueba que demuestre no-bloqueo ni el orden respuesta → log.

## What Changes

- Se auditan **todos** los handlers y servicios: se confirma que son `async def`, que no usan `time.sleep`, `requests`, `httpx` síncrono ni acceso síncrono a la base (RN-G-02). El resultado de la auditoría queda registrado; si apareciera una llamada bloqueante, se corrige **sin cambiar contratos ni códigos HTTP**.
- Se agrega `avisar_comprobante(venta_id, email, total)` en un módulo nuevo `app/modules/ventas/tasks.py`: hace `await asyncio.sleep(0.5)` y escribe un `logger.info(...)` con el id de venta y el email. La función **no recibe la sesión de la petición** (se cierra al responder) y **no consulta la base**; recibe solo datos escalares ya serializables.
- `POST /ventas/` agenda el aviso con `background_tasks.add_task(...)` **después del `commit`** y devuelve el `201` antes de que el aviso termine. No se usa `run_in_executor`, hilos, colas ni Redis (RN-G-02, fuera de alcance de CHANGES).
- Se configura el logging a **stdout** (módulo `app/core/logging.py`, invocado desde `create_app()`) para que el aviso aparezca en `docker logs libreria` (D-07), sin registrar credenciales ni la `DATABASE_URL`.
- Se agregan tests que fijan el comportamiento: el `201` llega en menos de 0.5 s, el log aparece **después** de la respuesta, y dos ventas concurrentes con `asyncio.gather` completan en ~0.5 s (no ~1 s) demostrando que el aviso no bloquea al servidor.

**Fuera de alcance**: no se toca el esquema (`data-model` no cambia), no se agregan endpoints, no se cambia el cuerpo ni los códigos HTTP existentes, no se agregan colas, workers, Redis ni hilos, y no se modifica la lógica de negocio de la venta (precio copiado, total, fecha).

## Capabilities

### New Capabilities

<!-- Ninguna: el aviso en segundo plano extiende el contrato de `POST /ventas/` ya cubierto por `api-contracts`, y la garantía de no-bloqueo y el logging a stdout son comportamiento transversal de `app-foundation`. -->

### Modified Capabilities

- `api-contracts`: se agrega el requisito del aviso de comprobante en segundo plano (`POST /ventas/` responde 201 antes de que el aviso termine y el aviso deja una línea de log con id de venta y email).
- `app-foundation`: se agregan los requisitos transversales de ejecución asíncrona sin bloqueos (todos los handlers `async def`, sin llamadas bloqueantes) y de registro a stdout para la evidencia D-07.

## Impact

- **Código**: `app/modules/ventas/router.py` (inyecta `BackgroundTasks` y agenda el aviso después del servicio), `app/modules/ventas/tasks.py` (nuevo, `avisar_comprobante`), `app/core/logging.py` (nuevo, logger a stdout) y `app/main.py` (una llamada a `configurar_logging()` en `create_app()`). `app/modules/ventas/service.py` **no cambia de firma**: sigue devolviendo `VentaRead`.
- **API**: `POST /ventas/` mantiene el mismo contrato de entrada y salida y el mismo `201`; cambia solo el *timing* (la respuesta ya no espera el aviso) y aparece una línea de log posterior.
- **Base de datos**: sin cambios de esquema ni de consultas; la tarea de fondo no accede a la base.
- **Dependencias**: ninguna nueva (solo `asyncio` y `logging` de la biblioteca estándar).
- **Tests**: `test/test_asincronia.py` (latencia <0.5 s medida en el mensaje ASGI de respuesta, orden respuesta → log y concurrencia con `asyncio.gather`), más un test unitario de `avisar_comprobante` y del orden de tareas.
- **Evidencia**: la línea de log de D-07 se captura en C-08/C-09 con `docker logs libreria`; C-07 deja el comportamiento y la prueba que lo respalda.
- **Riesgo principal**: con `httpx.ASGITransport` el cliente retorna recién cuando la app terminó —incluida la tarea de fondo—, así que medir la latencia desde el `await cliente.post(...)` daría ~0.5 s siempre. Por eso la medición se hace en el mensaje `http.response.body` final con un observador ASGI en el test (ver `design.md`).
