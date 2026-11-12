# Design

## Context

Ver `proposal.md` §Why. Estado actual que condiciona el diseño:

- No existe `Dockerfile`, `.dockerignore` ni `DEPLOY.md`. `scripts/` solo contiene `generar_evidencia_c07.py`; el seed vive en `app/seed.py` (C-05, archivado) y se invoca con `python -m app.seed`.
- `app/main.py::create_app()` llama a `configurar_logging()` (stdout idempotente, C-07) y el `lifespan` ejecuta `get_settings()`, `build_engine`, `create_all` y `dispose`. Si falta `DATABASE_URL`, `get_settings()` lanza `ConfigurationError` dentro del `lifespan` y uvicorn aborta el arranque.
- `app/core/config.py::load_dotenv()` corre al importar; dentro de la imagen no hay `.env`, así que es inofensivo.
- `requirements.txt` contiene `fastapi[standard]`, `sqlmodel>=0.0.24`, `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.30`, `python-dotenv>=1.0` (sin versiones fijas ni hashes).
- `.gitignore` cubre `.env`, `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, pero **no** `.env.docker`.
- **Entorno de verificación**: Docker 29.7.2 con motor Linux está operativo en la máquina de desarrollo (el CLI no está en el `PATH` del proceso: se invoca por ruta absoluta). El apply de C-08 ejecutó `docker build`, `docker run`, `docker ps`, `docker images`, `docker logs` y `docker exec` contra un PostgreSQL 16 efímero en Docker; la base del host no se tocó.
- Suite actual: 227 tests en verde; ninguno toca Docker.

## Goals / Non-Goals

**Goals:**

- Entregar `Dockerfile` y `.dockerignore` completos, revisables y alineados con `knowledge-base/12_devops_y_despliegue.md`.
- Dejar un procedimiento reproducible (script + documentación) que produzca D-01, D-02, D-05 y D-06 en cualquier máquina con Docker, sin ambigüedad.
- Cubrir con pytest lo que **sí** es verificable sin motor: el contenido de los artefactos y la ausencia de secretos.
- Iniciar `DEPLOY.md` con lo propio del contenedor; C-09 lo completa con URL pública, fecha de despliegue y D-03/D-04.

**Non-Goals:**

- No se inventa ninguna salida de Docker: toda evidencia corresponde a un comando ejecutado en el entorno de desarrollo.
- No se agrega Docker Compose, base en el contenedor ni migraciones.
- No se toca código de aplicación, contrato HTTP, esquema ni `requirements.txt` (salvo que un build real demuestre que falta un paquete del sistema; ver Riesgos).
- No se despliega en el VPS (C-09); allí se generan D-03 y D-04. D-07 sí se capturó en el apply con el contenedor local.

## Decisions

### 1. `Dockerfile` con el orden exigido por la consigna

Contenido exacto propuesto:

```dockerfile
FROM python:3.12-alpine

WORKDIR /app

# Dependencias primero: si requirements.txt no cambia, la capa sale de caché
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código después del pip install
COPY app ./app

# Usuario sin privilegios (uid 1000), sin home
RUN adduser -D -H -u 1000 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Justificación de cada instrucción: `python:3.12-alpine` es la única base bajo 100 MB (74,7 MB medidos por la cátedra); `--no-cache-dir` evita peso y capas inmutables; `EXPOSE 8000` documenta el puerto aunque el mapeo real lo hace `-p`; `HEALTHCHECK` es la única forma de que `docker ps` muestre salud sin Compose.

**Alternativa considerada**: `python:3.12-slim` (180 MB). Descartada: incumple D-01.

**Alternativa considerada**: multi-stage con `pip wheel` y copia de wheels. Descartada: agrega complejidad y una etapa de build con compilador, justo lo que DD-07 evita; no hay beneficio porque la consigna no exige tamaño de la imagen final.

### 2. Sin `COPY scripts`: el seed viaja en `app/`

C-05 dejó el seed en `app/seed.py` y `COPY app ./app` ya lo incluye. Copiar `scripts/` sumaría `generar_evidencia_c07.py` (no necesario en runtime) y una capa extra. `docker exec libreria python -m app.seed` funciona porque `/app` es el `WORKDIR` y el paquete `app` está en el `sys.path` por el directorio actual.

