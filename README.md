# Librería de barrio — API de catálogo y ventas

API REST asincrónica para una librería de barrio, construida con **FastAPI**,
**SQLModel** y **PostgreSQL**. Cubre el catálogo (editoriales, géneros, autores
y libros), los clientes con su perfil y las ventas con renglones, además de los
healthchecks de proceso y de base. Corresponde al Parcial de los Capítulos 1 a 4
de Programación III.

| Dato | Valor |
|---|---|
| Grupo | **ZorionTech** |
| Integrantes | **Lautaro Naranjo** y **Martin Escudero** |
| URL pública | **`http://46.202.151.202:8000`** |

## Requisitos

- **Python 3.12**
- **PostgreSQL 16** accesible (para arrancar la aplicación y correr la suite
  completa)
- Docker 20.10 o superior, solo si se quiere construir la imagen o desplegar

## Puesta en marcha desde cero

### 1. Entorno virtual y dependencias

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

En Linux/macOS:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
```

En PowerShell no hace falta activar el entorno: invocá siempre
`.venv\Scripts\python.exe -m ...`.

### 2. Variables de entorno

Copiá la plantilla y completá los valores del entorno real:

```powershell
Copy-Item env.example .env
```

En Linux/macOS: `cp env.example .env`.

- `DATABASE_URL` es **obligatoria** y no tiene valor por defecto. Debe empezar
  con `postgresql+asyncpg://`; por ejemplo
  `postgresql+asyncpg://usuario:password@127.0.0.1:5432/libreria`. Si falta o
  está vacía, el arranque falla con un mensaje que nombra la variable.
- `SQL_ECHO` es opcional y vale `false` si no se define. Acepta `true/false`,
  `1/0`, `yes/no`, `on/off` y `si/sí` (sin distinguir mayúsculas). `true` sirve
  para ver las consultas SQL en el log.
- Si la contraseña tiene caracteres especiales (`@`, `:`, `/`, `#`, ...),
  codificala con percent-encoding: `p@ss` se escribe `p%40ss`.
- El archivo `.env` nunca se versiona ni viaja en la entrega: está en
  `.gitignore`.

## Arranque

Windows (PowerShell):

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Linux/macOS:

```bash
.venv/bin/python -m uvicorn app.main:app --reload
```

La API queda en `http://127.0.0.1:8000` y la documentación interactiva en
`http://127.0.0.1:8000/docs`.

Al arrancar, el `lifespan` crea el motor asincrónico, publica el motor y la
fábrica de sesiones en `app.state` y ejecuta `SQLModel.metadata.create_all`.
**No hay migraciones**: `create_all` crea las tablas faltantes y **no altera
las existentes**; un cambio de esquema exige recrear la base o aplicar un
`ALTER` manual (decisión DD-06).

## Datos iniciales (seed)

Con la base configurada, cargá el conjunto inicial:

```powershell
.venv\Scripts\python.exe -m app.seed
```

En Linux/macOS o dentro del contenedor:

```bash
.venv/bin/python -m app.seed
docker exec libreria-zoriontech python -m app.seed
```

- Usa `DATABASE_URL` del entorno o del archivo `.env`. Si falta, termina con
  código 2 y un mensaje que nombra la variable.
- Es **idempotente**: se puede ejecutar las veces que haga falta. No duplica
  filas, no borra y no sobrescribe cambios hechos por la API.
- Deja editorial y género id 1, cuatro autores, cuatro libros (incluidos
  «Rayuela» a `25000.00` y «Respiración artificial» a `27000.00`), dos clientes
  y la venta id 2 con total `77000.00`.
- Ajusta las secuencias para que las altas posteriores por la API no choquen
  con los ids sembrados.
- No imprime la URL de conexión ni credenciales: solo informa los conteos por
  tabla.

## Cómo correr los casos de prueba

### Archivos `.http`

