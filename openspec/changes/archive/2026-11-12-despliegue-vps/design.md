# Design

## Context

Ver `proposal.md` §Why. Estado actual que condiciona el diseño:

- **C-08 archivado**: `Dockerfile` Alpine con `appuser` (uid 1000), `HEALTHCHECK` contra `http://127.0.0.1:8000/health/ready`, `CMD` en `0.0.0.0:8000`, `.dockerignore` que excluye `.env`, `.env.docker`, `.venv`, `.git`, `test`, `evidencia`, `knowledge-base`, `docs` y `openspec`. El build y el run locales se verificaron con Docker 29.7.2 y un PostgreSQL 16 efímero.
- **C-05 archivado**: `app/seed.py` idempotente, invocable con `python -m app.seed`; deja editorial y género id 1, cuatro autores, cuatro libros (1 Rayuela 25000.00, 4 Respiración artificial 27000.00), dos clientes (2 Tomás Ríos) y la venta 2 con total 77000.00.
- **`scripts/verificar_imagen.sh`** ya produce D-01, D-02, D-05 y D-06 en `evidencia/`; acepta `ENV_FILE`, `IMAGEN`, `CONTENEDOR`, `PUERTO`, `DOCKER_NETWORK` y `IMAGEN_BASE` por entorno y nunca imprime el archivo de variables.
- **`DEPLOY.md`** ya cubre la imagen: requisitos, archivo de variables local `.env.docker`, build, run, «la base no está en `localhost`», healthcheck, seed, actualización y la tabla de evidencia con D-03/D-04 pendientes de C-09.
- **Datos del VPS desconocidos**: host/IP, puerto y usuario SSH, método de acceso, puerto público y `DATABASE_URL` los provee la cátedra. Hoy no hay ningún valor real en el repositorio y este change no debe introducirlo.
- **Suite**: 249 tests en verde; ninguno toca Docker ni red externa.
- **Restricción de entrega**: ni el repositorio, ni la imagen, ni el `.zip` pueden contener credenciales (RN-G-04, regla dura D.11).

## Goals / Non-Goals

**Goals:**

- Dejar el despliegue **completamente preparado y verificable en local** sin depender de los datos del VPS: `DEPLOY.md` completo, scripts parametrizados, plantillas de evidencia y tests estáticos.
- Reducir la fase con servidor a una secuencia corta y repetible de comandos que no improvise nada.
- Garantizar que ningún secreto viaje al repositorio, a la imagen, al `.zip` ni a la documentación.
- Producir D-03 y D-04 con salida real del VPS cuando existan los datos, sin inventar resultados.

**Non-Goals:**

- No se modifica `app/`, el contrato HTTP, el esquema, el `Dockerfile`, `.dockerignore` ni `requirements.txt`.
- No se agrega Docker Compose, Nginx, TLS, dominio propio, CI/CD ni monitoreo: la consigna pide una imagen y `docker run`.
- No se automatiza el acceso SSH desde los scripts: se ejecutan **en** el VPS (o desde la máquina del operador para D-03) con los datos que provee la cátedra.
- No se crea ni se migra la base del VPS: se usa la que entrega la cátedra y `create_all` crea solo las tablas faltantes (DD-06).

## Decisions

### 1. Camino de build: build en el VPS, con transferencia de imagen como plan B

El camino principal es `docker build -t libreria .` **en el servidor**, porque D-02 evalúa un «servidor limpio» y así se evita mover la imagen. El plan B (`docker save libreria | gzip | ssh ... 'docker load'`) queda documentado en `DEPLOY.md` para el caso de que el VPS no tenga recursos para construir o no se pueda llevar el código.

**Alternativa considerada**: build local + `docker save`/`docker load` como camino principal. Descartada: el artefacto comprimido puede acercarse o superar el límite de 100 MB de descarga y no demuestra el build en el servidor. Se conserva como plan B.

### 2. Transferencia del código: `git clone`, con `rsync`/`.tar.gz` como alternativa

Orden de preferencia:

