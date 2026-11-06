# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — `libro_autor` como entidad de asociación, no `link_model`
**Decisión**: modelar la tabla intermedia con una clase `LibroAutor` propia y PK compuesta `(libro_id, autor_id)`.
**Contexto**: la relación muchos a muchos entre libro y autor lleva `rol` y `orden`.
**Alternativas consideradas**: `link_model` de SQLAlchemy (o `secondary` en `Relationship`).
**Justificación**: `rol` y `orden` no son atributos del libro ni del autor; un `link_model` los escondería y no permitiría navegar `libro.autorias[i].autor`.
**Trade-offs**: más código y una capa extra de DTOs anidados.

### DD-02 — FK de uno a uno en `perfil_cliente`
**Decisión**: `perfil_cliente.cliente_id` con `UNIQUE`.
**Contexto**: "un cliente tiene como máximo un perfil".
**Alternativas consideradas**: FK `cliente.perfil_id` (permitiría que dos clientes compartan perfil) o tabla sin UNIQUE.
**Justificación**: el perfil depende funcionalmente del cliente; el UNIQUE garantiza la cardinalidad en la base (RN-09) y habilita `perfil` nulo.
**Trade-offs**: el perfil no puede existir sin cliente (correcto para el dominio).

### DD-03 — Venta inmutable, sin `PATCH`
**Decisión**: no exponer `PATCH`/`PUT` de ventas.
**Contexto**: RN-08, las ventas registran un hecho.
**Justificación**: evita reescribir historia contable y simplifica la consistencia de `total`.
**Trade-offs**: corregir una venta exige registrar otra operación (no previsto en el alcance).

### DD-04 — Precio copiado y total calculado en el servidor
**Decisión**: `precio_unitario` se copia de `libro.precio` y `total` se calcula sumando; ninguno viaja en el DTO de entrada.
**Contexto**: RN-06 y RN-07.
**Justificación**: el cliente no puede alterar importes; el precio histórico queda congelado.
**Trade-offs**: si el precio del libro cambia, la venta histórica no se actualiza (es lo deseado).

### DD-05 — Sin consultas previas de existencia
**Decisión**: en las altas se escribe y se traduce `IntegrityError` a 409.
**Contexto**: la consigna prohíbe explícitamente el `if` que consulta si un id existe (Ejercicio 4) y exige que la unicidad la garantice la base.
**Justificación**: una sola operación, sin condición de carrera entre el `SELECT` y el `INSERT`.
**Trade-offs**: el mensaje de error debe mapearse por constraint para no filtrar texto de PostgreSQL.

### DD-06 — `create_all` en el lifespan, sin migraciones
**Decisión**: crear el esquema al arrancar.
**Contexto**: la consigna excluye migraciones.
**Justificación**: base vacía del VPS lista al primer arranque.
**Trade-offs**: los cambios de modelo no se aplican a tablas existentes; se documenta en `DEPLOY.md`/`README.md`.

### DD-07 — Imagen `python:3.12-alpine` sin compilador
**Decisión**: base Alpine, dependencias instaladas desde `requirements.txt` con `--no-cache-dir`, sin paquetes de build.
**Contexto**: límite de 100 MB para la imagen base y reducción de superficie de ataque.
**Justificación**: la cátedra verificó que `asyncpg`, `pydantic-core` y el resto del stack se instalan sin compilar en musl.
**Trade-offs**: si se agregara una dependencia con extensión C sin wheel musl, habría que instalar `build-base` (hoy no hace falta).

### DD-08 — `HEALTHCHECK` contra `127.0.0.1`
**Decisión**: usar `wget -qO- http://127.0.0.1:8000/health/ready`.
**Contexto**: en Alpine no hay `curl`; `localhost` resuelve primero a `::1` y uvicorn escucha IPv4.
**Justificación**: evita falsos `unhealthy`.
**Trade-offs**: ninguno relevante.

