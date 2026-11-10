# Librería de barrio — API de catálogo y ventas

API REST asincrónica construida con FastAPI, SQLModel y PostgreSQL. Este
repositorio corresponde al Capítulo 1–4 de Programación III: incluye el
esqueleto de la aplicación, el ciclo de vida del motor de base de datos en el
`lifespan`, los healthchecks, las nueve tablas del dominio y los endpoints de
CRUD de referencia (editoriales, géneros, autores, clientes y libros).

## Requisitos

- Python 3.12
- PostgreSQL 16 accesible (para arrancar la aplicación y correr el test de integración)

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

En PowerShell no hace falta activar el entorno: invocá siempre
`.venv\Scripts\python.exe -m ...`.

## Configuración

Copiá la plantilla y completá los valores reales:

```powershell
Copy-Item env.example .env
```

- `DATABASE_URL` es **obligatoria** y no tiene valor por defecto. Debe empezar
  con `postgresql+asyncpg://`. Si falta o está vacía, el arranque falla con un
  mensaje que nombra la variable.
- `SQL_ECHO` es opcional y vale `false` si no se define. Acepta `true/false`,
  `1/0`, `yes/no`, `on/off` y `si/sí` (sin distinguir mayúsculas).
- Si la contraseña tiene caracteres especiales (`@`, `:`, `/`, `#`, ...),
  codificala con percent-encoding: `p@ss` se escribe `p%40ss`.
- El archivo `.env` nunca se versiona: está listado en `.gitignore`.

## Arranque

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Al arrancar, la aplicación crea el motor asincrónico, publica el motor y la
fábrica de sesiones en `app.state` y ejecuta `SQLModel.metadata.create_all`.
**No hay migraciones**: `create_all` crea las tablas faltantes y no altera las
existentes; un cambio de esquema exige recrear la base o aplicar un `ALTER`
manual.

## Endpoints de salud

| Método | Ruta | Código | Cuerpo | Descripción |
|---|---|---|---|---|
| GET | `/health/live` | 200 | `{"estado": "vivo"}` | Proceso vivo; no consulta la base |
| GET | `/health/ready` | 200 | `{"estado": "listo", "base": "ok"}` | La base responde `SELECT 1` |
| GET | `/health/ready` | 503 | `{"estado": "no_listo", "base": "error"}` | La base no responde; el detalle queda solo en el log |

## Notas de contrato

- `PATCH /libros/{id}` edita **solo campos escalares** (`isbn`, `titulo`,
  `precio`, `stock`, `editorial_id`, `genero_id`). Las autorías **no** se editan
  por `PATCH`: se cargan únicamente en el alta del libro (`POST /libros/`).

## Pruebas

```powershell
.venv\Scripts\python.exe -m pytest -q
```

La suite por defecto no necesita PostgreSQL: el test de integración de
`/health/ready` se salta si `DATABASE_URL` no está definida. Ojo: si tenés un
`.env` con `DATABASE_URL`, el test también corre en `pytest -q`. Para ejecutarlo
solo a él:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://usuario:password@127.0.0.1:5432/base"
.venv\Scripts\python.exe -m pytest -q -m integration
```