1. `git clone <repo> libreria` en el VPS, si tiene git y salida a la red.
2. `rsync -az --exclude .venv --exclude .git --exclude .env --exclude .env.docker --exclude __pycache__ --exclude evidencia ./ usuario@host:~/libreria/`, si hay `rsync`.
3. `tar` local excluyendo las mismas rutas + `scp` + `tar -xzf` en el servidor.

En los tres casos el `.dockerignore` sigue gobernando el contexto de build. `evidencia/` se excluye del envío porque no hace falta para construir y se regenera en el VPS; si se prefiere conservarla, se copia al final solo para comparar.

**Alternativa considerada**: comprimir la raíz completa con `.git` y `.venv`. Descartada: sube cientos de MB y arrastra historial y entorno local.

### 3. Archivo de variables del servidor: `libreria.env`, permisos `600`, fuera del repositorio

- Nombre por defecto `libreria.env`; el nombre real puede cambiar si la cátedra lo fija. Los scripts lo reciben por `ENV_FILE` y **no** asumen contenido.
- Vive en el home del usuario que despliega (por ejemplo `~/libreria.env`) o en `/etc/libreria/libreria.env`, **nunca** dentro del directorio del repositorio, de la imagen ni del `.zip`.
- Se crea con `install -m 600 /dev/null libreria.env` y se completa con un editor; `ls -l` debe mostrar `-rw-------`.
- Contiene exactamente `DATABASE_URL=postgresql+asyncpg://...` y `SQL_ECHO=false`. Si la contraseña tiene `@`, `:`, `/` o `#`, se codifica con percent-encoding.
- `DEPLOY.md` menciona el **nombre** del archivo y nunca su contenido; la evidencia tampoco lo imprime.

**Alternativa considerada**: reutilizar `.env.docker` en el VPS. Descartada: mezcla el archivo local de desarrollo con el de producción y hace más fácil versionarlo por error.

### 4. Red: `host.docker.internal` si la base está en el host; `localhost` prohibido

- Si PostgreSQL corre en el host del VPS: `docker run` con `--add-host=host.docker.internal:host-gateway` y `DATABASE_URL` con `host.docker.internal`. Requiere Docker 20.10 o superior en el servidor.
- Si la cátedra da otra dirección (otra máquina o un servicio gestionado): se usa esa dirección y **no** se agrega `--add-host`.
- `localhost` y `127.0.0.1` dentro de `DATABASE_URL` quedan prohibidos: apuntan al propio contenedor. Un test estático verifica que los scripts y `DEPLOY.md` no los usen como host de base.

**Alternativa considerada**: `--network host`. Descartada: publica todos los puertos del contenedor y cambia el modelo de aislamiento; además no es lo que pide la consigna.

### 5. Puerto público: el asignado por la cátedra, con 8000 como valor de ejemplo

`PUERTO_PUBLICO` es obligatorio en el script de despliegue; si no se pasa, el script falla con un mensaje que lo nombra en lugar de asumir un valor. `DEPLOY.md` escribe `<puerto>` en los comandos y, una vez conocido, el número real en la sección de URL. El 8000 solo aparece como puerto **interno** del contenedor y como ejemplo local.

### 6. Reinicio automático: `--restart unless-stopped`

Si el VPS se reinicia o la base tarda en levantar, Docker vuelve a arrancar el contenedor; `create_all` corre de nuevo y solo crea lo que falte. Es el flag que pide la consigna y el que hace que el despliegue siga en línea sin intervención.

### 7. Verificación en dos planos: desde afuera y desde el VPS

- **Desde fuera** (`scripts/verificar_publico.sh`, se ejecuta en la máquina del operador): `curl` contra `URL_PUBLICA` para `GET /health/ready`, `GET /libros/` y `POST /ventas/` con el cuerpo del caso C-06; guarda códigos, cuerpos y la comprobación de `"total":"77000.00"` y de los precios copiados en `evidencia/D-03-endpoints-publicos.txt`. Se niega a correr contra `127.0.0.1`/`localhost` para no confundir una prueba local con D-03.
- **Desde el VPS** (`scripts/verificar_despliegue.sh`): `docker ps` (estado `healthy` y puerto publicado), `docker exec libreria id` (D-06), `docker logs libreria` para el aviso del comprobante (D-07) y el ciclo `docker rm -f` + mismo `docker run` para D-04, comprobando después que `/health/ready` vuelve a 200 y que `GET /libros/` conserva los datos.

