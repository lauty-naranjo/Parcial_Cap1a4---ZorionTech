# Despliegue del contenedor

Este documento cubre la **imagen** (construirla, correrla, verificarla y cargar
datos) y el **despliegue en el VPS de la cátedra** (URL pública, archivo de
variables del servidor, actualización y evidencia de los casos D).

> **Estado**: desplegado y verificado el **2026-11-12**, reconstruido desde el
> commit final **`8d3e8b0`** (`main`). El servidor es un VPS
> compartido (EasyPanel + Docker Swarm + Traefik) con otros proyectos; este
> despliegue usa nombres propios (`libreria-zoriontech`,
> `libreria-zoriontech-db`, red `libreria-zoriontech-net`) para no colisionar
> con los contenedores de otros grupos. La base es un PostgreSQL 16 en un
> contenedor separado del servidor, con volumen propio: **no vive dentro de la
> imagen de la aplicación**. No se inventa ningún dato ni se escribe evidencia
> ficticia.

- Imagen base: `python:3.12-alpine` (medida por debajo de los 100 MB).
- La configuración entra **solo** por `--env-file`; no hay `ENV` ni `ARG` con
  cadenas de conexión dentro de la imagen.
- El proceso corre con el usuario `appuser` (uid 1000), no root.

## URL pública y fecha del despliegue

| Dato | Valor | Estado |
|---|---|---|
| URL pública | `http://46.202.151.202:8000` | verificado desde fuera del VPS |
| Día y hora del despliegue | `2026-11-12T17:26:00Z` | registrado |
| Reconstrucción final | `2026-11-12`, desde `main` (`8d3e8b0`) | verificado (`healthy`) |
| Método | `http`, sin TLS ni dominio propio | definitivo |
| Contenedor | `libreria-zoriontech`, puerto interno `8000` | verificado (`healthy`) |
| Base | `libreria-zoriontech-db` (postgres:16-alpine), volumen `libreria-zoriontech-pgdata` | verificado |
| Red | `libreria-zoriontech-net` | verificado |
| Archivo de variables | `/root/libreria-zoriontech.env` (permisos `600`) | verificado |

## Requisitos

- Docker 20.10 o superior (probado con Docker 29.7.2). `--add-host` con
  `host-gateway` exige 20.10+.
- Un PostgreSQL 16 accesible desde el contenedor. Si la base corre en el host
  del servidor, ver «La base no está en `localhost`».
- El repositorio completo en el directorio de trabajo (el `Dockerfile` usa el
  contexto `.`).

## Archivos de variables

Hay **dos archivos distintos** y ninguno se versiona, se hornea en la imagen ni
viaja en el `.zip`:

| Archivo | Dónde vive | Para qué |
|---|---|---|
| `.env.docker` | raíz del repositorio, solo en desarrollo local | probar la imagen en la máquina del operador |
| `libreria-zoriontech.env` | servidor, **fuera del repositorio** (`/root/libreria-zoriontech.env`) | configuración de producción |

### Archivo local `.env.docker` (desarrollo)

Se crea a partir de la plantilla `env.example`:

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@<HOST_BD>:<PUERTO_BD>/<NOMBRE_BD>
SQL_ECHO=false
```

- `DATABASE_URL` es obligatoria; si falta, el contenedor termina con código
  distinto de 0 (caso D-05).
- Si la contraseña tiene `@`, `:`, `/`, `#` u otro carácter especial, codificala
  con percent-encoding (`p@ss` → `p%40ss`).
- `SQL_ECHO=false` en despliegue; `true` solo para capturar consultas.
- `.env.docker` está en `.gitignore` y en `.dockerignore`.

### Archivo del servidor `libreria-zoriontech.env` (producción)

1. En el home del usuario que despliega, crear el archivo vacío con permisos
   `600`:

   ```bash
   cd ~
   install -m 600 /dev/null libreria-zoriontech.env
   ```

2. Completarlo con un editor (nunca con `echo` en el historial de la shell):

   ```env
   DATABASE_URL=postgresql+asyncpg://usuario:password@<HOST_BD>:<PUERTO_BD>/<NOMBRE_BD>
   SQL_ECHO=false
   ```

3. Verificar y reforzar los permisos: `ls -l libreria-zoriontech.env` debe
   mostrar `-rw-------`, y si el editor los cambió,
   `chmod 600 libreria-zoriontech.env`.

Reglas del archivo de variables del servidor:

- Vive **fuera del repositorio**, de la imagen y del `.zip`. Si `ARCHIVO_ENV`
  apunta dentro del repositorio, `scripts/desplegar_vps.sh` rechaza la ejecución.
