# Tasks

> Docker 29.7.2 (motor Linux) está operativo en el entorno de desarrollo: el apply ejecutó `docker build`, `docker run`, `docker ps`, `docker images`, `docker logs` y `docker exec` contra un PostgreSQL 16 efímero en Docker, y capturó D-01, D-02, D-05, D-06 y D-07 como evidencia real. El CLI no está en el `PATH` del proceso: se invoca por ruta absoluta. D-03 y D-04 siguen siendo de C-09. TDD aplica solo al test de artefactos: el grupo 1 escribe el test que falla (RED) y el grupo 2 lo pone en verde (GREEN).

## 1. Test de artefactos (RED)

- [x] 1.1 Crear `test/test_artefactos_imagen.py` con la prueba del `Dockerfile`: existe, la primera instrucción efectiva (ignorando comentarios y líneas vacías) es `FROM python:3.12-alpine`, `COPY requirements.txt` y `RUN pip install --no-cache-dir -r requirements.txt` aparecen antes de `COPY app ./app`, existen `adduser -D -H -u 1000 appuser`, `USER appuser`, `EXPOSE 8000` y `CMD` con `app.main:app`, `0.0.0.0` y `8000`. Verificación: `pytest test/test_artefactos_imagen.py -q` falla porque los archivos no existen.
- [x] 1.2 Agregar la prueba de healthcheck y secretos: `HEALTHCHECK` contiene `http://127.0.0.1:8000/health/ready`, el `Dockerfile` no contiene la palabra `localhost` ni cadenas `DATABASE_URL`, `postgresql://` o `postgresql+asyncpg://`, y hay una sola instrucción `HEALTHCHECK`. Verificación: el test falla en RED.
- [x] 1.3 Agregar la prueba de `.dockerignore` y `.gitignore`: `.dockerignore` incluye `.env`, `.env.docker`, `.venv`, `.git`, `__pycache__`, `*.pyc`, `.pytest_cache`, `knowledge-base`, `docs`, `evidencia`, `openspec` y `test`; ninguna línea excluye `app/` ni `requirements.txt`; `.gitignore` incluye `.env.docker`. Verificación: el test falla en RED.
- [x] 1.4 Agregar la prueba de documentación: `DEPLOY.md` existe y menciona `docker build -t libreria .`, `docker run`, `--env-file`, `docker exec libreria python -m app.seed` y `http://127.0.0.1:8000/health/ready`, y no contiene `postgresql+asyncpg://` con usuario y contraseña reales (solo valores de ejemplo o nombres de archivo). Verificación: el test falla en RED.

## 2. Imagen: `Dockerfile` y `.dockerignore` (GREEN)

- [x] 2.1 Crear `Dockerfile` con el contenido exacto de `design.md` §Decisión 1 (base alpine, dependencias antes del código, `COPY app ./app`, usuario `appuser`, `EXPOSE`, `HEALTHCHECK` a `127.0.0.1`, `CMD` de uvicorn en `0.0.0.0:8000`). Verificación: las tareas 1.1 y 1.2 pasan.
- [x] 2.2 Crear `.dockerignore` con las doce líneas de `design.md` §Decisión 6 (las once de C-08 más `.env.docker`), sin excluir `app/`. Verificación: la tarea 1.3 pasa.
- [x] 2.3 Agregar `.env.docker` a `.gitignore` bajo la sección de entornos y secretos. Verificación: `git check-ignore -v .env.docker` responde con la regla y la tarea 1.3 pasa.
- [x] 2.4 Verificar que el contexto de build no incluiría secretos ni el entorno virtual: `git status --porcelain` no muestra `Dockerfile`/`.dockerignore` inesperados, y una revisión manual confirma que `app/seed.py` está incluido por `COPY app ./app` y que `scripts/` no se copia. Verificación: lectura del `Dockerfile` final contra el bloque exacto del diseño.

## 3. Procedimiento reproducible, documentación y evidencia real

