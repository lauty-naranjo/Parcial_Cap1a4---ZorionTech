# Preguntas Abiertas

## Inconsistencias / ambigüedades detectadas

> Las seis quedaron **resueltas el 2026-11-09**. No se reabren sin acuerdo explícito del grupo; si la cátedra responde distinto, se actualiza este archivo y el change afectado.

### IN-01 — `PATCH /libros/{id}` y la lista de autores — RESUELTA
**La consigna dice**: el alta de libro recibe `autores` con `rol` y `orden`; el `PATCH` devuelve "Detalle del libro".
**No dice**: si `LibroUpdate` puede modificar autorías.
**Impacto**: si la corrección espera edición de autores por PATCH y no existe, se pierde puntaje del Ejercicio 3.
**Decisión (2026-11-09, grupo)**: `LibroUpdate` acepta **solo campos escalares** (`isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id`). Las autorías se cargan únicamente en `POST /libros/` y **no** se editan por `PATCH`. Se documenta en `README.md` y en el proposal de C-03.

### IN-02 — Código de respuesta para `genero_id` inexistente — RESUELTA
**La consigna dice**: C-04 exige 409 para "editorial o autor inexistente"; C-05 para "libro o cliente inexistente".
**No dice**: qué código corresponde a un `genero_id` inexistente.
**Impacto**: criterio de "Altas con relaciones".
**Decisión (2026-11-09, grupo)**: **409**, por coherencia con la traducción de `IntegrityError` de FK (RI-05). `genero_id` se trata igual que `editorial_id` y `autor_id`.

### IN-03 — Forma exacta de `/health/ready` — RESUELTA
**La consigna dice**: "Estado de la base" como respuesta; el ejemplo de `/health/live` es `{"estado": "vivo"}`.
**No dice**: el cuerpo exacto de `ready`.
**Impacto**: bajo; el `HEALTHCHECK` solo mira el código HTTP.
**Decisión (2026-11-09, grupo)**: 200 `{"estado": "listo", "base": "ok"}` cuando `SELECT 1` responde; 503 `{"estado": "no_listo", "base": "error"}` con mensaje propio cuando falla. El `HEALTHCHECK` de C-08 depende del código HTTP, no del cuerpo.

### IN-04 — Cantidad exacta de consultas esperada en C-07 — RESUELTA
**La consigna dice**: "cantidad fija de consultas, la misma con uno o varios autores o renglones".
**No dice**: el número exacto.
**Impacto**: la evidencia debe mostrar el conteo; el corrector compara entre ejecuciones.
**Decisión (2026-11-09, grupo)**: el detalle de libro y el de venta se resuelven en un **número fijo** de consultas, independiente de la cantidad de autores o renglones. La implementación de referencia usa **2**: una consulta con `joinedload` de las relaciones a uno y una con `selectinload` de la colección (con el `joinedload` del extremo dentro de la misma). El número real se registra en `evidencia/C-07-consultas-libro.txt` y `evidencia/C-07-consultas-venta.txt` junto con el conteo con 1 y con 3 relaciones. Lo que se evalúa es que **no crezca**, no un número mágico.

### IN-05 — Formato de `fecha` — RESUELTA
**La consigna dice**: `"fecha": "2026-10-08T21:14:11.751581Z"` (UTC con `Z`).
**No dice**: si se exige microsegundos y sufijo `Z` exactos.
**Impacto**: diferencias de serialización.
**Decisión (2026-11-09, grupo)**: `DateTime(timezone=True)` en UTC, serializado como ISO 8601 con microsegundos y sufijo `Z`. Si Pydantic serializa `+00:00`, se normaliza en el DTO de salida y se cubre con un test de contrato.

### IN-06 — `env.example` con `SQL_ECHO` — RESUELTA
**La consigna dice**: el `--env-file` incluye `DATABASE_URL` y "la variable que activa el diagnóstico de consultas (SQL_ECHO en el ejemplo del env.example) en false".
**No dice**: si `SQL_ECHO` es obligatoria o tiene default.
**Impacto**: el arranque no debe fallar si falta.
**Decisión (2026-11-09, grupo)**: `SQL_ECHO` es **opcional** con default `false` en `config.py`; se incluye igual en `env.example` con `false`.

## Preguntas abiertas (priorizadas)

Solo quedan las que dependen de datos que provee la cátedra al momento del despliegue:

| Prioridad | Pregunta | Bloquea | Decisor | Estado |
|---|---|---|---|---|
| Alta | ¿Cuál es el puerto asignado por la cátedra para publicar el contenedor? | D-02, D-03, DEPLOY.md | Cátedra | Abierta — se necesita en C-09 |
| Alta | ¿Cuál es el `DATABASE_URL` real del VPS y qué usuario/base provee la cátedra? | Despliegue | Cátedra | Abierta — se necesita en C-09 |

### Preguntas cerradas en esta revisión

| Pregunta | Decisión | Dónde se aplica |
|---|---|---|
| ¿`PATCH /libros/{id}` edita autorías? | No: solo campos escalares | IN-01 · C-03 |
| ¿Endpoints `DELETE`? | No: fuera de alcance, solo los listados de la matriz | Reglas transversales |
| ¿Se pagina todo listado aunque la matriz no muestre `limit`/`offset`? | Sí: RN-10 dice "todo listado"; se aceptan `limit`/`offset` con default 20/0 en toda colección | C-03, C-06 |
| Cuerpo de `/health/ready` | `{"estado": "listo", "base": "ok"}` / 503 `{"estado": "no_listo", "base": "error"}` | IN-03 · C-01 |
| Datos del seed | Sí: coinciden con los ejemplos (Rayuela 25000, id 4 a 27000, cliente id 2, venta 77000.00) | C-05 |
| Aviso de comprobante | `logger.info` con id de venta, email y total, a stdout | C-07 |
| Usuario no root en la imagen | `appuser` (uid 1000) | C-08 |
| ¿`total` es columna o se recalcula? | Columna `Numeric(12,2)` con CHECK `>= 0`, como exige la tabla de la consigna | C-02 |
| ¿Se incluye `.git` en el `.zip`? | No: se excluye, junto con `docs/`, `knowledge-base/`, `openspec/`, `.atl/`, `AGENTS.md` y `CLAUDE.md` | C-11 |

## [DISCOVERY] Campos inferidos con baja confianza

Ninguno bloqueante. Los seis campos de `kb.discovery` se infirieron con alta confianza desde la consigna:

- `system_type`: API REST (FastAPI).
- `domain`: retail / librería (catálogo y ventas).
- `scale`: single-tenant, uso interno de una librería de barrio; despliegue público en VPS para corrección.
- `stack`: Python 3.12 + FastAPI + SQLModel + SQLAlchemy async + asyncpg + PostgreSQL 16 + Docker.
- `needs_infra`: true (PostgreSQL y Docker/VPS).
