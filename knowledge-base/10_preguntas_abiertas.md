# Preguntas Abiertas

## Inconsistencias / ambigüedades detectadas

### IN-01 — `PATCH /libros/{id}` y la lista de autores
**La consigna dice**: el alta de libro recibe `autores` con `rol` y `orden`; el `PATCH` devuelve "Detalle del libro".
**No dice**: si `LibroUpdate` puede modificar autorías.
**Impacto**: si la corrección espera edición de autores por PATCH y no existe, se pierde puntaje del Ejercicio 3.
**Resolución propuesta**: limitar `LibroUpdate` a campos escalares (`isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id`) y documentarlo en `README.md`; si se quiere cubrir, aceptar `autores` opcional que reemplace la colección.

### IN-02 — Código de respuesta para `genero_id` inexistente
**La consigna dice**: C-04 exige 409 para "editorial o autor inexistente"; C-05 para "libro o cliente inexistente".
**No dice**: qué código corresponde a un `genero_id` inexistente.
**Impacto**: criterio de "Altas con relaciones".
**Resolución propuesta**: 409, por coherencia con la traducción de `IntegrityError` de FK (RI-05).

### IN-03 — Forma exacta de `/health/ready`
**La consigna dice**: "Estado de la base" como respuesta; el ejemplo de `/health/live` es `{"estado": "vivo"}`.
**No dice**: el cuerpo exacto de `ready`.
**Impacto**: bajo; el `HEALTHCHECK` solo mira el código HTTP.
**Resolución propuesta**: `{"estado": "listo", "base": "ok"}` o `{"base": "ok"}` — decidir uno y mantenerlo.

### IN-04 — Cantidad exacta de consultas esperada en C-07
**La consigna dice**: "cantidad fija de consultas, la misma con uno o varios autores o renglones".
**No dice**: el número exacto.
**Impacto**: la evidencia debe mostrar el conteo; el corrector compara entre ejecuciones.
**Resolución propuesta**: registrar en `evidencia/` el mismo número con 1 y con 3 autores/renglones (p. ej. 3 consultas para libro, 3 para venta) y explicar el desglose.

### IN-05 — Formato de `fecha`
**La consigna dice**: `"fecha": "2026-10-08T21:14:11.751581Z"` (UTC con `Z`).
**No dice**: si se exige microsegundos y sufijo `Z` exactos.
**Impacto**: diferencias de serialización.
**Resolución propuesta**: `DateTime(timezone=True)` en UTC y serialización ISO 8601 con `Z`.

### IN-06 — `env.example` con `SQL_ECHO`
**La consigna dice**: el `--env-file` incluye `DATABASE_URL` y "la variable que activa el diagnóstico de consultas (SQL_ECHO en el ejemplo del env.example) en false".
**No dice**: si `SQL_ECHO` es obligatoria o tiene default.
**Impacto**: el arranque no debe fallar si falta.
**Resolución propuesta**: `SQL_ECHO=false` por defecto en `config.py`; incluirla igual en `env.example`.

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|
| Alta | ¿El `PATCH /libros/{id}` debe permitir editar autorías (rol/orden)? | Ejercicio 3 | Cátedra |
| Alta | ¿Cuál es el puerto asignado por la cátedra para publicar el contenedor? | D-02, D-03, DEPLOY.md | Cátedra |
| Alta | ¿Cuál es el `DATABASE_URL` real del VPS y qué usuario/base provee la cátedra? | Despliegue | Cátedra |
| Alta | ¿Se incluye `.git` en el `.zip`? (si sí, el historial se revisa y no debe tener secretos) | Entrega | Grupo |
| Media | ¿Los datos del seed deben coincidir exactamente con los ejemplos (Rayuela 25000, id 4 27000, cliente id 2)? | C-06, D-03 | Grupo |
| Media | ¿Se esperan endpoints DELETE? | Alcance | Cátedra |
| Media | ¿`GET /editoriales/` y `GET /generos/` exigen paginación aunque la tabla no la muestre? | RN-10 | Cátedra |
| Media | ¿Qué cuerpo exacto se espera en `/health/ready`? | D-02 | Cátedra |
| Baja | ¿El aviso de comprobante debe incluir datos concretos (id de venta, email) en el log? | D-07 | Grupo |
| Baja | ¿Se exige un nombre de usuario no root específico en la imagen? | D-06 | Cátedra |
| Baja | ¿El total se guarda como columna o se recalcula? (la tabla `venta` lo exige como columna) | Modelo | Cátedra |

## [DISCOVERY] Campos inferidos con baja confianza

Ninguno bloqueante. Los seis campos de `kb.discovery` se infirieron con alta confianza desde la consigna:

- `system_type`: API REST (FastAPI).
- `domain`: retail / librería (catálogo y ventas).
- `scale`: single-tenant, uso interno de una librería de barrio; despliegue público en VPS para corrección.
- `stack`: Python 3.12 + FastAPI + SQLModel + SQLAlchemy async + asyncpg + PostgreSQL 16 + Docker.
- `needs_infra`: true (PostgreSQL y Docker/VPS).
