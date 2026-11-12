# Despliegue del contenedor

Este documento cubre lo propio de la **imagen**: construirla, correrla, verificar
su salud y cargar los datos iniciales. El despliegue en el VPS (URL pública,
fecha, puerto asignado y casos D-03/D-04) lo completa **C-09**.

- Imagen base: `python:3.12-alpine` (medida por debajo de los 100 MB).
- La configuración entra **solo** por `--env-file`; no hay `ENV` ni `ARG` con
  cadenas de conexión dentro de la imagen.
- El proceso corre con el usuario `appuser` (uid 1000), no root.

## Requisitos

- Docker con motor Linux (probado con Docker 29.7.2).
- Un PostgreSQL 16 accesible desde el contenedor. Si la base corre en el host
  del servidor, ver «La base no está en `localhost`».
- El repositorio completo en el directorio de trabajo (el `Dockerfile` usa el
  contexto `.`).

## Archivo de variables

El archivo de variables es **local**, no se versiona y no debe copiarse al
`.zip` de entrega. Se crea en la raíz del proyecto como `.env.docker` (está en
`.gitignore` y en `.dockerignore`) a partir de la plantilla `env.example`:

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@host:5432/base
SQL_ECHO=false
```

- `DATABASE_URL` es obligatoria; si falta, el contenedor termina con código
  distinto de 0 (caso D-05).
- Si la contraseña tiene `@`, `:`, `/`, `#` u otro carácter especial, codificala
  con percent-encoding (`p@ss` → `p%40ss`).
- `SQL_ECHO=false` en despliegue; `true` solo para capturar consultas.

## Construcción

```bash
docker build -t libreria .
```

Las dependencias se instalan antes de copiar `app/`, así que un cambio de código
no reinstala `requirements.txt`. El build no incluye `.env`, `.env.docker`,
`.venv`, `.git`, `test/`, `evidencia/`, `knowledge-base/`, `docs/` ni
`openspec/` (ver `.dockerignore`).

## Ejecución

```bash
docker run -d --name libreria -p 8000:8000 --restart unless-stopped \
  --env-file .env.docker libreria
```

| Flag | Efecto |
|---|---|
| `-p 8000:8000` | Publica el puerto 8000 del contenedor (en el VPS, `-p <puerto>:8000`) |
| `--restart unless-stopped` | Docker vuelve a levantar el contenedor si termina |
| `--env-file .env.docker` | Inyecta `DATABASE_URL` y `SQL_ECHO` sin hornearlas en la imagen |

Al arrancar, el `lifespan` crea las tablas faltantes con
`SQLModel.metadata.create_all`. No hay migraciones.

### La base no está en `localhost`

Dentro del contenedor, `localhost` es el propio contenedor. Para llegar a un
PostgreSQL que corre en el host del servidor:

```bash
docker run -d --name libreria -p 8000:8000 --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  --env-file .env.docker libreria
```

y usar `host.docker.internal` como host en `DATABASE_URL`.

## Verificación del healthcheck

La imagen declara `HEALTHCHECK` contra `GET /health/ready` en
`http://127.0.0.1:8000` (nunca `localhost`: en Alpine resuelve primero IPv6 y
uvicorn escucha IPv4).

```bash
docker ps                                                     # estado: healthy
docker exec libreria wget -qO- http://127.0.0.1:8000/health/ready
# {"estado": "listo", "base": "ok"}
```

Si la base no responde, `/health/ready` devuelve 503 y el contenedor queda
`unhealthy` aunque el proceso siga vivo: es el comportamiento buscado.

## Seed dentro del contenedor

El módulo de datos iniciales viaja dentro de `app/` (`app/seed.py`), por eso no
se copia `scripts/` a la imagen:

```bash
docker exec libreria python -m app.seed
```

Es idempotente y deja editorial y género id 1, cuatro autores, cuatro libros,
dos clientes y la venta id 2 con total `77000.00`. No imprime la URL ni
credenciales.

## Actualización

```bash
docker build -t libreria .
docker rm -f libreria
docker run -d --name libreria -p 8000:8000 --restart unless-stopped \
  --env-file .env.docker libreria
docker ps
```

Los datos no se pierden: viven en el PostgreSQL del servidor, no en el
contenedor.

## Qué hizo falta para que corra en el contenedor

- `Dockerfile` con `python:3.12-alpine`, usuario `appuser` (uid 1000) y
  `HEALTHCHECK` propio; sin `COPY scripts`, porque el seed vive en `app/seed.py`
  desde C-05.
- `.dockerignore` que excluye entornos virtuales, `.git`, pruebas y
  documentación, y también `.env.docker` (el archivo local con credenciales).
- `.gitignore` con `.env.docker`.
- `.env.docker` local creado a partir de `env.example` (no versionado).
- Ningún cambio en `app/`, en el contrato HTTP ni en `requirements.txt`.
- Para la verificación local se usó un PostgreSQL 16 efímero en una red de
  Docker (`postgres:16-alpine`) en lugar de la base del host; ese contenedor se
  eliminó al terminar (ver `evidencia/`).

## Evidencia

| Caso | Archivo | Estado |
|---|---|---|
| D-01 tamaño de la imagen base | `evidencia/D-01-docker-images.txt` | verificado 2026-11-12 |
| D-02 build, run, `docker ps` y `docker logs` | `evidencia/D-02-build-run-ps.txt` | verificado 2026-11-12 |
| D-03 endpoints públicos desde fuera | `evidencia/D-03-endpoints-publicos.txt` | pendiente (C-09) |
| D-04 reinicio con datos intactos | `evidencia/D-04-restart.txt` | pendiente (C-09) |
| D-05 contenedor sin `DATABASE_URL` | `evidencia/D-05-sin-database-url.txt` | verificado 2026-11-12 |
| D-06 usuario no root | `evidencia/D-06-usuario.txt` | verificado 2026-11-12 |
| D-07 aviso del comprobante en logs | `evidencia/D-07-background.txt` | verificado 2026-11-12 |

Procedimiento reproducible en Linux/WSL:

```bash
bash scripts/verificar_imagen.sh
# o con otro archivo de variables:
ENV_FILE=/ruta/al/archivo.env bash scripts/verificar_imagen.sh
```

El script no imprime el contenido del archivo de variables. La evidencia de C-08
se capturó en el entorno de desarrollo con Docker 29.7.2; C-09 repite el
procedimiento en el VPS con la base real y completa D-03 y D-04.
