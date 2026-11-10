# app-foundation Specification

## Purpose
Define el arranque, la configuración por entorno y el ciclo de vida de la aplicación: qué necesita para levantar, cómo obtiene su configuración y cómo administra el motor y las sesiones de base de datos durante toda la vida del proceso.

## Requirements

### Requirement: Estructura de paquetes obligatoria

El proyecto SHALL organizarse en paquetes por dominio bajo `app/modules/<módulo>/`, cada uno con su `__init__.py`, y SHALL concentrar la infraestructura transversal en `app/core/`. El punto de entrada SHALL ser `app/main.py` y los healthchecks SHALL vivir en `app/modules/health/router.py`.

#### Scenario: Esqueleto de la aplicación presente

- **WHEN** se inspecciona la raíz del repositorio tras aplicar el change
- **THEN** existen `app/main.py`, `app/core/config.py`, `app/core/database.py`, `app/modules/health/router.py` y un paquete con `__init__.py` por cada dominio previsto (`health`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`)

### Requirement: Artefactos de soporte del proyecto

El proyecto SHALL incluir los directorios `test/` y `scripts/`, y los archivos `requirements.txt`, `env.example`, `.gitignore` y un `README.md` mínimo con los pasos de instalación y arranque. El `.gitignore` SHALL excluir al menos `.env`, `.venv`, `__pycache__/` y `*.pyc`.

#### Scenario: Artefactos de soporte presentes

- **WHEN** se inspecciona la raíz del repositorio tras aplicar el change
- **THEN** existen `test/`, `scripts/`, `requirements.txt`, `env.example`, `.gitignore` y `README.md`, y el `.gitignore` excluye `.env`, `.venv`, `__pycache__/` y `*.pyc`

### Requirement: Dependencias limitadas al stack oficial

El archivo `requirements.txt` SHALL declarar únicamente `fastapi[standard]`, `sqlmodel>=0.0.24`, `sqlalchemy[asyncio]>=2.0`, `asyncpg>=0.30` y `python-dotenv>=1.0`. El proyecto MUST NOT incorporar Redis, Alembic, autenticación ni frameworks de migración.

#### Scenario: Instalación del stack aprobado

- **WHEN** se revisa `requirements.txt`
- **THEN** contiene las cinco dependencias del stack oficial y ninguna dependencia de caché, migraciones o autenticación

### Requirement: Configuración exclusiva por entorno con fallo temprano

El sistema SHALL leer su configuración del entorno, cargando previamente un archivo `.env` local si existe. La variable `DATABASE_URL` SHALL ser obligatoria y MUST NOT tener valor por defecto: si está ausente o vacía, el arranque SHALL fallar con un mensaje claro que nombre la variable faltante. La variable `SQL_ECHO` SHALL ser opcional, SHALL interpretarse como booleano y SHALL valer `false` cuando no está definida.

#### Scenario: Arranque sin DATABASE_URL

- **WHEN** se inicia la aplicación sin `DATABASE_URL` en el entorno
- **THEN** el arranque falla antes de atender peticiones con un mensaje propio que menciona `DATABASE_URL`, sin exponer credenciales ni trazas internas

#### Scenario: SQL_ECHO omitido

- **WHEN** la aplicación arranca con `DATABASE_URL` definida y sin `SQL_ECHO`
- **THEN** el registro de consultas SQL queda desactivado

#### Scenario: SQL_ECHO activado explícitamente

- **WHEN** `SQL_ECHO` vale `true`
- **THEN** el motor de base de datos emite el registro de las consultas SQL

### Requirement: Credenciales solo por entorno

El repositorio SHALL incluir `env.example` con la forma de `DATABASE_URL` y el valor `SQL_ECHO=false`, sin credenciales ni hosts reales. Ningún archivo versionado, imagen o entregable SHALL contener la cadena de conexión real.

#### Scenario: Plantilla sin secretos

- **WHEN** se revisa `env.example` en el repositorio
- **THEN** muestra `DATABASE_URL=postgresql+asyncpg://usuario:password@host:5432/base` y `SQL_ECHO=false`, y no contiene credenciales reales

### Requirement: Ciclo de vida del motor y la fábrica de sesiones

Al arrancar, la aplicación SHALL crear un motor asincrónico y una fábrica de sesiones a partir de la configuración, y SHALL publicarlos en el estado de la aplicación (`app.state.engine` y `app.state.session_factory`) para que estén disponibles durante toda la vida del proceso. Al apagarse, SHALL liberar el motor y sus conexiones.

#### Scenario: Arranque con configuración válida

- **WHEN** la aplicación completa su arranque con `DATABASE_URL` válida y la base accesible
- **THEN** el estado de la aplicación expone un motor y una fábrica de sesiones utilizables por los handlers

#### Scenario: Apagado ordenado

- **WHEN** la aplicación recibe la señal de apagado
- **THEN** libera el motor y sus conexiones antes de terminar el proceso

### Requirement: Sesión por petición

Cada petición que necesite base de datos SHALL obtener su propia sesión asincrónica y SHALL liberarla al finalizar la petición, incluso si el handler falla. La sesión MUST NOT compartirse entre peticiones concurrentes.

#### Scenario: Sesión aislada y cerrada

- **WHEN** dos peticiones concurrentes usan la dependencia de sesión
- **THEN** cada una recibe una sesión distinta y ambas quedan cerradas al finalizar sus peticiones

### Requirement: Creación del esquema al arrancar

Al arrancar, la aplicación SHALL crear las tablas faltantes del esquema con todos los modelos del proyecto ya registrados, sin alterar tablas existentes y sin ejecutar migraciones. Si la base no responde, el arranque SHALL fallar en lugar de continuar en un estado inconsistente.

#### Scenario: Base vacía

- **WHEN** la aplicación arranca contra una base accesible sin tablas
- **THEN** el esquema queda creado y la aplicación comienza a atender peticiones

#### Scenario: Base inalcanzable al arrancar

- **WHEN** la aplicación arranca y la base de datos no responde
- **THEN** el arranque falla y el proceso termina con error antes de declararse listo
