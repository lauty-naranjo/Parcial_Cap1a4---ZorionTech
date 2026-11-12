# Proposal

## Why

La aplicación funciona en local, pero el Ejercicio 7 (15 %) exige empaquetarla en una imagen Docker reproducible que arranque en el VPS, corra sin privilegios y traiga su propio healthcheck. Antes de este change no existía `Dockerfile` ni `.dockerignore`, así que no había forma de construir ni desplegar el proyecto.

El entorno de desarrollo cuenta con **Docker 29.7.2** (motor Linux), así que este change no se limita a entregar los artefactos y el procedimiento reproducible: también ejecuta el build y el run y captura la evidencia real de D-01, D-02, D-05, D-06 y D-07 (con un PostgreSQL efímero en Docker, no la base del host). D-03 (endpoints públicos) y D-04 (reinicio con datos) siguen siendo de C-09, que repite el procedimiento en el VPS con la base real.

## What Changes

- **Nuevo `Dockerfile`**: `FROM python:3.12-alpine`, `WORKDIR /app`, dependencias antes del código (`COPY requirements.txt` + `RUN pip install --no-cache-dir`), `COPY app ./app`, usuario `appuser` (uid 1000) y `USER appuser`, `EXPOSE 8000`, `HEALTHCHECK` contra `http://127.0.0.1:8000/health/ready` y `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
- **Nuevo `.dockerignore`**: excluye `.env`, `.venv`, `.git`, `__pycache__`, `*.pyc`, `.pytest_cache`, `knowledge-base`, `docs`, `evidencia`, `openspec` y `test`; **no** excluye `app/` (ahí vive `app/seed.py`).
- **Sin `COPY scripts`**: el seed viaja dentro de `app/`, así que `python -m app.seed` funciona en el contenedor sin una capa adicional. `scripts/` contiene solo utilidades de evidencia y no se copia.
- **Nuevo `DEPLOY.md`** con la sección de imagen y contenedor (build, `docker run` con `--env-file`, healthcheck, seed, usuario, actualización); C-09 lo completa con URL pública, fecha de despliegue y los casos D-03/D-04.
- **`.gitignore`**: agrega `.env.docker` (archivo local con `DATABASE_URL`, nunca versionado) si no está cubierto.
- **Procedimiento de verificación reproducible** (`scripts/verificar_imagen.sh` o bloque de comandos documentado en `DEPLOY.md`) para D-01, D-02, D-05 y D-06, ejecutable donde haya Docker.
- **Evidencia**: `evidencia/D-01`, `D-02`, `D-05`, `D-06` y `D-07` contienen la salida **real** capturada al ejecutar el build, el run, el seed y una venta en el entorno de desarrollo; D-03 y D-04 quedan como plantillas `ESTADO: PENDIENTE (C-09)`. No se escribe ninguna salida ficticia.
- **Test de artefactos** (pytest, sin Docker): verifica que el `Dockerfile` parte de `python:3.12-alpine`, usa `127.0.0.1` en el `HEALTHCHECK`, no contiene credenciales y que `.dockerignore` excluye `.env`/`.venv`/`.git`.
- Sin cambios de código de aplicación, de contrato HTTP, de esquema ni de dependencias de `requirements.txt`.

## Capabilities

### New Capabilities

- `container-image`: empaquetado de la API en una imagen Alpine reproducible, sin secretos, con usuario no root y healthcheck propio, más el procedimiento de build/run y la política de evidencia verificable.

### Modified Capabilities

Ninguna. Los healthchecks (`health-checks`), el seed (`seed-data`) y los contratos (`api-contracts`) no cambian: la imagen los consume tal como están.

## Impact

- **Archivos nuevos**: `Dockerfile`, `.dockerignore`, `DEPLOY.md`, `test/test_artefactos_imagen.py`, `scripts/verificar_imagen.sh` (o bloque equivalente en `DEPLOY.md`), `evidencia/D-0*.txt` con la salida real de D-01/D-02/D-05/D-06/D-07 y D-03/D-04 pendientes de C-09.
- **Archivos modificados**: `.gitignore` (`.env.docker`), `README.md` (sección breve de Docker que apunta a `DEPLOY.md`), `CHANGES.md` (estado de C-08 al archivo).
- **Sin impacto** en `app/`, `test/` funcional, `requirements.txt` ni en la base de datos.
- **Riesgo de verificación**: el build y el run se probaron en el entorno de desarrollo con Docker 29.7.2 y un PostgreSQL efímero; el VPS puede diferir en red, versión del motor o base real, por eso C-09 repite el procedimiento y completa D-03/D-04 con la salida del servidor.