**Alternativa considerada**: `COPY scripts ./scripts` como en el borrador de la KB. Descartada: la ruta real del seed cambió en C-05; el propio `CHANGES.md` admite "o la ruta del seed elegida en C-05".

**Alternativa considerada**: copiar solo `app/seed.py` además de `app/`. Descartada: duplica archivos y rompería imports relativos del paquete.

### 3. Alpine sin compilador, con el supuesto registrado como riesgo verificable

`requirements.txt` arrastra `uvicorn`, `uvloop`, `httptools`, `watchfiles` y `asyncpg`; la consigna afirma que existen wheels musllinux y que no hace falta compilador. Se construye **sin** `build-base` por defecto. Si el build real fallara por compilación, la alternativa documentada es instalar `build-base`/`libpq` en la misma capa del `pip install` y purgarlos después (`apk del`), o pasar a `python:3.12-slim` perdiendo D-01. No se agrega nada de eso preventivamente: encarece el build y contradice DD-07.

### 4. Usuario no root y consecuencias sobre el sistema de archivos

`adduser -D -H -u 1000 appuser` crea el usuario sin home y con uid numérico fijo (reproducible entre builds), y `USER appuser` cambia el proceso. `WORKDIR /app` queda propiedad de root y la app solo lee de ahí; cuando Python intenta escribir `__pycache__` y falla por permisos, lo ignora y sigue (no es un error fatal). Los paquetes instalados por pip ya traen sus `.pyc` generados en el build, así que no hay penalidad de arranque.

**Alternativa considerada**: `chown -R appuser /app`. Descartada: agrega una capa del tamaño del código sin necesidad; la aplicación no escribe en el proyecto.

**Alternativa considerada**: uid 10001 (estilo distroless). Descartada: la consigna y D-06 hablan de un usuario sin privilegios; 1000 es legible y suficiente.

### 5. `HEALTHCHECK` con `127.0.0.1` y `wget` de busybox

Alpine trae `wget` de busybox; no se instala `curl`. `localhost` en musl resuelve primero `::1` y uvicorn con `--host 0.0.0.0` escucha solo IPv4: un healthcheck con `localhost` daría `unhealthy` falso. `--start-period=10s` cubre el `create_all` inicial; si la base tarda más, los reintentos de 30 s dan margen.

**Alternativa considerada**: `python -c "import urllib.request; ..."`. Descartada: arranca un intérprete completo cada 30 s y complica el `CMD` del healthcheck.

### 6. `.dockerignore` exacto (con `.env.docker` agregado)

Contenido exacto propuesto:

```dockerignore
.env
.env.docker
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

Los once primeros elementos son los de `CHANGES.md` §C-08 y `knowledge-base/12_devops_y_despliegue.md`. Se agrega `.env.docker` porque es el archivo local que el propio procedimiento pide crear en la raíz para `--env-file`; sin esa línea, un build descuidado subiría el archivo con la URL y la contraseña al contexto. **`app/` nunca se excluye**: ahí vive `app/seed.py`. Tampoco se excluye `requirements.txt`, que el `Dockerfile` necesita.

**Alternativa considerada**: `.env*`. Descartada: excluiría `env.example`, que documenta la forma de la URL y no tiene valores reales; se prefiere una lista explícita y auditable.

### 7. Configuración solo por `--env-file` y fallo sin `DATABASE_URL`

El `Dockerfile` no declara `ENV DATABASE_URL` ni `ARG`. `docker run --env-file .env.docker -p 8000:8000 libreria` inyecta `DATABASE_URL` y `SQL_ECHO`. Sin `DATABASE_URL`, el `lifespan` lanza `ConfigurationError`, uvicorn falla al iniciar y el proceso termina con código distinto de 0; el código exacto se registra en la evidencia cuando se ejecute (uvicorn no documenta un código estable para fallos de lifespan, por eso el criterio es "≠ 0"). La URL puede contener `@`, `:` o `#`; se documenta percent-encoding como ya hace `README.md`.

**Alternativa considerada**: `ENV DATABASE_URL=postgresql+asyncpg://...` de ejemplo. Descartada: viola RN-G-04 y DD-09; una capa con la cadena queda para siempre.

### 8. Test de artefactos, no de Docker

`test/test_artefactos_imagen.py` (pytest puro, sin motor) verifica el contrato estático:

