# Proposal

## Why

El Ejercicio 8 (10 %) exige el proyecto **en línea** en el VPS de la cátedra, con la base cargada desde el propio contenedor, la URL pública declarada en `DEPLOY.md` y la evidencia de los casos D-03 y D-04, que C-08 no pudo producir porque requieren el servidor real. La imagen ya está construida y verificada (249 tests en verde), pero hasta hoy el proyecto no tiene procedimiento de despliegue ni datos de acceso.

El apply de este change depende de **datos del VPS que todavía no conocemos** (host, usuario y puerto SSH, método de acceso, puerto público asignado y `DATABASE_URL` de la base que provee la cátedra). Por eso el plan se divide en dos fases: todo lo que se puede dejar listo sin el servidor y, cuando lleguen los datos, la puesta en línea y la evidencia real. **No se inventa ningún dato de acceso ni se escribe evidencia ficticia.**

## What Changes

- **`DEPLOY.md` completo**: URL pública, día y hora del despliegue, comandos `docker build` y `docker run` completos (con el nombre del archivo de variables y **sin su contenido**), cambios hechos para que corra en el contenedor, procedimiento de actualización (build → `docker rm -f` → `docker run`) y la limitación de `create_all` sobre tablas existentes (DD-06).
- **Script de despliegue** `scripts/desplegar_vps.sh` (bash) parametrizado por variables de entorno, que arma el `docker run` con `--restart unless-stopped`, `--env-file` y `--add-host=host.docker.internal:host-gateway` cuando la base vive en el host; nunca imprime el archivo de variables ni la `DATABASE_URL`.
- **Script de verificación en el VPS** `scripts/verificar_despliegue.sh` que ejecuta, desde fuera del contenedor y con `curl`, `GET /health/ready`, `GET /libros/` y `POST /ventas/` (cuerpo del caso C-06) y escribe `evidencia/D-03-endpoints-publicos.txt`; además `docker rm -f` + el mismo `docker run` para `evidencia/D-04-restart.txt`, `docker logs` para `D-07` y `docker exec libreria id` para `D-06` en el servidor.
- **Plantillas de evidencia** de D-03 y D-04 con `ESTADO: PENDIENTE (C-09, requiere datos del VPS)`, el comando reproducible y el criterio de aceptación, sin salidas inventadas.
- **Selección y documentación del camino de build**: build **en el VPS** como opción principal (D-02 pide "servidor limpio"); `docker save` + `docker load` por `ssh` documentado como plan B.
- **Transferencia del código al VPS**: `git clone` si el servidor tiene git; si no, `rsync`/`scp` del árbol excluyendo `.venv`, `.git`, `.env`, `.env.docker`, `__pycache__` y `evidencia/`, o un `.tar.gz` equivalente. El `.dockerignore` sigue mandando en el contexto de build y **ningún secreto viaja**.
- **Archivo de variables del servidor** `libreria.env` (nombre definitivo sujeto a lo que fije la cátedra), con permisos `600`, fuera del repositorio y de la imagen, nunca en `.zip` ni en `DEPLOY.md`.
- **Base de datos**: si PostgreSQL corre en el host del VPS se usa `host.docker.internal` con `--add-host`; si la cátedra da otra dirección, se usa esa. `localhost` queda prohibido dentro del contenedor.
- **Carga inicial** con `docker exec libreria python -m app.seed` (C-05) y verificación de los datos del seed.
- **Pruebas estáticas nuevas** (pytest, sin VPS) que revisan los artefactos: `DEPLOY.md` con las secciones obligatorias y sin credenciales, los scripts con `127.0.0.1`/`localhost` correctos, `--env-file`, `--restart unless-stopped`, `--add-host` y la ausencia de secretos.
- **Sin cambios** en `app/`, en el contrato HTTP, en el esquema, en la imagen ni en `requirements.txt`: C-09 despliega exactamente lo que C-08 verificó.

## Capabilities

### New Capabilities

- `vps-deployment`: puesta en línea del contenedor en el VPS de la cátedra, con configuración por archivo de variables fuera del repositorio, carga inicial de datos, verificación desde fuera, reinicio sin pérdida de datos y documentación de despliegue y actualización.

### Modified Capabilities

Ninguna. `container-image`, `seed-data`, `health-checks` y `api-contracts` describen lo que la aplicación ya hace; el despliegue los **consume** sin cambiar sus requisitos.

## Impact

- **Archivos nuevos**: `scripts/desplegar_vps.sh`, `scripts/verificar_despliegue.sh`, `test/test_artefactos_despliegue.py`, `evidencia/D-03-endpoints-publicos.txt` y `evidencia/D-04-restart.txt` (plantillas con `PENDIENTE` hasta tener el VPS).
- **Archivos modificados**: `DEPLOY.md` (se completa con las secciones del servidor), `README.md` (enlace al despliegue), `CHANGES.md` (estado de C-09 al archivar).
- **Archivos que NO se tocan**: todo `app/`, `test/` funcional, `Dockerfile`, `.dockerignore`, `requirements.txt`, `env.example`.
- **Datos que se piden a la cátedra y quedan como `(TBD)` hasta recibirlos**: host/IP y puerto SSH, usuario SSH, método de acceso (clave o contraseña), puerto público asignado, host/puerto/base/usuario de PostgreSQL, si la base corre en el host del VPS o en otra máquina, y si el servidor ya tiene Docker y git instalados.
- **Riesgo de verificación**: sin los datos del VPS no se puede cerrar D-03, D-04 ni completar la URL y la fecha en `DEPLOY.md`. El change puede dejar todo lo demás listo y verificable en local; el cierre real ocurre cuando el servidor responde.
