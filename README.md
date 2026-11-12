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

## Datos iniciales (seed)

Después de configurar la base, cargá el conjunto inicial de datos con:

```powershell
.venv\Scripts\python.exe -m app.seed
```

En Linux o dentro del contenedor:

```bash
python -m app.seed
docker exec libreria python -m app.seed
```

- Usa `DATABASE_URL` del entorno o del archivo `.env` del proyecto (sección
  Configuración). Si falta, el comando termina con código 2 y un mensaje que
  nombra la variable.
- Es **idempotente**: se puede ejecutar las veces que haga falta sobre una base
  vacía o ya sembrada. No duplica filas, no borra y no sobrescribe cambios
  hechos por la API.
- Crea las tablas faltantes y deja editorial y género id 1, cuatro autores,
  cuatro libros (incluidos «Rayuela» a 25000.00 y «Respiración artificial» a
  27000.00), dos clientes y la venta id 2 con total 77000.00.
- Ajusta las secuencias para que las altas posteriores por la API no choquen
  con los ids sembrados.
- No imprime la URL de conexión ni credenciales: solo informa los conteos por
  tabla.
- Si otra fila ya usa un valor único reservado por el seed (por ejemplo, el
  nombre de la editorial), el comando aborta con código 1 sin dejar cambios a
  medias.

## Docker

La imagen se construye a partir de `python:3.12-alpine`, corre con el usuario
`appuser` (no root) y trae su propio healthcheck sobre `/health/ready`. La
configuración entra por `--env-file` (un archivo local con `DATABASE_URL` y
`SQL_ECHO`, nunca versionado) y los datos iniciales se cargan dentro del
contenedor con `docker exec libreria python -m app.seed`.

Los comandos completos de build, ejecución, verificación y actualización están
en [DEPLOY.md](DEPLOY.md).

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
