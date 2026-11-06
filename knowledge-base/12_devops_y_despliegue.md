# DevOps y Despliegue

> Esta KB complementa los 10 archivos canónicos: el contenedor y el VPS pesan **25 puntos** (15 + 10) y tienen reglas propias que no encajan en el modelo de dominio.

## Imagen Docker

### Reglas del Dockerfile (cada una con su razón)

| Regla | Razón |
|---|---|
| `FROM python:3.12-alpine` | La imagen base medida con Docker 29.2 (2-nov-2026) ocupa **74,7 MB**; `python:3.12-slim` ocupa 180 MB y no cumple el límite de 100 MB |
| Copiar e instalar `requirements.txt` **antes** del código, con `--no-cache-dir` | Si las dependencias no cambian, la capa sale de caché; un cambio de código no reinstala todo |
| Crear usuario sin privilegios y activarlo con `USER` | Si vulneran la app, no son dueños del contenedor (D-06) |
| No incluir secretos | `.dockerignore` excluye `.env`, `.venv`, `.git`, `__pycache__`; la URL y la clave entran por `--env-file` (lo horneado en una capa queda para siempre) |
| `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `127.0.0.1` dentro del contenedor solo se alcanza desde adentro; el puerto publicado nunca respondería |
| `create_all` al arrancar | Crea las tablas; si la base no responde, el arranque falla y el contenedor termina con error (deseado) |
| `HEALTHCHECK` sobre `GET /health/ready` | Sin Compose, la propia imagen declara su salud y `docker ps` lo muestra |
| `HEALTHCHECK` con `127.0.0.1` | Alpine no trae `curl`; `localhost` resuelve primero a `::1` y uvicorn escucha IPv4 → falso `unhealthy` |

### Forma del Dockerfile

```dockerfile
FROM python:3.12-alpine

WORKDIR /app

# Dependencias primero: capa cacheable
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código después
COPY app ./app
COPY scripts ./scripts   # si existe el seed

# Usuario sin privilegios
RUN adduser -D -H -u 1000 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.dockerignore`

```
.env
.venv
.git
__pycache__
*.pyc
.pytest_cache
knowledge-base
docs
evidencia
openspec
test
```

> `test/` y `evidencia/` pueden excluirse de la imagen: no son necesarios en runtime. Si el seed vive en `scripts/`, **no** excluirlo.

## Ejecución

```bash
docker build -t libreria .

docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped \
  --env-file <archivo-de-variables> libreria
```

| Flag | Efecto |
|---|---|
| `-p <puerto>:8000` | Publica solo la aplicación en el puerto asignado por la cátedra |
| `--restart unless-stopped` | Docker vuelve a levantar el contenedor si termina (reinicio del servidor o base no lista al arrancar) |
| `--env-file` | Configuración desde un archivo del servidor, fuera del repositorio y de la imagen |

### La base no está en localhost

Dentro del contenedor, `localhost` es el contenedor, no el servidor. Una `DATABASE_URL` con `localhost` falla con "Connection refused" aunque PostgreSQL funcione.

| Escenario | Solución |
|---|---|
| PostgreSQL en el host del servidor | `host.docker.internal` + `--add-host=host.docker.internal:host-gateway` (Linux) |
| Otra dirección provista por la cátedra | Usar esa |

### Verificación del healthcheck

```bash
docker exec libreria wget -qO- http://127.0.0.1:8000/health/live
```

La dirección que sirve es `127.0.0.1`.

## Variables de entorno del contenedor

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@host:5432/base
SQL_ECHO=false
```

- **`DATABASE_URL`**: obligatoria. Sin ella el arranque falla (D-05). Nunca en el Dockerfile, nunca en el repositorio.
- **`SQL_ECHO`**: `false` en despliegue (deja de escribir cada consulta en el registro); `true` para capturar C-07.

## Seed de datos

```bash
# Local
python -m app.seed          # o: python scripts/seed.py

# En el VPS, dentro del contenedor
docker exec libreria python -m app.seed
```

Debe dejar la base en un estado inicial conocido y ser seguro de re-ejecutar (`ON CONFLICT DO NOTHING`, `merge` o chequeo idempotente).

## DEPLOY.md — contenido obligatorio

1. URL pública.
2. Día y hora del despliegue.
3. Comandos `docker build` y `docker run` **completos**, con el nombre del archivo de variables y **sin su contenido**.
4. Cualquier cambio hecho al proyecto para que corra en el contenedor.
5. Procedimiento de actualización: construir de nuevo, eliminar el contenedor y volver a correr. Los datos no se pierden porque viven en la base del servidor.

## Actualización

```bash
docker build -t libreria .
docker rm -f libreria
docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped \
  --env-file <archivo-de-variables> libreria
docker ps          # estado healthy
```

## Evidencia (carpeta `evidencia/`)

| Archivo | Contenido |
|---|---|
| `C-07-consultas-libro.txt` | Consultas emitidas al pedir el detalle de un libro con 1 y con varios autores |
| `C-07-consultas-venta.txt` | Consultas emitidas al pedir el detalle de una venta con 1 y con varios renglones |
| `D-01-docker-images.txt` | Salida de `docker images` con la base y la del proyecto |
| `D-02-build-run-ps.txt` | `docker build`, `docker run`, `docker ps` y `docker logs` |
| `D-03-endpoints-publicos.txt` | `GET /health/ready`, `GET /libros/`, `POST /ventas/` desde fuera |
| `D-04-restart.txt` | `docker rm -f` + `docker run` + `docker ps` + datos intactos |
| `D-05-sin-database-url.txt` | Contenedor sin `DATABASE_URL` terminando con error |
| `D-06-usuario.txt` | `docker exec libreria id` con usuario no root |
| `D-07-background.txt` | `docker logs libreria` con el aviso después de la respuesta |

## Checklist de entrega

- [ ] `.zip` llamado `Parcial_Cap1a4_<NombreDelGrupo>.zip`, en una sola carpeta.
- [ ] Código fuente, `requirements.txt`, `env.example` (sin valores reales), `test/`, `Dockerfile`, `.dockerignore`.
- [ ] `README.md` con nombres y apellidos de los integrantes y pasos desde cero (venv, dependencias, `.env`, arranque, seed).
- [ ] `DEPLOY.md` completo.
- [ ] `evidencia/` con C-07 y D-01…D-07.
- [ ] **Sin** `.venv`, `__pycache__`, `.env`.
- [ ] Historial Git sin credenciales (si se incluye `.git`). Si hubo una, **cambiarla**.
- [ ] El despliegue sigue en línea hasta que se publiquen las notas.