- `scripts/desplegar_vps.sh` y `scripts/verificar_despliegue.sh` comprueban
  existencia y permisos `600`; si no se cumplen, terminan con error.
- El contenido **nunca se imprime**: Docker lo lee con `--env-file` y los
  scripts solo muestran el nombre del archivo. `DEPLOY.md`, `README.md` y
  `evidencia/` no contienen su usuario, contraseña ni host reales.

## Construcción

### En el VPS (camino principal)

El camino elegido es construir **en el servidor**, porque D-02 evalúa un
servidor limpio y evita transferir la imagen:

```bash
docker build -t libreria-zoriontech .
```

Las dependencias se instalan antes de copiar `app/`, así que un cambio de código
no reinstala `requirements.txt`. El build no incluye `.env`, `.env.docker`,
`.venv`, `.git`, `test/`, `evidencia/`, `knowledge-base/`, `docs/` ni
`openspec/` (ver `.dockerignore`).

### Plan B: transferir la imagen ya construida

Se usa solo si el VPS no puede construir por recursos o por falta de salida a
internet. Criterio para pasar al plan B: `docker build` falla en el servidor por
descarga de la base o de las wheels, o el servidor no tiene espacio suficiente.

En la máquina del operador (build local ya verificado):

```bash
docker save libreria-zoriontech | gzip -9 > libreria-zoriontech.tar.gz
scp libreria-zoriontech.tar.gz <VPS_USER>@<IP_VPS>:~/
```

En el VPS:

```bash
gunzip -c ~/libreria-zoriontech.tar.gz | docker load
docker images libreria-zoriontech
```

Variante en un solo paso, sin dejar el archivo en el servidor:

```bash
docker save libreria-zoriontech | gzip -9 | ssh <VPS_USER>@<IP_VPS> 'gunzip -c | docker load'
```

Comprimir el `.tar` es obligatorio: sin `gzip` el archivo suele superar el
límite de descarga de 100 MB. El camino realmente usado se anota en la sección
«Qué hizo falta para que corra en el contenedor».

## Transferencia del código al VPS

Orden de preferencia; en los tres casos el `.dockerignore` sigue gobernando el
contexto de build y **ningún secreto viaja**:

1. **`git clone`** (si el servidor tiene git y salida a la red):

   ```bash
   git clone <URL_DEL_REPOSITORIO> /opt/libreria-zoriontech
   ```

2. **`rsync`** (si hay `rsync`), excluyendo entorno, historial y secretos:

   ```bash
   rsync -az \
     --exclude .venv --exclude .git --exclude .env --exclude .env.docker \
     --exclude 'libreria*.env' --exclude __pycache__ --exclude evidencia \
     ./ <VPS_USER>@<IP_VPS>:/opt/libreria-zoriontech/
   ```

3. **`tar` + `scp`** (si no hay git ni `rsync`; es el camino usado en este
   despliegue):

   ```bash
   tar -czf libreria-zoriontech-codigo.tar.gz \
     --exclude .venv --exclude .git --exclude .env --exclude .env.docker \
     --exclude 'libreria*.env' --exclude __pycache__ --exclude evidencia .
   scp libreria-zoriontech-codigo.tar.gz <VPS_USER>@<IP_VPS>:~/
   # en el VPS:
   mkdir -p /opt/libreria-zoriontech
   tar -xzf ~/libreria-zoriontech-codigo.tar.gz -C /opt/libreria-zoriontech
   ```

`evidencia/` no hace falta para construir: se regenera en el VPS con los
scripts. Si se quiere comparar, se copia al final con `scp` de archivos
puntuales, no del directorio completo. El archivo `libreria-zoriontech.env`
**no** se transfiere con el código: se crea en el servidor (ver arriba).

## Ejecución

### Verificación local (máquina del operador)

La imagen y el contenedor locales se llaman `libreria-local`, **nunca**
`libreria`: ese nombre, en el VPS, es el contenedor de otro grupo.

```bash
docker build -t libreria-local .
docker run -d --name libreria-local -p 8000:8000 --restart unless-stopped \
  --env-file .env.docker libreria-local
```

### En el VPS

Con el archivo de variables del servidor ya creado y la base en su contenedor y
red:

```bash
# 1. red y base (una sola vez; el volumen conserva los datos)
docker network create libreria-zoriontech-net
docker volume create libreria-zoriontech-pgdata
docker run -d --name libreria-zoriontech-db --network libreria-zoriontech-net \
  --restart unless-stopped \
  -e POSTGRES_USER=libreria -e POSTGRES_DB=libreria -e POSTGRES_PASSWORD=<PASSWORD_BD> \
  -v libreria-zoriontech-pgdata:/var/lib/postgresql/data postgres:16-alpine

# 2. aplicación
docker run -d --name libreria-zoriontech --network libreria-zoriontech-net \
  -p 8000:8000 --restart unless-stopped \
  --env-file /root/libreria-zoriontech.env libreria-zoriontech
```

En `DATABASE_URL` el host de la base es el **nombre del contenedor de la base**
(`libreria-zoriontech-db`), porque ambos comparten la red de Docker. No se usa
`host.docker.internal` porque PostgreSQL no corre en el host del servidor.

| Flag | Efecto |
|---|---|
| `-p 8000:8000` | Publica el puerto asignado hacia el 8000 del contenedor |
| `--restart unless-stopped` | Docker vuelve a levantar el contenedor si falla o si el VPS reinicia |
| `--env-file /root/libreria-zoriontech.env` | Inyecta `DATABASE_URL` y `SQL_ECHO` sin hornearlas en la imagen |
| `--network libreria-zoriontech-net` | Aísla app y base del resto de los proyectos del servidor |

El script hace lo mismo, validando antes los datos:

```bash
IMAGEN=libreria-zoriontech CONTENEDOR=libreria-zoriontech \
RED=libreria-zoriontech-net PUERTO_PUBLICO=8000 \
HOST_BD=libreria-zoriontech-db NOMBRE_BD=libreria USUARIO_BD=libreria \
ARCHIVO_ENV=/root/libreria-zoriontech.env PASSWORD_BD=<PASSWORD_BD> \
IP_VPS=46.202.151.202 bash scripts/desplegar_vps.sh
```

Falla nombrando la variable que falte (incluidas `IMAGEN` y `CONTENEDOR`, que no
tienen valor por defecto), se niega a usar `libreria`/`libreria-db`, rechaza
`localhost`/`127.0.0.1` como host de base, exige permisos `600` en el archivo y
espera el estado `healthy` con `docker inspect`. `DRY_RUN=1` muestra los
comandos sin ejecutarlos.

### La base no está en `localhost`

Dentro del contenedor, `localhost` es el propio contenedor y **está prohibido**
como host de la base: `/health/ready` nunca llegaría a PostgreSQL. En este
despliegue el host es `libreria-zoriontech-db`, el nombre del contenedor de la
base en `libreria-zoriontech-net` (ver «Ejecución → En el VPS»).

Solo si PostgreSQL corriera en el **host** del servidor, el `docker run` sería:

```bash
docker run -d --name libreria-zoriontech --network libreria-zoriontech-net \
  -p 8000:8000 --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  --env-file /root/libreria-zoriontech.env libreria-zoriontech
```

y `DATABASE_URL` usaría `host.docker.internal`. Si la cátedra provee otra
dirección (otra máquina o un servicio gestionado), se usa esa dirección y
**no** se agrega `--add-host`.

## Verificación del healthcheck

La imagen declara `HEALTHCHECK` contra `GET /health/ready` en
`http://127.0.0.1:8000` (nunca `localhost`: en Alpine resuelve primero IPv6 y
uvicorn escucha IPv4).

```bash
docker ps                                                     # estado: healthy
docker exec libreria-zoriontech wget -qO- http://127.0.0.1:8000/health/ready
# {"estado": "listo", "base": "ok"}
```

Si la base no responde, `/health/ready` devuelve 503 y el contenedor queda
`unhealthy` aunque el proceso siga vivo: es el comportamiento buscado.

## Seed dentro del contenedor

El módulo de datos iniciales viaja dentro de `app/` (`app/seed.py`), por eso no
se copia `scripts/` a la imagen:

```bash
docker exec libreria-zoriontech python -m app.seed
```

Es idempotente y deja editorial y género id 1, cuatro autores, cuatro libros,
dos clientes y la venta id 2 con total `77000.00`. No imprime la URL ni
credenciales. Re-ejecutarlo no duplica filas.

## Actualización

El procedimiento reconstruye la imagen, elimina **solo** el contenedor de este
proyecto y lo vuelve a correr con el mismo `docker run` de «Ejecución → En el
VPS»; la red, la base y el volumen no se recrean:

```bash
docker build -t libreria-zoriontech .
docker rm -f libreria-zoriontech
docker run -d --name libreria-zoriontech --network libreria-zoriontech-net \
  -p 8000:8000 --restart unless-stopped \
  --env-file /root/libreria-zoriontech.env libreria-zoriontech
docker ps --filter name=libreria-zoriontech
docker logs libreria-zoriontech
```