- [x] 3.1 Crear `scripts/verificar_imagen.sh` con los pasos de `design.md` §Decisión 9: comprobar que existe `docker`, build, `docker images` (D-01), run con `--env-file "${ENV_FILE:-.env.docker}"` y `-p 8000:8000`, espera acotada de `healthy`, `docker ps`, `docker logs` (D-02), `docker exec libreria id` (D-06), `docker rm -f` y run sin `--env-file` capturando el código de salida (D-05). El script MUST NOT imprimir el contenido del archivo de variables. Verificación: `bash -n scripts/verificar_imagen.sh` no reporta errores de sintaxis y una lectura confirma que no hay `cat` ni `echo` del archivo de entorno.
- [x] 3.2 Crear los archivos de evidencia `evidencia/D-01-docker-images.txt`, `evidencia/D-02-build-run-ps.txt`, `evidencia/D-05-sin-database-url.txt`, `evidencia/D-06-usuario.txt` y `evidencia/D-07-background.txt` con la salida real de los comandos ejecutados (Docker 29.7.2, PostgreSQL efímero), el caso, los comandos reproducibles, el criterio de aceptación y la sección `SALIDA REAL`. `D-03` y `D-04` se crean con `ESTADO: PENDIENTE (C-09)` y sin salida. Verificación: cada archivo existe y ninguna salida es inventada.
- [x] 3.3 Crear `DEPLOY.md` con las secciones de imagen y contenedor: requisitos (Docker en el VPS), `docker build -t libreria .`, creación de `.env.docker` local a partir de `env.example` con percent-encoding, `docker run -d --name libreria -p 8000:8000 --restart unless-stopped --env-file .env.docker libreria`, `--add-host=host.docker.internal:host-gateway` para PostgreSQL en el host, verificación del healthcheck con `docker exec libreria wget -qO- http://127.0.0.1:8000/health/ready`, seed con `docker exec libreria python -m app.seed`, procedimiento de actualización y estado de la evidencia (D-01/D-02/D-05/D-06/D-07 verificados el 2026-11-12; D-03/D-04 pendientes de C-09). Sin valores reales de conexión. Verificación: la tarea 1.4 pasa y una lectura completa no muestra credenciales.
- [x] 3.4 Agregar en `README.md` una sección breve «Docker» que remita a `DEPLOY.md`, indique que la imagen es `python:3.12-alpine`, que se corre con `--env-file` y que el seed dentro del contenedor es `docker exec libreria python -m app.seed`; no repetir los comandos completos. Verificación: `README.md` menciona `DEPLOY.md` y no incluye cadenas de conexión.

## 4. Verificación de integración

- [x] 4.1 Ejecutar la suite completa: `.venv\Scripts\python.exe -m pytest -q`. Verificación: los 227 tests previos siguen en verde y los nuevos de `test/test_artefactos_imagen.py` pasan (sin requerir Docker ni PostgreSQL).
- [x] 4.2 Revisar que ningún artefacto afirme una verificación no ejecutada: `rg -n "VERIFICADO|healthy|uid=" evidencia/` debe coincidir con comandos realmente ejecutados en el apply, y `D-03`/`D-04` deben conservar `ESTADO: PENDIENTE (C-09)`. Verificación: cada salida de evidencia corresponde a un comando ejecutado y no hay salidas inventadas.
- [x] 4.3 Ejecutar `openspec validate --strict imagen-docker` y revisar el resultado. Verificación: el change valida sin errores ni advertencias.
- [x] 4.4 Contrastar el `Dockerfile` final con `knowledge-base/12_devops_y_despliegue.md` §Imagen Docker y con `CHANGES.md` §C-08: misma base, orden de capas, usuario, healthcheck con `127.0.0.1`, `CMD` y `.dockerignore`; documentar en `DEPLOY.md` cualquier diferencia (por ejemplo, la ausencia de `COPY scripts`). Verificación: lectura cruzada sin divergencias no explicadas.

## Workflow follow-up

- Verificar el change con `openspec-verify-change` contra proposal, design, specs y tasks.
- Archivar el change y sincronizar la delta a `openspec/specs/container-image/spec.md`.
- Marcar C-08 en `CHANGES.md` con su línea de cierre: artefactos entregados, 249 tests en verde, evidencia D-01/D-02/D-05/D-06/D-07 ejecutada el 2026-11-12, D-03/D-04 pendientes de C-09, y el procedimiento reproducible en `scripts/verificar_imagen.sh` + `DEPLOY.md`.
- En C-09, ejecutar `bash scripts/verificar_imagen.sh` con el `--env-file` del servidor para refrescar D-01/D-02/D-05/D-06 con la salida del VPS y completar D-03 y D-04 (hoy `ESTADO: PENDIENTE (C-09)`) con la salida verdadera.
