# Spec Delta

## Purpose

Define cómo la API se empaqueta en una imagen Docker reproducible, sin secretos y con usuario no root, y cómo se verifica su arranque, su salud y su configuración por entorno.

## ADDED Requirements

### Requirement: Base Alpine dentro del límite

La imagen SHALL construirse a partir de `python:3.12-alpine`. La imagen base SHALL quedar por debajo de 100 MB según `docker images`, y la imagen del proyecto MAY superar ese límite por sus dependencias.

#### Scenario: Tamaño de la imagen base

- **WHEN** se ejecuta `docker images` después del build
- **THEN** la entrada de `python:3.12-alpine` figura por debajo de 100 MB y el `Dockerfile` parte de esa referencia

#### Scenario: Build reproducible en un servidor limpio

- **WHEN** se ejecuta `docker build -t libreria .` sobre un checkout sin imágenes previas
- **THEN** el build termina con código 0 e instala todas las dependencias de `requirements.txt` sin compilador

### Requirement: Capas con dependencias antes del código

El `Dockerfile` SHALL copiar `requirements.txt` e instalar las dependencias antes de copiar el código de la aplicación, usando `pip install --no-cache-dir`. Un cambio que solo toque `app/` MUST NOT reinstalar las dependencias.

#### Scenario: Rebuild tras cambio de código

- **WHEN** se modifica un archivo bajo `app/` y se vuelve a construir la imagen con la caché disponible
- **THEN** la capa de `pip install` sale de caché y el build no reinstala las dependencias

### Requirement: Proceso sin privilegios

El contenedor SHALL ejecutar la aplicación con un usuario sin privilegios creado en la imagen, con uid 1000. `docker exec libreria id` MUST NOT reportar `uid=0`.

#### Scenario: Usuario del proceso

- **WHEN** se ejecuta `docker exec libreria id`
- **THEN** la salida muestra un usuario cuyo uid es 1000 y no es root

### Requirement: Servicio accesible por el puerto publicado

El proceso SHALL escuchar en `0.0.0.0:8000` y MUST NOT escuchar solo en `127.0.0.1`, de modo que el puerto publicado con `-p <puerto>:8000` responda desde fuera del contenedor.

#### Scenario: Acceso desde el host

- **WHEN** el contenedor corre con `-p 8000:8000` y se solicita `GET /health/live` contra el puerto publicado del host
- **THEN** la respuesta es 200 con `{"estado": "vivo"}`

### Requirement: Imagen y contexto de build sin secretos

La imagen MUST NOT contener `.env`, `.venv`, `.git`, `__pycache__`, `*.pyc` ni cadenas de conexión. El `.dockerignore` SHALL excluir esos elementos y también `knowledge-base`, `docs`, `evidencia`, `openspec` y `test`. El `Dockerfile` MUST NOT declarar `DATABASE_URL` ni credenciales, y el contexto de build MUST NOT excluir `app/`.

#### Scenario: Contexto sin archivos sensibles

- **WHEN** se inspecciona el contenido enviado al build con el `.dockerignore` vigente
- **THEN** no incluye `.env`, `.venv`, `.git`, `test/`, `evidencia/` ni `knowledge-base/`, e incluye `app/`

#### Scenario: Dockerfile sin secretos

- **WHEN** se revisa el `Dockerfile` en busca de `DATABASE_URL`, `postgresql://` o contraseñas
- **THEN** no aparece ninguna cadena de conexión ni credencial

### Requirement: Healthcheck propio sobre la base

La imagen SHALL declarar un `HEALTHCHECK` que consulte `GET /health/ready` a través de `http://127.0.0.1:8000` con `wget`. El healthcheck MUST NOT usar `localhost`, porque Alpine lo resuelve a IPv6 y uvicorn escucha IPv4.

#### Scenario: Contenedor healthy

- **WHEN** el contenedor arranca con una base accesible y se ejecuta `docker ps`
- **THEN** el estado de salud aparece como `healthy` dentro del período de gracia configurado

#### Scenario: Healthcheck con IPv4 explícita

- **WHEN** se ejecuta `docker exec libreria wget -qO- http://127.0.0.1:8000/health/ready`
- **THEN** responde 200 con `{"estado": "listo", "base": "ok"}`

### Requirement: Configuración por entorno al correr

La configuración SHALL entrar al contenedor con `--env-file` en `docker run`, con `DATABASE_URL` obligatoria y `SQL_ECHO` opcional. El contenedor MUST NOT arrancar sin `DATABASE_URL`: el proceso SHALL terminar con código distinto de 0.

#### Scenario: Arranque con variables

- **WHEN** se ejecuta `docker run` con `--env-file` que define `DATABASE_URL` válida
- **THEN** el contenedor arranca, crea las tablas faltantes y queda sirviendo

#### Scenario: Faltante DATABASE_URL

- **WHEN** se ejecuta la imagen sin `DATABASE_URL` en el entorno
- **THEN** el contenedor no queda sirviendo y termina con un código de salida distinto de 0

### Requirement: Seed ejecutable dentro del contenedor

La imagen SHALL incluir el módulo de datos iniciales dentro de `app/`, de modo que `docker exec libreria python -m app.seed` funcione sobre la base configurada sin copiar directorios adicionales.

#### Scenario: Seed en el contenedor

- **WHEN** se ejecuta `docker exec libreria python -m app.seed`
- **THEN** el comando termina con código 0 y deja los conteos iniciales esperados

### Requirement: Procedimiento de verificación reproducible

El proyecto SHALL documentar los comandos de build, ejecución y verificación de los casos D-01, D-02, D-05 y D-06 en `DEPLOY.md` o en un script versionado. La evidencia que requiera un motor Docker SHALL registrarse como pendiente cuando no pueda ejecutarse, con el comando y el criterio de aceptación, y MUST NOT contener salidas inventadas.

#### Scenario: Verificación sin Docker disponible

- **WHEN** el entorno de desarrollo no tiene el comando `docker`
- **THEN** los artefactos de imagen se entregan igual, y los archivos de evidencia D-01/D-02/D-05/D-06 indican `PENDIENTE` con el comando que los produce

#### Scenario: Verificación con Docker disponible

- **WHEN** se corre el procedimiento documentado en una máquina o VPS con Docker
- **THEN** las salidas reales reemplazan el estado pendiente y cubren tamaño, estado `healthy`, logs, fallo sin `DATABASE_URL` y usuario no root

### Requirement: Documentación de imagen y contenedor

`DEPLOY.md` SHALL documentar la construcción de la imagen, el comando `docker run` con `--env-file` y `-p`, la verificación del healthcheck, la ejecución del seed dentro del contenedor y el procedimiento de actualización, sin incluir valores reales de conexión.

#### Scenario: DEPLOY.md utilizable

- **WHEN** otra persona lee `DEPLOY.md` con el repositorio clonado y un archivo de variables propio
- **THEN** puede construir, correr y verificar el contenedor siguiendo solo ese documento, sin credenciales en el repositorio

#### Scenario: Sin secretos en la documentación

- **WHEN** se revisa `DEPLOY.md` en busca de usuarios, contraseñas o hosts reales
- **THEN** solo aparecen nombres de archivo de variables y valores de ejemplo