Los datos no se pierden: viven en `libreria-zoriontech-db` (volumen
`libreria-zoriontech-pgdata`), no en el contenedor de la aplicación.

> **No elimines el contenedor `libreria` ni uses la imagen `libreria`**: ese
> contenedor (puerto 8001) pertenece a otro grupo del servidor y debe quedar
> intacto. Este despliegue siempre usa `libreria-zoriontech`.

Rollback: `docker rm -f libreria-zoriontech` deja el servicio abajo pero **no
toca la base**; para volver a la versión anterior se reconstruye el commit
previo y se repite el mismo `docker run` (no hay migraciones que revertir).

## Verificación en el VPS y evidencia

El orden es obligatorio: **D-03 → D-07 → D-04**, porque D-04 reinicia el
contenedor y reiniciar antes borra los logs de la venta que necesita D-07.

1. **D-03 — desde fuera del VPS** (máquina del operador). Se niega a correr
   contra `127.0.0.1`/`localhost`: una prueba local no es D-03.

   ```bash
   URL_PUBLICA=http://46.202.151.202:8000 bash scripts/verificar_publico.sh
   ```

   Comprueba `GET /health/ready` (200), `GET /libros/` (200 con cuatro libros) y
   `POST /ventas/` con el cuerpo del caso C-06 (201, precios copiados y total
   `77000.00`), y escribe `evidencia/D-03-endpoints-publicos.txt` con la salida
   real.

2. **D-07 — en el VPS**. Después de la venta:

   ```bash
   docker logs libreria-zoriontech
   CONTENEDOR=libreria-zoriontech IMAGEN=libreria-zoriontech \
     RED=libreria-zoriontech-net bash scripts/verificar_despliegue.sh
   ```

   El script falla si no encuentra el aviso del comprobante. La salida se pega
   en la sección «VPS» de `evidencia/D-07-background.txt`.

3. **D-04 — en el VPS**, al final de la ventana:

   ```bash
   CONFIRMAR_REINICIO=1 CONTENEDOR=libreria-zoriontech \
     IMAGEN=libreria-zoriontech RED=libreria-zoriontech-net \
     ARCHIVO_ENV=/root/libreria-zoriontech.env PUERTO_PUBLICO=8000 \
     HOST_BD=libreria-zoriontech-db bash scripts/verificar_despliegue.sh
   ```

   Sin `CONFIRMAR_REINICIO=1` el script **no reinicia**. Con la confirmación
   hace `docker rm -f libreria-zoriontech` + el mismo `docker run` (con
   `--network libreria-zoriontech-net`), espera `healthy`, comprueba
   `/health/ready` y `/libros/` y escribe `evidencia/D-04-restart.txt`.

**Regeneración del resto de la evidencia**: D-01, D-05 y D-06 quedaron
verificados en local con Docker 29.7.2 y se conservan así (miden la imagen, no
el servidor). Si se quiere repetir en el VPS, usar nombres propios para no tocar
producción:

```bash
CONTENEDOR=libreria-zoriontech-verif PUERTO=18000 bash scripts/verificar_imagen.sh
```

D-02 se complementa con el build real en el VPS (`BUILD_EXIT=0`, 264 MB) y D-06
también queda registrado por `scripts/verificar_despliegue.sh`
(`docker exec libreria-zoriontech id`).

## Qué hizo falta para que corra en el contenedor

- `Dockerfile` con `python:3.12-alpine`, usuario `appuser` (uid 1000) y
  `HEALTHCHECK` propio; sin `COPY scripts`, porque el seed vive en `app/seed.py`
  desde C-05.
- `.dockerignore` que excluye entornos virtuales, `.git`, pruebas y
  documentación, y también `.env`, `.env.docker`, `libreria.env` y
  `libreria-zoriontech.env` (los archivos con credenciales).
- `.gitignore` con `.env.docker`, `.env`, `libreria.env` y
  `libreria-zoriontech.env`; el archivo del servidor se crea fuera del
  repositorio.
- Ningún cambio en `app/`, en el contrato HTTP ni en `requirements.txt`.
- Para la verificación local de C-08 se usó un PostgreSQL 16 efímero en una red
  de Docker (`postgres:16-alpine`); ese contenedor se eliminó al terminar.