El orden importa: D-03 crea la venta, D-07 lee sus logs, y **después** D-04 reinicia (reiniciar antes borra los logs de la venta).

**Alternativa considerada**: un solo script que haga todo desde la máquina del operador por SSH. Descartada: obliga a manejar claves SSH y `ProxyCommand` en el script, y difumina qué se ejecutó en cada lado.

### 8. Evidencia: real o pendiente, nunca simulada

- `evidencia/D-03-endpoints-publicos.txt` y `D-04-restart.txt` se entregan como plantillas con `ESTADO: PENDIENTE (C-09, requiere datos del VPS)`, el comando exacto y el criterio. Al ejecutar los scripts se sobreescriben con `ESTADO: VERIFICADO (<fecha UTC>)`, el entorno y la salida real.
- D-01, D-02, D-05 y D-06 se regeneran en el VPS con `scripts/verificar_imagen.sh` durante la ventana inicial (antes de dejar la producción arriba), usando `CONTENEDOR=libreria` y `PUERTO=<puerto>`; el script ya escribe en `evidencia/` del directorio donde se ejecuta. Si ya hay un contenedor en producción, se corre con `CONTENEDOR=libreria-verif` y `PUERTO=18000` para no interrumpirlo, y se documenta la diferencia de puerto.
- D-07 se conserva el archivo local y se agrega una sección del VPS con los logs reales; si el VPS no se puede usar, se documenta que el caso ya quedó verificado en el contenedor local de C-08.
- Copiar la evidencia del VPS al repo local con `scp` de los archivos puntuales, no del directorio completo.

**Alternativa considerada**: dejar la evidencia local de C-08 y no repetir nada en el VPS. Descartada: D-02 y D-03 pierden valor si no son del servidor; se permite conservarlas solo como respaldo y marcando el entorno.

### 9. `DEPLOY.md`: secciones exactas y sin secretos

Se completa el documento existente con:

1. URL pública (IP y puerto, o dominio si lo hubiera) y método (`http`, sin TLS).
2. Día y hora del despliegue (zona horaria explícita).
3. Comandos completos de `docker build` y `docker run`, con `--env-file libreria.env`, `--restart unless-stopped`, `-p <puerto>:8000` y `--add-host` cuando corresponda; sin el contenido del archivo.
4. Cambios hechos para que corra en el contenedor (los de C-08 más lo que aparezca en el VPS: por ejemplo `--add-host`, firewall o `create_all` sobre base vacía).
5. Procedimiento de actualización: build → `docker rm -f libreria` → `docker run` → `docker ps`; datos intactos porque la base no vive en el contenedor.
6. Limitación de `create_all` (DD-06): no altera tablas existentes.
7. Tabla de evidencia D-01…D-07 con fecha y entorno.

**Alternativa considerada**: un `DEPLOY.md` aparte solo para el VPS. Descartada: la checklist de C-11 revisa un único `DEPLOY.md` con todo.

### 10. Parámetros del servidor como `(TBD)` explícitos

Ningún valor real se escribe hasta recibirlo. La tabla siguiente es la lista de datos a pedir y el lugar donde se usan.