- `Dockerfile` existe y su primera instrucción efectiva es `FROM python:3.12-alpine`.
- `COPY requirements.txt` y `RUN pip install --no-cache-dir -r requirements.txt` aparecen **antes** de `COPY app ./app`.
- Contiene `adduser -D -H -u 1000 appuser` y `USER appuser`; `EXPOSE 8000`; `CMD` con `app.main:app`, `0.0.0.0` y `8000`.
- `HEALTHCHECK` apunta a `http://127.0.0.1:8000/health/ready` y el archivo **no** contiene `localhost`.
- El `Dockerfile` no contiene `DATABASE_URL`, `postgresql://` ni `postgresql+asyncpg://`.
- `.dockerignore` incluye las entradas obligatorias, no contiene una línea que excluya `app/` y excluye `.env.docker`.
- `.gitignore` incluye `.env.docker`.
- `DEPLOY.md` menciona `docker build`, `docker run`, `--env-file`, `docker exec libreria python -m app.seed` y `127.0.0.1`.

**Alternativa considerada**: test que invoque `docker` y se salte si falta. Descartada: en esta máquina se saltaría siempre y no protegería nada; la verificación real es el script de shell.

### 9. Procedimiento reproducible: script + `DEPLOY.md`

Se versiona `scripts/verificar_imagen.sh` (bash, para el VPS Linux) que:

1. valida que `docker` exista y falle con mensaje claro si no;
2. `docker build -t libreria .`;
3. `docker pull python:3.12-alpine` y `docker images` de la base y del proyecto (D-01); el pull explícito es necesario porque el store containerd de Docker 29 no etiqueta la base usada por digest en el `FROM`;
4. `docker run -d --name libreria -p 8000:8000 --env-file "${ENV_FILE:-.env.docker}" libreria` y espera `healthy` con un bucle acotado; imprime `docker ps` y `docker logs` (D-02);
5. `docker exec libreria id` (D-06);
6. `docker rm -f libreria`; `docker run --rm libreria` **sin** `--env-file` y captura el código de salida (D-05);
7. escribe las salidas en `evidencia/D-0*.txt` con encabezado de fecha y comando, sin imprimir el contenido del archivo de variables.

El script nunca hace `cat` del `--env-file` ni pasa la URL por la línea de comandos. `DEPLOY.md` reproduce los mismos comandos para quien prefiera ejecutarlos a mano.

**Alternativa considerada**: solo documentar comandos. Descartada: el script reduce el error de transcripción y hace la evidencia repetible; se mantiene la versión manual en `DEPLOY.md` por si no hay bash.

### 10. Evidencia con salida real, nunca salidas ficticias

Los archivos `evidencia/D-01-docker-images.txt`, `D-02-build-run-ps.txt`, `D-05-sin-database-url.txt`, `D-06-usuario.txt` y `D-07-background.txt` se escriben con esta forma, tomada de los comandos que se ejecutan:

```
ESTADO: VERIFICADO (<fecha>) — Docker <versión>, motor Linux
CASO: D-0x — <qué demuestra>
COMANDOS:
  <bloque reproducible>
CRITERIO DE ACEPTACIÓN:
  <resultado esperado>
SALIDA REAL:
  <salida copiada del comando ejecutado>
```

Si un caso no se puede ejecutar en el entorno, su archivo conserva `ESTADO: PENDIENTE (<change responsable>)` con el comando y el criterio, y la sección `SALIDA REAL` queda vacía.

D-03 y D-04 no se generan en C-08: pertenecen a C-09 y allí se completan. Con Docker operativo, el apply ejecutó el script (y los comandos equivalentes) y escribió `VERIFICADO (2026-11-12)` con la salida verdadera en D-01, D-02, D-05, D-06 y D-07; D-03 y D-04 conservan `ESTADO: PENDIENTE (C-09)`.

## Casos D: alcance de la verificación