- En el VPS (2026-11-12):
  - El servidor es **compartido** (EasyPanel + Docker Swarm + Traefik) y ya
    tenía un contenedor `libreria` en el puerto 8001 y una `libreria-db` de
    otro grupo. Se dejaron intactos: el despliegue usa nombres propios.
  - El puerto **8000** estaba libre y no hay `ufw` activo; se publicó ahí.
  - PostgreSQL **no** está instalado en el host ni activo como servicio: las
    bases viven en contenedores. Se creó `libreria-zoriontech-db`
    (`postgres:16-alpine`) con volumen `libreria-zoriontech-pgdata`.
  - El código se transfirió con `tar` + `scp` (el VPS tiene git, pero la
    transferencia evita depender de credenciales del repositorio).
  - `docker build -t libreria-zoriontech .` en el servidor: `BUILD_EXIT=0`,
    imagen de 264 MB (1 CPU, Alpine resolvió wheels musllinux).
  - `create_all` sobre la base vacía creó el esquema en el primer arranque; el
    seed se ejecutó con `docker exec libreria-zoriontech python -m app.seed`.

## Limitación de `create_all` (DD-06)

Al arrancar, el `lifespan` ejecuta `SQLModel.metadata.create_all`. Eso **crea
las tablas faltantes y no altera las existentes**: no hay migraciones, no hay
`ALTER TABLE` automático y no se borra nada. Consecuencias:

- Una base vacía queda lista con el esquema completo en el primer arranque.
- Un cambio de esquema en el código **no** se aplica solo: exige recrear la base
  o ejecutar el `ALTER` a mano.
- Si la base asignada ya tiene tablas con otro esquema, `create_all` no las
  corrige; hay que pedir una base limpia a la cátedra. Nunca se hace `DROP` por
  cuenta propia.

## Evidencia

| Caso | Archivo | Estado |
|---|---|---|
| D-01 tamaño de la imagen base | `evidencia/D-01-docker-images.txt` | **verificado en el VPS 2026-11-12** (74.8 MB) y en local |
| D-02 build, run, `docker ps` y `docker logs` | `evidencia/D-02-build-run-ps.txt` | **verificado en el VPS 2026-11-12** (`BUILD_EXIT=0`, 9 tablas) y en local |
| D-03 endpoints públicos desde fuera | `evidencia/D-03-endpoints-publicos.txt` | **verificado en el VPS 2026-11-12** |
| D-04 reinicio con datos intactos | `evidencia/D-04-restart.txt` | **verificado en el VPS 2026-11-12** sobre `main` (`8d3e8b0`) |
| D-05 contenedor sin `DATABASE_URL` | `evidencia/D-05-sin-database-url.txt` | **verificado en el VPS 2026-11-12** (exit 3) y en local |
| D-06 usuario no root | `evidencia/D-06-usuario.txt` | **verificado en el VPS 2026-11-12** (`uid=1000`) y en local |
| D-07 aviso del comprobante en logs | `evidencia/D-07-background.txt` | **verificado en local y en el VPS 2026-11-12** |

Procedimiento reproducible en Linux/WSL:

```bash
bash scripts/verificar_imagen.sh
# o con otro archivo de variables:
ENV_FILE=/ruta/al/archivo.env bash scripts/verificar_imagen.sh
```

Ningún script imprime el contenido del archivo de variables. La evidencia de
C-08 se capturó en el entorno de desarrollo con Docker 29.7.2; C-09 repite el
procedimiento en el VPS con la base real y completa D-03 y D-04.

## Datos del despliegue

| Parámetro | Valor |
|---|---|
| Host / IP del VPS | `46.202.151.202` |
| Puerto SSH | `22` |
| Usuario SSH | `root` (acceso por clave, sin contraseña) |
| Sistema | Ubuntu 24.04.4 LTS |
| Docker | 29.7.1 |
| Puerto público | `8000` |
| URL pública | `http://46.202.151.202:8000` |
| Contenedor de la app | `libreria-zoriontech` |
| Contenedor de la base | `libreria-zoriontech-db` (`postgres:16-alpine`) |
| Volumen de la base | `libreria-zoriontech-pgdata` |
| Red | `libreria-zoriontech-net` |
| Archivo de variables | `/root/libreria-zoriontech.env` (permisos `600`) |
| Código en el servidor | `/opt/libreria-zoriontech` |

La contraseña de PostgreSQL vive **solo** en `/root/libreria-zoriontech.env`.
No se versiona, no se imprime y no aparece en este documento, en la imagen ni en
la evidencia.

> **Servidor compartido**: el VPS aloja otros proyectos (EasyPanel, Docker
> Swarm, Traefik) y ya tenía un contenedor `libreria` en el puerto 8001 y una
> `libreria-db` de otro grupo. Este despliegue no los modificó: usa nombres
> propios, red propia y volumen propio.
