# Funcionalidades

Organizadas por **épica** y luego por **historia de usuario**. Cada historia referencia sus reglas y los casos de prueba que la demuestran.

## Épica 0: Fundación técnica

### US-000 — Proyecto, conexión y ciclo de vida
**Como** equipo de desarrollo
**Quiero** una aplicación FastAPI con motor asincrónico creado en el `lifespan`, sesión por petición y `.env`
**Para** que la API arranque, cree su esquema y atienda peticiones sin bloquear.

**Criterios de aceptación**:
- [ ] Estructura obligatoria: `app/main.py`, `app/core/config.py`, `app/core/database.py`, `app/modules/<módulo>/{models,schemas,service,router}.py`.
- [ ] `DATABASE_URL` se lee del entorno (`.env` no versionado); existe `env.example` sin secretos.
- [ ] El motor y la fábrica de sesiones se crean en `lifespan`, se guardan en `app.state` y el motor se cierra al apagar.
- [ ] La sesión llega con `Depends(get_session)`, una por petición, `expire_on_commit=False`.
- [ ] `SQLModel.metadata.create_all` corre al arrancar con todos los modelos importados.
- [ ] `GET /health/live` responde `{"estado": "vivo"}` **sin tocar la base**.
- [ ] `GET /health/ready` ejecuta `SELECT 1` y reporta el estado de la base.
- [ ] Sin `DATABASE_URL` la aplicación falla al arrancar (D-05).

**Reglas**: RN-G-05, RN-G-04 · **Casos**: D-02, D-05, D-06

## Épica 1: Catálogo

### US-010 — Gestionar editoriales
**Como** librero **quiero** crear, listar, consultar y editar editoriales **para** clasificar los libros por sello.

**Criterios de aceptación**:
- [ ] `POST /editoriales/` → 201 `EditorialRead`; nombre repetido → 409.
- [ ] `GET /editoriales/` paginado (`limit` 1–100 def. 20, `offset` ≥ 0) → 200; parámetros fuera de rango → 422.
- [ ] `GET /editoriales/{id}` → 200 o 404; id no entero → 422 sin ejecutar el handler (C-01).
- [ ] `PATCH /editoriales/{id}` aplica solo campos enviados (`exclude_unset`) → 200, 404, 409.
- [ ] `GET /editoriales/{id}/libros` → libros de la editorial; 404 si la editorial no existe.

**Reglas**: RN-10, RN-12 · **Casos**: C-01

### US-011 — Gestionar géneros
**Como** librero **quiero** crear, listar y ver los libros de un género **para** organizar el catálogo temáticamente.

**Criterios de aceptación**:
- [ ] `POST /generos/` → 201, 409 si el nombre está repetido.
- [ ] `GET /generos/` → 200 (paginado).
- [ ] `GET /generos/{id}/libros` → 200 / 404.

**Reglas**: RN-G-01, RN-10

### US-012 — Gestionar autores y sus libros
**Como** librero **quiero** crear, consultar, editar autores y ver sus libros con rol y orden **para** conocer la participación de cada autor.

**Criterios de aceptación**:
- [ ] `POST /autores/` → 201 / 422.
- [ ] `GET /autores/{id}` y `PATCH /autores/{id}` → 200 / 404 / 422.
- [ ] `GET /autores/{id}/libros` devuelve cada libro con su `rol` y `orden`; 404 si el autor no existe.

**Reglas**: RN-10, RN-G-03

### US-013 — Alta de libro con relaciones
**Como** librero **quiero** dar de alta un libro con editorial, género opcional y varios autores con rol y orden **para** reflejar el modelo real del catálogo.

**Criterios de aceptación**:
- [ ] `POST /libros/` recibe `isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id` (opcional) y `autores: [{autor_id, rol, orden}]`.
- [ ] Responde 201 con el detalle del libro (editorial, género y autores).
- [ ] ISBN repetido → 409 (RN-01).
- [ ] Editorial o autor inexistente → **409** con mensaje propio, sin consulta previa (C-04).
- [ ] `precio <= 0` o `stock < 0` → 422 (DTO) y CHECK en la base.
- [ ] Cada autoría persiste en `libro_autor` con PK `(libro_id, autor_id)`.

**Reglas**: RN-01, RN-03, RI-01, RI-02, RI-05 · **Casos**: C-02, C-04

### US-014 — Listado y búsqueda de libros
**Como** librero **quiero** listar libros con su editorial y género, filtrando por parte del título y por género **para** encontrar rápidamente un ejemplar.

**Criterios de aceptación**:
- [ ] `GET /libros/?limit&offset&titulo&genero_id` → 200 con libros y su editorial y género.
- [ ] `titulo` busca por parte del título sin distinguir mayúsculas, con parámetro ligado (RN-11).
- [ ] `titulo=' OR '1'='1` → 200 con lista vacía (C-08), nunca error de SQL.
- [ ] Parámetros de paginación inválidos → 422.

**Reglas**: RN-10, RN-11 · **Casos**: C-08

### US-015 — Detalle de libro sin N+1
**Como** librero **quiero** ver un libro con editorial, género y autores **para** revisar su ficha completa.

**Criterios de aceptación**:
- [ ] `GET /libros/{id}` → 200 con editorial, género y autores; 404 si no existe.
- [ ] La consulta usa `joinedload` (editorial, género) y `selectinload` (autorías → autor).
- [ ] La cantidad de consultas es fija con uno o con varios autores (C-07).

**Reglas**: RN-G-03 · **Casos**: C-07

### US-016 — Edición parcial de libro
**Como** librero **quiero** actualizar campos sueltos de un libro **para** corregir precio, stock o clasificación sin reenviar todo.