| Caso | Sin Docker | Con Docker | Responsable |
|---|---|---|---|
| D-01 tamaño base | No. Se verifica que el `Dockerfile` parte de `python:3.12-alpine` (test de artefactos) | `docker images` con base <100 MB | C-08 (script) |
| D-02 build/run/ps/logs | No. Se verifica orden de capas y `CMD` (test) | build, `docker ps` healthy, `docker logs` con tablas creadas | C-08 (script) |
| D-05 sin `DATABASE_URL` | Parcial: el código ya falla en `get_settings()` (cubierto por tests de `app-foundation`) | Código de salida real ≠ 0 del contenedor | C-08 (script) |
| D-06 usuario no root | Parcial: `adduser` + `USER appuser` en el `Dockerfile` (test) | `docker exec libreria id` | C-08 (script) |
| D-03 endpoints públicos | No | C-09 | C-09 |
| D-04 reinicio con datos | No | C-09 | C-09 |
| D-07 aviso en logs | Parcial: C-07 ya probó logger a stdout y orden | `docker logs` | C-08 (local); C-09 (VPS) |

Sin Docker operativo, C-08 podía cerrar como **artefactos + procedimiento + tests**, con la evidencia marcada como pendiente. Con Docker 29.7.2 operativo, C-08 cierra como **artefactos + procedimiento + tests + evidencia real**: el apply ejecutó build, run, seed, D-01, D-02, D-05, D-06 y D-07. C-09 repite el procedimiento en el VPS con la base real y agrega D-03 y D-04.

## Risks / Trade-offs

- **Docker local distinto del VPS** → mitigación: el script reproducible y los tests estáticos permiten repetir la verificación; el build local se hizo con Docker 29.7.2 y un PostgreSQL efímero, y C-09 repite el procedimiento con el motor y la base del servidor. No se simulan salidas.
- **Falta una wheel musllinux en el build real** → mitigación: el build falla temprano y ruidosamente; la alternativa documentada es `build-base`/`libpq` solo durante el `pip install` con purga posterior, o `python:3.12-slim` como último recurso (incumple D-01 y se anota en `DEPLOY.md`).
- **`requirements.txt` sin versiones fijas** → el build puede instalar versiones distintas con el tiempo y romper Alpine. Mitigación: no se fijan versiones en este change (fuera de alcance y afectaría el entorno local); se registra como riesgo de reproducibilidad y se anota en `DEPLOY.md`.
- **`WORKDIR /app` propiedad de root** → Python no puede escribir `__pycache__`; no rompe porque ignora el fallo y los paquetes ya vienen compilados. Si alguna dependencia necesitara escribir en `/app` en runtime, fallaría con `Permission denied`; no es el caso de esta app.
- **Healthcheck dependiente de la base** → con PostgreSQL caído el contenedor queda `unhealthy` aunque el proceso viva. Es el comportamiento buscado (D-02 y `docker ps` reflejan readiness real).
- **`--restart unless-stopped` con configuración inválida** → Docker reintenta en bucle si falta `DATABASE_URL`; es visible en `docker ps`/`docker logs` y D-05 se captura con `docker run` sin `--restart`.
- **El script de verificación escribe en `evidencia/`** → si se corre en el VPS, sobreescribe plantillas con salidas reales; se documenta que eso es el paso esperado y que `git diff` debe mostrar el cambio de `ESTADO`.
- **`.env.docker` en la raíz** → mitigación doble: `.gitignore` y `.dockerignore`.

## Migration Plan

1. Apply: crear `Dockerfile`, `.dockerignore`, `DEPLOY.md`, el script y las plantillas de evidencia; actualizar `.gitignore` y `README.md`; agregar el test de artefactos.
2. Verificación local: suite completa (227 + 22 nuevos) en verde, `openspec validate --strict imagen-docker`, y `bash scripts/verificar_imagen.sh` (o los comandos equivalentes) con Docker 29.7.2, que produjo D-01, D-02, D-05, D-06 y D-07.
3. Verificación con Docker (C-09 o máquina con motor): `bash scripts/verificar_imagen.sh` con `.env.docker` válido; completar D-01/D-02/D-05/D-06 y continuar con D-03/D-04/D-07.
4. Rollback: borrar los artefactos nuevos y revertir `.gitignore`/`README.md`; no hay migración de datos ni de esquema. La imagen anterior en el VPS sigue operativa hasta que C-09 haga `docker rm -f` + `docker run`.

## Open Questions

- Código de salida exacto de uvicorn cuando el `lifespan` falla: se registra al ejecutar D-05; el criterio de la spec es "≠ 0", así que no bloquea el diseño.
- Valor del puerto público: lo define la cátedra; C-09 lo fija en `DEPLOY.md`. En local se usa `8000:8000`.

## UI Mockups

`Decision: no (project policy)` — `visual_design.mode` es `off` y este change no tiene interfaz.