| Parámetro | Variable | Dónde se usa | Estado |
|---|---|---|---|
| Host o IP del VPS | `VPS_HOST` | transferencia, `DEPLOY.md` (URL) | `(TBD)` |
| Puerto SSH | `VPS_SSH_PORT` | transferencia | `(TBD)` |
| Usuario SSH | `VPS_USER` | transferencia | `(TBD)` |
| Método de acceso | — | clave o contraseña; define los comandos | `(TBD)` |
| Puerto público asignado | `PUERTO_PUBLICO` | `docker run -p`, URL | `(TBD)` |
| Host de PostgreSQL | `DB_HOST` | `DATABASE_URL` | `(TBD)` |
| Puerto de PostgreSQL | `DB_PORT` | `DATABASE_URL` | `(TBD)` |
| Nombre de la base | `DB_NAME` | `DATABASE_URL` | `(TBD)` |
| Usuario y contraseña de la base | `DB_USER` / `DB_PASSWORD` | `DATABASE_URL` | `(TBD)` |
| ¿La base está en el host del VPS? | — | decide `--add-host` | `(TBD)` |
| ¿El VPS ya tiene Docker? | — | build en el VPS o instalación | `(TBD)` |
| ¿El VPS tiene git? | — | `git clone` o `rsync`/`scp` | `(TBD)` |

Los scripts fallan con un mensaje que nombra la variable faltante; no hay valores por defecto para host, usuario, puerto SSH ni base.

## Fases del apply

**Fase 1 — sin el VPS (todo verificable en local):**

1. Completar `DEPLOY.md` con las secciones del servidor usando marcadores `<...>` donde falten datos.
2. Crear `scripts/desplegar_vps.sh`: valida `ENV_FILE` y `PUERTO_PUBLICO`, construye la imagen, detecta `DB_HOST=host.docker.internal` para agregar `--add-host`, hace `docker rm -f libreria` si existe y ejecuta el `docker run` con `--restart unless-stopped`; nunca imprime el archivo de variables.
3. Crear `scripts/verificar_despliegue.sh` (en el VPS) y `scripts/verificar_publico.sh` (desde fuera).
4. Escribir las plantillas `PENDIENTE` de D-03 y D-04.
5. Agregar `test/test_artefactos_despliegue.py`: `DEPLOY.md` con las siete secciones y sin `postgresql+asyncpg://` con credenciales, `--env-file`, `--restart unless-stopped`, `--add-host` condicionado, scripts sin `localhost` como host de base, plantillas con `PENDIENTE` y sin salidas inventadas.
6. Correr la suite completa y `openspec validate --strict despliegue-vps`.

**Fase 2 — con los datos del VPS (governance ALTO: confirmar antes de tocar el servidor):**

1. Registrar los datos en un lugar privado (no en el repo) y crear `libreria.env` con `600`.
2. Transferir el código (git clone o rsync/tar) y confirmar `docker --version` en el VPS.
3. Ejecutar `scripts/verificar_imagen.sh` en el VPS (build limpio, D-01/D-02/D-05/D-06 reales) y copiar la evidencia.
4. Ejecutar `scripts/desplegar_vps.sh` con el puerto y el archivo de variables reales.
5. `docker exec libreria python -m app.seed`.
6. Desde fuera: `scripts/verificar_publico.sh` con la URL pública (D-03).
7. En el VPS: `scripts/verificar_despliegue.sh` para D-06, D-07 y D-04, en ese orden.
8. Completar `DEPLOY.md` con URL, fecha y hora reales; dejar el contenedor en línea.

## Casos D en el VPS

| Caso | Dónde se ejecuta | Verificación | Evidencia |
|---|---|---|---|
| D-01 | VPS | `docker images` con base <100 MB | `D-01-docker-images.txt` regenerado |
| D-02 | VPS | build, run, `docker ps` healthy, logs con tablas creadas | `D-02-build-run-ps.txt` regenerado |
| D-03 | Fuera del VPS | 200 / 200 con seed / 201 total `77000.00` | `D-03-endpoints-publicos.txt` |
| D-04 | VPS | `docker rm -f` + run → healthy y datos intactos | `D-04-restart.txt` |
| D-05 | VPS | imagen sin `DATABASE_URL` termina ≠ 0 | `D-05-sin-database-url.txt` regenerado |
| D-06 | VPS | `docker exec libreria id` ≠ root | `D-06-usuario.txt` regenerado |
| D-07 | VPS | `docker logs` con el aviso después de la respuesta | `D-07-background.txt` + sección del VPS |

## Risks / Trade-offs