En `test/` hay ocho archivos ejecutables: `health.http`, `editoriales.http`,
`generos.http`, `autores.http`, `libros.http`, `clientes.http`, `ventas.http`
y `casos-C.http`. Cada bloque declara el caso (`# Caso:`) y el resultado
esperado (`# Esperado:`); `casos-C.http` recorre C-01…C-06 y C-08, y C-07 se
documenta como comando con su evidencia.

Se ejecutan con **VS Code REST Client** o **JetBrains HTTP Client**:

1. Arrancá la API y corré el seed.
2. Abrí el `.http` y ejecutá cada bloque con la acción del cliente
   (*Send Request* / ▶).
3. La variable `@base` al inicio del archivo apunta a
   `http://localhost:8000`. Para probar la URL pública, cambiala a
   `http://46.202.151.202:8000`.

No hace falta editar el resto del archivo: los datos del seed son
deterministas y los bloques crear → duplicado están en orden.

### Suite automática

```powershell
.venv\Scripts\python.exe -m pytest -q
```

La suite por defecto no necesita PostgreSQL: los tests que lo requieren se
saltan si `DATABASE_URL` no está definida. Si tenés un `.env` con
`DATABASE_URL`, esos tests también corren. Para ejecutar solo los de
integración:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://usuario:password@127.0.0.1:5432/libreria"
.venv\Scripts\python.exe -m pytest -q -m integration
```

## Despliegue

La API está en línea en **`http://46.202.151.202:8000`**, en el contenedor
`libreria-zoriontech`, con la base en el contenedor
`libreria-zoriontech-db` (PostgreSQL 16) y las variables en
`/root/libreria-zoriontech.env`, fuera del repositorio.

El procedimiento completo —build en el servidor, archivo de variables,
transferencia, verificación, seed dentro del contenedor y actualización— está
en [DEPLOY.md](DEPLOY.md). El seed se ejecuta dentro del contenedor:

```bash
docker exec libreria-zoriontech python -m app.seed
```

## Estructura del proyecto

```text
.
├── app/
│   ├── main.py              # aplicación y lifespan
│   ├── seed.py              # datos iniciales idempotentes
│   ├── core/                # configuración, motor, errores, paginación
│   └── modules/             # editoriales, géneros, autores, libros,
│                            # clientes, ventas y health
├── test/                    # suite pytest + casos .http
├── evidencia/               # C-07 y D-01…D-07
├── scripts/                 # despliegue y verificación en el VPS
├── env.example              # plantilla de variables, sin valores reales
├── requirements.txt         # dependencias de runtime
├── requirements-dev.txt     # pytest, pytest-asyncio y httpx
├── pyproject.toml           # configuración de pytest
├── Dockerfile
├── .dockerignore
├── .gitignore
├── README.md
└── DEPLOY.md
```

## Endpoints de salud

| Método | Ruta | Código | Cuerpo | Descripción |
|---|---|---|---|---|
| GET | `/health/live` | 200 | `{"estado": "vivo"}` | Proceso vivo; no consulta la base |
| GET | `/health/ready` | 200 | `{"estado": "listo", "base": "ok"}` | La base responde `SELECT 1` |
| GET | `/health/ready` | 503 | `{"estado": "no_listo", "base": "error"}` | La base no responde; el detalle queda solo en el log |

## Notas de contrato

- `PATCH /libros/{id}` edita **solo campos escalares** (`isbn`, `titulo`,
  `precio`, `stock`, `editorial_id`, `genero_id`). Las autorías **no** se
  editan por `PATCH`: se cargan únicamente en el alta del libro
  (`POST /libros/`).
- Los importes se serializan siempre como string decimal de dos cifras
  (`"25000.00"`), nunca como número JSON.
- Toda colección acepta `limit` (1…100, por defecto 20) y `offset` (≥ 0, por
  defecto 0).
- Los errores de unicidad y de clave foránea devuelven **409** con un mensaje
  propio; nunca exponen texto de PostgreSQL, nombres de constraints ni trazas.
- No hay migraciones ni `DELETE` en los recursos del catálogo: el esquema se
  crea con `create_all` y se carga con el seed.
