# Visión y Objetivos

## Propósito del sistema

API REST asincrónica para la gestión de catálogo y ventas de una librería de barrio (proyecto **ZorionTech**, parcial de Programación III, unidades 1 a 4 + despliegue).

El sistema permite administrar editoriales, géneros, autores y libros —con sus relaciones de agregación y muchos a muchos con datos—, registrar clientes con su perfil uno a uno, y registrar ventas compuestas por renglones que copian el precio del libro al momento de la operación. La aplicación se empaqueta en una imagen Docker basada en `python:3.12-alpine` y se publica en un VPS con PostgreSQL 16 provisto por la cátedra.

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| Librero / administrador del catálogo | Mantener el catálogo actualizado (editoriales, géneros, autores, libros) | Controlar stock y precio; consultar existencias por editorial, género o autor |
| Librero / vendedor | Registrar una venta con sus renglones en una sola operación | Obtener el total calculado por el servidor; consultar las ventas de un cliente |
| Cliente de la librería | Quedar registrado con sus datos de contacto y su perfil | Recibir el aviso de comprobante de su compra |
| Cátedra / corrector | Verificar el cumplimiento de los 8 ejercicios y de los casos C-01…C-08 y D-01…D-07 | Acceder a la API desplegada y revisar la evidencia y el historial del repositorio |
| Equipo de desarrollo (ZorionTech) | Construir, contenerizar y desplegar el proyecto | Mantener credenciales fuera del repositorio y de la imagen |

## Alcance v1.0 (entrega del parcial)

- API REST con FastAPI, todos los handlers `async def`, sin llamadas bloqueantes.
- Ciclo de vida con `lifespan`: motor asincrónico, fábrica de sesiones y `create_all` al arrancar; cierre del motor al apagar.
- DTO separados de los modelos de tabla (`Create`, `Update`, `Read`) y códigos HTTP 200/201/404/409/422.
- Modelo de dominio completo con UNIQUE, CHECK, claves foráneas, índices y navegación bidireccional (`Relationship(back_populates=...)`).
- CRUD de referencia para editoriales, géneros, autores, libros, clientes y ventas, con paginación (RN-10) y búsqueda por título (RN-11).
- Altas con relaciones: libro con `editorial_id`, `genero_id` y lista de autorías; venta con `cliente_id` y renglones anidados.
- Lecturas con carga anticipada (`joinedload` / `selectinload`) y número fijo de consultas.
- Aviso de comprobante en segundo plano con `BackgroundTasks` + `asyncio.sleep(0.5)`.
- Imagen Docker (`python:3.12-alpine`, usuario no root, sin secretos, `HEALTHCHECK`) y despliegue en el VPS con `docker run` y `--env-file`.
- `env.example`, `README.md`, `DEPLOY.md`, carpeta `evidencia/` y archivos `.http` en `test/`.

## Fuera de alcance (explícito en la consigna)

- Autenticación y autorización (capítulo 5): no hay login, tokens ni RBAC.
- Repositorios y Unit of Work (capítulo 6).
- Colas de tareas con Redis (capítulos 7 y 8).
- Docker Compose: el despliegue es de una sola imagen.
- Migraciones: el esquema se crea con `create_all` al arrancar; no se evalúan Alembic ni versionado de esquema.
- La base de datos no forma parte del paquete: se usa la PostgreSQL 16 ya instalada en el servidor.
- Interfaz web / frontend: el entregable es la API y su documentación.

## Métricas de éxito

| Métrica | Meta |
|---|---|
| Ejercicios aprobados | 8/8 (8 + 22 + 12 + 17 + 8 + 8 + 15 + 10 puntos) |
| Casos de prueba mínimos | C-01…C-08 y D-01…D-07 demostrados |
| Levantamiento desde cero | README reproducible en la máquina del grupo |
| Despliegue | URL pública respondiendo 200 en `/health/ready` al momento de la corrección |
| Seguridad de secretos | Ninguna credencial en el repositorio, el historial, la imagen ni el `.zip` |
| Consultas en lecturas relacionales | Cantidad fija, independiente de la cantidad de autores o renglones |
