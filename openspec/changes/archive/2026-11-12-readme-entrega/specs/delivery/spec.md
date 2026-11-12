# Spec Delta

## Purpose

Define la entrega del proyecto: un `README.md` reproducible que identifica a
los integrantes, una plantilla de entorno sin valores reales, un `DEPLOY.md`
que cumple la checklist y un paquete `.zip` con el contenido exacto y sin
secretos.

## ADDED Requirements

### Requirement: README reproducible con integrantes

El `README.md` SHALL identificar al grupo **ZorionTech** y a los integrantes
**Lautaro Naranjo** y **Martin Escudero** con nombres y apellidos, y SHALL
describir el camino desde cero: requisitos, creación del entorno virtual,
instalación de `requirements.txt` y `requirements-dev.txt`, copia de
`env.example` a `.env`, arranque con `uvicorn app.main:app`, carga de datos
iniciales con `python -m app.seed` y ejecución de los casos de prueba.

#### Scenario: Identificación de la entrega

- **WHEN** se abre `README.md`
- **THEN** aparecen el grupo ZorionTech y los dos integrantes con nombres y apellidos

#### Scenario: Arranque desde cero

- **WHEN** un tercero sigue los pasos del README en una máquina con Python 3.12 y PostgreSQL 16
- **THEN** crea el venv, instala las dependencias, copia `env.example` a `.env`, arranca la API y carga el seed sin editar código

#### Scenario: Casos de prueba documentados

- **WHEN** se busca cómo ejecutar los casos
- **THEN** el README indica los archivos `.http` de `test/` con VS Code REST Client o JetBrains HTTP Client, la variable `@base` para local o la URL pública, y el comando `pytest -q`

### Requirement: Plantilla de entorno sin secretos

`env.example` SHALL contener únicamente la forma de `DATABASE_URL` (con los marcadores `usuario`, `password`, `host` y `base`) y `SQL_ECHO=false`. MUST NOT contener usuario, contraseña, host o base reales, ni la IP del VPS.

#### Scenario: Plantilla neutra

- **WHEN** se lee `env.example`
- **THEN** `DATABASE_URL` usa solo marcadores y `SQL_ECHO` vale `false`

#### Scenario: Sin datos del despliegue

- **WHEN** se busca la IP del VPS, un usuario o una contraseña en `env.example`
- **THEN** no aparece ninguno

### Requirement: DEPLOY.md completo contra la checklist

`DEPLOY.md` SHALL documentar la URL pública, el día y la hora del despliegue,
los comandos completos de construcción, ejecución, verificación y
actualización, el **nombre** del archivo de variables sin su contenido, los
cambios necesarios para correr en el contenedor y el procedimiento de
actualización.

#### Scenario: Reproducción del despliegue

- **WHEN** se sigue `DEPLOY.md` en el VPS
- **THEN** los comandos usan `libreria-zoriontech` y `/root/libreria-zoriontech.env` y se pueden ejecutar sin adivinar valores

#### Scenario: Sin secretos en la documentación

- **WHEN** se revisa `DEPLOY.md`
- **THEN** no contiene contraseñas, usuarios de base reales ni el contenido del archivo de variables

### Requirement: Paquete de entrega con contenido exacto

El paquete SHALL llamarse `Parcial_Cap1a4_ZorionTech.zip` y SHALL contener una sola carpeta raíz `Parcial_Cap1a4_ZorionTech/` con exactamente `app/` (incluido `app/seed.py`), `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `env.example`, `test/`, `Dockerfile`, `.dockerignore`, `README.md`, `DEPLOY.md`, `evidencia/` y `scripts/`.

#### Scenario: Contenido incluido

- **WHEN** se listan las entradas del `.zip`
- **THEN** están todas las rutas de la lista blanca bajo una única raíz `Parcial_Cap1a4_ZorionTech/`

#### Scenario: Contenido excluido

- **WHEN** se buscan `.env`, `.env.docker`, `.git/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `openspec/`, `docs/`, `knowledge-base/`, `.atl/`, `AGENTS.md` o `CLAUDE.md` dentro del `.zip`
- **THEN** no aparece ninguno

### Requirement: Paquete sin secretos

El `.zip` MUST NOT contener credenciales, cadenas de conexión con usuario y
contraseña reales, claves privadas, tokens ni archivos de variables del
entorno. La revisión SHALL hacerse sobre la copia que se comprime, incluidos
los archivos que git ignora.

#### Scenario: Revisión antes de comprimir

- **WHEN** se buscan `DATABASE_URL` con credenciales, `password=`, claves privadas o tokens en la copia limpia
- **THEN** no hay coincidencias y ningún archivo `.env` real está presente

#### Scenario: Copia limpia

- **WHEN** se arma el `.zip`
- **THEN** se parte de una copia con lista blanca y no de la raíz del repositorio con `.git`

### Requirement: Verificación de la entrega

Antes de cerrar, la suite SHALL pasar completa y el despliegue SHALL seguir en
línea. La verificación SHALL incluir `openspec validate --strict` del change y
un `GET` de solo lectura a `/health/ready` de la URL pública.

#### Scenario: Suite completa

- **WHEN** se ejecuta `pytest -q`
- **THEN** pasan 405 tests y quedan 3 skipped por requerir PostgreSQL

#### Scenario: Despliegue en línea

- **WHEN** se hace `GET http://46.202.151.202:8000/health/ready`
- **THEN** responde 200 con `{"estado": "listo", "base": "ok"}`
