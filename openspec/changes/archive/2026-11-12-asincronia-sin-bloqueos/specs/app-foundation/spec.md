# Spec Delta

## ADDED Requirements

### Requirement: Ejecución asíncrona sin bloqueos

Todos los handlers de la API SHALL ser `async def` y MUST NOT ejecutar llamadas bloqueantes como `time.sleep`, clientes HTTP síncronos, acceso síncrono a la base ni ejecución en hilos o executors.

#### Scenario: Petición atendida mientras corre una tarea de fondo

- **WHEN** dos peticiones se envían de forma concurrente y una de ellas deja una tarea de fondo en curso
- **THEN** ambas reciben su respuesta y la segunda no espera a que termine la tarea de la primera

#### Scenario: Auditoría de handlers sin bloqueos

- **WHEN** se revisan los handlers y servicios de la aplicación
- **THEN** todos los handlers son `async def` y no hay `time.sleep`, `requests`, `httpx` síncrono, `run_in_executor` ni acceso síncrono a la base

### Requirement: Registro de la aplicación a stdout

La aplicación SHALL configurar su logging para escribir a la salida estándar, de modo que los mensajes de sus módulos aparezcan en la salida del proceso contenedor. El logging MUST NOT registrar credenciales ni la `DATABASE_URL`.

#### Scenario: Aviso visible en la salida del contenedor

- **WHEN** la aplicación arranca y procesa una venta con aviso de comprobante
- **THEN** el mensaje del aviso aparece en la salida estándar del proceso, disponible para `docker logs`

#### Scenario: Configuración de logging sin duplicados

- **WHEN** se crea más de una instancia de la aplicación en el mismo proceso
- **THEN** el logging queda configurado una sola vez, sin handlers duplicados ni mensajes repetidos