- **Base del VPS vacía o ya poblada** → `create_all` crea tablas faltantes y el seed es idempotente; si la base asignada ya tiene tablas con otro esquema, `create_all` no las altera y hay que pedir una base limpia a la cátedra. Nunca se hace `DROP` por cuenta propia.
- **Firewall o puerto cerrado** → el contenedor queda `healthy` en el VPS pero la URL no responde desde afuera. Mitigación: probar `GET /health/ready` desde el operador y revisar el firewall/security group antes de dar el despliegue por cerrado; anotarlo en `DEPLOY.md`.
- **Sin DNS ni dominio** → se declara `http://<IP>:<puerto>`. Si la cátedra exige dominio, se resuelve en su panel; no se inventa uno.
- **VPS sin salida a internet** → `docker build` no puede descargar la base ni las wheels. Mitigación: plan B con `docker save`/`docker load`; si la base tampoco está, pedirla o pedir acceso a un mirror.
- **Límite de 100 MB al transferir la imagen** → el `.tar` de `docker save` suele superar el tamaño de la imagen. Mitigación: preferir build en el VPS y, si se usa el plan B, comprimir con `gzip -9` y verificar el tamaño antes de subir.
- **`--env-file` con `postgresql+asyncpg://` mal formado o contraseña sin percent-encoding** → el arranque falla; `docker logs` muestra el error de configuración sin la URL completa. Mitigación: validar la forma de la URL antes de reiniciar y documentar el percent-encoding.
- **`--restart unless-stopped` con configuración inválida** → Docker reintenta en bucle. Mitigación: revisar `docker ps` (restart count) y `docker logs` antes de dejar el despliegue; no se considera terminado hasta ver `healthy`.
- **Dos archivos de variables (`libreria.env` en el VPS y `.env.docker` local)** → confusión. Mitigación: nombres distintos, `DEPLOY.md` explica cuál es cuál y ambos quedan fuera del repo y del `.zip`.
- **Scripts de verificación que reinician producción** → D-04 implica `docker rm -f`. Mitigación: se ejecuta en la ventana de despliegue, se documenta la interrupción breve y se verifica que los datos siguen; nunca en horario de corrección.
- **`verificar_imagen.sh` sobreescribe evidencia local** → Mitigación: se ejecuta en el VPS y se copian los archivos puntuales; si se corre en producción, usar `CONTENEDOR=libreria-verif` y `PUERTO=18000`.
- **La corrección ocurre con el VPS caído** → el criterio se evalúa solo por `DEPLOY.md` y `evidencia/`; por eso la fase 1 deja todo completo y las plantillas nunca contienen datos falsos.

## Migration Plan

1. **Apply fase 1**: completar `DEPLOY.md`, crear los tres scripts, las plantillas de D-03/D-04 y el test de artefactos; actualizar `README.md` y `CHANGES.md`. Suite y `openspec validate --strict despliegue-vps` en verde.
2. **Apply fase 2**: con los datos de la cátedra, desplegar, sembrar, verificar y completar la evidencia y `DEPLOY.md` (URL y fecha).
3. **Rollback**: `docker rm -f libreria` deja el servidor sin servicio pero **sin tocar la base**; volver a la imagen anterior es `docker run` de la etiqueta previa (si se etiquetó) o rebuild del commit anterior. No hay migraciones ni cambios de esquema que revertir. Los archivos nuevos (scripts, tests, plantillas) se pueden borrar sin afectar la aplicación.

## Open Questions

- Nombre definitivo del archivo de variables y si la cátedra fija un puerto concreto: se resuelve al recibir los datos; los scripts ya lo reciben por parámetro y `DEPLOY.md` usa marcadores mientras tanto.
- Si el VPS permite construir (recursos y salida a internet) o si hay que usar el plan B: se decide al probar `docker build` en el servidor; ambos caminos quedan documentados.
- Si la base del VPS está vacía o ya contiene tablas de otra entrega: se verifica con `\dt` o un `SELECT 1` antes del seed; no cambia el diseño.

## UI Mockups

`Decision: no (project policy)` — `visual_design.mode` es `off` y este change no tiene interfaz.