### DD-09 — Configuración exclusivamente por entorno
**Decisión**: `DATABASE_URL` obligatoria, sin valor por defecto.
**Contexto**: D-05 exige que el contenedor falle sin `DATABASE_URL`; RN-G-04 prohíbe secretos en la imagen.
**Justificación**: un default silencioso llevaría a conectar a la base equivocada.
**Trade-offs**: el arranque falla ruidosamente si falta la variable (es lo pedido).

### DD-10 — Seed como módulo ejecutable
**Decisión**: script de datos iniciales invocable con `python -m app.seed` (o equivalente) y reutilizable vía `docker exec libreria …`.
**Contexto**: la consigna exige un comando que deje la base en estado conocido y su ejecución en el VPS.
**Justificación**: mismo camino en local y en producción, sin depender de archivos SQL externos.
**Trade-offs**: debe ser idempotente para no duplicar datos en reruns (ver `10_preguntas_abiertas.md`).

## Supuestos inferidos

### SU-01 — Claves primarias enteras autoincrementales
**Supuesto**: todas las PK `id` son `Integer` autoincrementales.
**Origen**: los ejemplos de la consigna usan ids 1, 2, 3, 4 y la tabla no especifica tipo.
**Riesgo si es falso**: bajo; los casos usan ids concretos del seed.
**Cómo validar**: revisar el enunciado del capítulo 4 o consultar a la cátedra.

### SU-02 — Valores de `rol` en minúsculas y en español
**Supuesto**: `rol` ∈ {`autor`, `coautor`, `traductor`, `ilustrador`}, tal como aparecen en la consigna y en el ejemplo `"rol": "coautor"`.
**Origen**: tabla de `libro_autor` y ejemplo de `POST /libros/`.
**Riesgo si es falso**: 422/409 en altas válidas.
**Cómo validar**: el CHECK debe aceptar exactamente esos literales.

### SU-03 — Los DTO de salida serializan `Decimal` como string
**Supuesto**: `precio`, `total`, `precio_unitario` y `subtotal` salen como `"25000.00"` (string), no como número.
**Origen**: la respuesta esperada de la consigna los muestra entre comillas.
**Riesgo si es falso**: diferencia de contrato en la corrección.
**Cómo validar**: comparar con el JSON de ejemplo del enunciado (página 13).

### SU-04 — `GET /libros/` no incluye autores; el detalle sí
**Supuesto**: el listado devuelve "Libros con editorial y género"; los autores aparecen en el detalle.
**Origen**: tabla de endpoints, columna "Respuesta".
**Riesgo si es falso**: N+1 innecesario en listados.
**Cómo validar**: criterio de corrección de "Lecturas sin N+1".

### SU-05 — Los endpoints DELETE no son obligatorios
**Supuesto**: no se exige borrado de recursos; la tabla de referencia no los lista.
**Origen**: "Endpoints de referencia".
**Riesgo si es falso**: falta funcionalidad.
**Cómo validar**: confirmar con la cátedra si se espera DELETE.

### SU-06 — El seed carga datos compatibles con los ejemplos
**Supuesto**: el seed incluye "Rayuela" (25000.00, id 1), "Respiración artificial" (27000.00, id 4), editorial/género id 1, autores id 3 y 4, cliente id 2 "Tomás Ríos".
**Origen**: ejemplos de `POST /ventas/` y `POST /libros/`.
**Riesgo si es falso**: los casos D-03 no reproducen el total 77000.00.
**Cómo validar**: ejecutar C-06/D-03 y comparar con el JSON esperado.

### SU-07 — `genero_id` nulo se envía como `null` u omitido
**Supuesto**: `LibroCreate.genero_id` es opcional; ambos casos son válidos.
**Origen**: "genero_id (nulo permitido)".
**Riesgo si es falso**: 422 en altas sin género.
**Cómo validar**: probar alta sin `genero_id`.

### SU-08 — `PATCH /libros/{id}` no reemplaza autorías
**Supuesto**: `LibroUpdate` actualiza campos escalares; la lista de autores se gestiona solo en el alta.
**Origen**: la consigna no define un endpoint de autorías.
**Riesgo si es falso**: se esperaría poder editar autores.
**Cómo validar**: consultar alcance de PATCH en la cátedra.