**Criterios de aceptación**:
- [ ] `PATCH /libros/{id}` con `exclude_unset` → 200 con el detalle actualizado.
- [ ] 404 si no existe; 409 si el nuevo ISBN choca; 422 si el cuerpo no cumple el contrato.

**Reglas**: RN-01, RN-03, RN-10

## Épica 2: Clientes

### US-020 — Alta y edición de clientes
**Como** librero **quiero** registrar y editar clientes **para** asociarles ventas.

**Criterios de aceptación**:
- [ ] `POST /clientes/` → 201; email repetido → 409; cuerpo inválido → 422.
- [ ] `GET /clientes/{id}` → 200 con su perfil (objeto o `null`), 404 si no existe.
- [ ] `PATCH /clientes/{id}` → 200 con perfil, 404, 409, 422.

**Reglas**: RN-02, RN-09

### US-021 — Perfil uno a uno
**Como** librero **quiero** cargar teléfono y dirección de un cliente **para** tener sus datos de contacto.

**Criterios de aceptación**:
- [ ] `POST /clientes/{id}/perfil` → 201 `PerfilRead`; 404 si el cliente no existe.
- [ ] Segundo perfil para el mismo cliente → **409** (UNIQUE `cliente_id`) (C-03).
- [ ] `Cliente.perfil` devuelve un objeto, no una lista.

**Reglas**: RN-09 · **Casos**: C-03

### US-022 — Ventas de un cliente
**Como** librero **quiero** ver las ventas de un cliente **para** atender consultas y reclamos.

**Criterios de aceptación**:
- [ ] `GET /clientes/{id}/ventas` → 200 con la lista; 404 si el cliente no existe.
- [ ] No dispara N+1 sobre renglones ni cliente.

**Reglas**: RN-G-03

## Épica 3: Ventas

### US-030 — Registrar venta con renglones
**Como** librero **quiero** registrar una venta con todos sus renglones en una sola operación **para** que el hecho quede consistente y con el total correcto.

**Criterios de aceptación**:
- [ ] `POST /ventas/` recibe `cliente_id` y `renglones: [{libro_id, cantidad}]` → 201 con cliente y renglones.
- [ ] El precio unitario se copia del libro; el total se calcula sumando `cantidad × precio_unitario` (RN-06, RN-07).
- [ ] El precio y el total **no** viajan en el DTO; la fecha la pone el servidor con zona horaria.
- [ ] Renglones vacíos o `libro_id` repetido → 422 (RN-05).
- [ ] Cliente o libro inexistente → **409** (C-05).
- [ ] Cada renglón de la respuesta incluye `libro_id`, `titulo`, `cantidad`, `precio_unitario` y `subtotal`.

**Reglas**: RN-04, RN-05, RN-06, RN-07, RI-03, RI-04 · **Casos**: C-05, C-06, D-03

### US-031 — Listado y detalle de ventas
**Como** librero **quiero** listar y consultar ventas con cliente y renglones **para** auditar la operación.

**Criterios de aceptación**:
- [ ] `GET /ventas/?limit&offset` → 200 paginado, 422 fuera de rango.
- [ ] `GET /ventas/{id}` → 200 con cliente y renglones, 404 si no existe.
- [ ] Sin carga perezosa; cantidad fija de consultas (C-07).
- [ ] No existe PATCH de ventas (RN-08).

**Reglas**: RN-08, RN-10, RN-G-03 · **Casos**: C-07

### US-032 — Aviso de comprobante en segundo plano
**Como** cliente **quiero** recibir el aviso de mi comprobante **para** tener constancia de la compra, sin que la venta espere ese envío.

**Criterios de aceptación**:
- [ ] Al registrar la venta se agenda `BackgroundTasks` con `asyncio.sleep(0.5)` y un mensaje en el log.
- [ ] La respuesta 201 se envía **antes** de que el aviso termine.
- [ ] El servidor sigue atendiendo otras peticiones mientras corre el aviso.
- [ ] En `docker logs libreria` el aviso aparece después de la línea de la respuesta (D-07).

**Reglas**: RN-G-02 · **Casos**: D-07

## Épica 4: Entrega y despliegue

### US-040 — Imagen Docker
**Como** equipo **quiero** empaquetar la aplicación en una imagen Alpine sin secretos y con usuario no root **para** desplegarla en el VPS.

**Criterios de aceptación**:
- [ ] `FROM python:3.12-alpine`; la imagen base queda por debajo de 100 MB (D-01).
- [ ] `requirements.txt` se copia e instala antes del código, con `--no-cache-dir`.
- [ ] Usuario sin privilegios + `USER` (D-06).
- [ ] `.dockerignore` excluye `.env`, `.venv`, `.git`, `__pycache__`.
- [ ] `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- [ ] `HEALTHCHECK` contra `/health/ready` usando `127.0.0.1` (no `localhost`).
- [ ] `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo> libreria`.

**Reglas**: RN-G-04 · **Casos**: D-01, D-02, D-06

### US-041 — Despliegue y evidencia
**Como** grupo **quiero** el proyecto en línea y documentado **para** que la corrección pueda probarlo.

**Criterios de aceptación**:
- [ ] URL pública declarada y accesible; `/health/ready` → 200.
- [ ] `DEPLOY.md` con URL, fecha y hora, comandos completos, cambios hechos y procedimiento de actualización.
- [ ] Base cargada con el comando de seed dentro del contenedor.
- [ ] `evidencia/` con la salida de C-07 y de cada caso D.
- [ ] `.zip` sin `.venv`, `__pycache__` ni `.env`; nombres de integrantes en `README.md`.

**Casos**: D-01…D-07
