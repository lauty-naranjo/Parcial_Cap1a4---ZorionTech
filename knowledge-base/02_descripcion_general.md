# Descripción General

## Stack tecnológico

| Capa | Tecnología | Versión mínima | Uso |
|---|---|---|---|
| Lenguaje | Python | 3.12 | Runtime de la aplicación |
| Framework web | FastAPI | 0.111 | API REST; todos los handlers `async def` |
| Modelos y DTO | SQLModel | 0.0.24 | Modelos de tabla y contratos en una sola librería |
| ORM | SQLAlchemy | 2.0 (asincrónico) | Motor, sesión y carga anticipada |
| Driver | asyncpg | 0.30 | Controlador asincrónico de PostgreSQL |
| Base de datos | PostgreSQL | 16 | Persistencia; en el despliegue, la del servidor |
| Configuración | python-dotenv | 1.0 | Lectura del archivo `.env` |
| Servidor ASGI | uvicorn | la que instala `fastapi[standard]` | Servir la app (`app.main:app`) |
| Contenedor | Docker | 20.10 | Construir la imagen y correr el contenedor en local y en el VPS |

Decisiones transversales:

- **Dinero con `Decimal`**, nunca `float`. Los DTO de salida serializan importes como string decimal (`"25000.00"`).
- **Sin secretos en código**: `DATABASE_URL` se lee de `.env`; el repositorio incluye `env.example` sin valores reales.
- **Diagnóstico SQL configurable** (`SQL_ECHO`, por ejemplo vía `echo=True`) para evidenciar el número fijo de consultas (caso C-07).

## Arquitectura general

```
Cliente HTTP (.http / curl / corrector)
        │  JSON
        ▼
┌──────────────────────────────────────────────┐
│ FastAPI (app/main.py)                        │
│  lifespan: crea engine + session factory     │
│            en app.state, create_all          │
│  routers por módulo funcional                │
└───────┬──────────────────────────────────────┘
        │ Depends(get_session)  (una sesión por petición)
        ▼
┌──────────────────────────────────────────────┐
│ Módulo funcional                             │
│  router.py  → recibe, delega, declara salida │
│  service.py → lógica, IntegrityError, eager  │
│  models.py  → tabla, restricciones, relaciones│
│  schemas.py → Create / Update / Read         │
└───────┬──────────────────────────────────────┘
        │ SQLAlchemy 2.0 async (asyncpg)
        ▼
┌──────────────────────────────────────────────┐
│ PostgreSQL 16 (servidor de la cátedra)       │
│  UNIQUE · CHECK · FK · índices               │
└──────────────────────────────────────────────┘
```

Justificación de alto nivel:

- **Organización por módulo funcional** (no por capa técnica): cada módulo agrupa `models`, `schemas`, `service` y `router`, con la misma estructura repetida. Reduce el costo de navegación y hace explícito el límite de cada dominio.
- **La lógica vive en el `service`**, que recibe la sesión como parámetro. El router no arma consultas ni traduce errores de base.
- **La base garantiza lo que la base puede garantizar**: unicidad, claves foráneas y CHECK. No se consulta antes para verificar existencia; se escribe y se traduce el `IntegrityError` a 409 (RN-01, RN-02, RN-09, C-02…C-05).
- **Carga anticipada declarada en la consulta**: `joinedload` para relaciones a uno (`libro.editorial`, `libro.genero`, `venta.cliente`, `cliente.perfil`, `libro_autor.autor`) y `selectinload` para colecciones (`libro.autorias`, `venta.renglones`). Nunca carga perezosa.
- **Una sola imagen**: el contenedor no incluye la base; la configuración entra por `--env-file` en tiempo de ejecución.

## Integraciones externas

| Servicio | Propósito | Tipo |
|---|---|---|
| PostgreSQL 16 del VPS | Persistencia relacional | Driver asyncpg (TCP) |
| Docker Engine del VPS | Construir y correr la imagen | CLI `docker build` / `docker run` |
| Ninguna API de terceros | — | — |

No hay pasarela de pagos, correo real ni servicios cloud: el aviso de comprobante es simulado con log y `asyncio.sleep(0.5)`.

## API REST (resumen por recurso)

| Recurso | Rutas |
|---|---|
| Salud | `GET /health/live`, `GET /health/ready` |
| Editoriales | `POST /editoriales/`, `GET /editoriales/`, `GET /editoriales/{id}`, `PATCH /editoriales/{id}`, `GET /editoriales/{id}/libros` |
| Géneros | `POST /generos/`, `GET /generos/`, `GET /generos/{id}/libros` |
| Autores | `POST /autores/`, `GET|PATCH /autores/{id}`, `GET /autores/{id}/libros` |
| Libros | `POST /libros/`, `GET /libros/`, `GET /libros/{id}`, `PATCH /libros/{id}` |
| Clientes | `POST /clientes/`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas` |
| Ventas | `POST /ventas/`, `GET /ventas/`, `GET /ventas/{id}` (sin PATCH: RN-08) |

El contrato completo (cuerpos, respuestas y códigos) está en [11_contratos_api.md](11_contratos_api.md).

## Documentación interactiva

FastAPI expone `/docs` y `/openapi.json` automáticamente (no se evalúa su contenido, pero sirve para probar el contrato).
