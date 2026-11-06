# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| Modular por dominio | `app/modules/<módulo>/` con `models`, `schemas`, `service`, `router` | Estructura obligatoria; límites explícitos entre dominios |
| Capas router → service → sesión | Todo módulo | El router no arma SQL ni traduce errores; el servicio recibe la sesión como parámetro |
| DTO separados de tablas | `schemas.py` (`Create`, `Update`, `Read`) | Evita filtrar `id` en altas y permite PATCH parcial |
| Repository / UoW | **No aplica** | Excluido por la consigna (capítulo 6) |
| Lifespan + `app.state` | `app/main.py` | Un solo motor por proceso; se cierra al apagar |
| Sesión por petición | `Depends(get_session)` | Aislamiento y cierre garantizado; `expire_on_commit=False` |
| Eager loading declarativo | `service.py` | Elimina N+1 y la carga perezosa |
| Traducción de `IntegrityError` | `service.py` | Cumple RN-12: nunca texto interno de la base |
| Composición con cascade | `Venta` ↔ `RenglonVenta` | El renglón nace y muere con la venta |
| Asociación con datos | `LibroAutor` | `rol` y `orden` pertenecen a la relación |
| Tareas en segundo plano | `BackgroundTasks` | El aviso no bloquea la respuesta |
| Configuración por entorno | `app/core/config.py` + `.env` / `--env-file` | Sin secretos en código ni imagen |

## Estructura de directorios

```
Parcial_Cap1a4 - ZorionTech/
├── app/
│   ├── main.py                  # FastAPI, lifespan, registro de routers
│   ├── core/
│   │   ├── config.py            # DATABASE_URL, SQL_ECHO desde el entorno
│   │   └── database.py          # motor, async_sessionmaker, get_session
│   └── modules/
│       ├── health/
│       │   └── router.py        # /health/live, /health/ready
│       ├── editoriales/
│       │   ├── models.py        # Editorial
│       │   ├── schemas.py       # EditorialCreate/Update/Read
│       │   ├── service.py
│       │   └── router.py
│       ├── generos/             # misma estructura
│       ├── autores/             # misma estructura
│       ├── libros/              # Libro + LibroAutor (viven acá)
│       ├── clientes/            # Cliente + PerfilCliente
│       └── ventas/              # Venta + RenglonVenta
├── scripts/ (o app/seed.py)     # datos iniciales conocidos
├── test/
│   ├── health.http
│   ├── editoriales.http
│   ├── generos.http
│   ├── autores.http
│   ├── libros.http
│   ├── clientes.http
│   ├── ventas.http
│   └── casos-C.http            # C-01 … C-08 con resultado esperado comentado
├── evidencia/
│   ├── C-07-consultas-libro.txt
│   ├── C-07-consultas-venta.txt
│   └── D-01 … D-07
├── docs/
│   └── consigna-parcial-cap1a4.md
├── knowledge-base/
├── openspec/
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── env.example
├── README.md
├── DEPLOY.md
├── .gitignore
└── .env                        # NO se versiona, NO va al zip, NO va a la imagen
```

## Capa de datos

```python
# app/core/database.py (forma esperada)
engine = create_async_engine(settings.database_url, echo=settings.sql_echo)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
```

```python
# app/main.py (forma esperada)
@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(...)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    await engine.dispose()
```

> `create_all` requiere que **todos** los modelos estén importados antes de ejecutarse; de lo contrario crea un esquema incompleto.

## Seguridad

| Aspecto | Enfoque |
|---|---|
| Autenticación | No implementada (fuera de alcance) |
| Autorización | No implementada (fuera de alcance) |
| Validación de input | DTO SQLModel/Pydantic con `Field` (`gt`, `ge`, `min_length`), `Query` con límites y `exclude_unset` en PATCH |
| SQL | ORM y parámetros ligados; **nunca** concatenación con datos del usuario |
| Errores | Traducción de `IntegrityError` a mensajes propios; sin trazas ni nombres de constraints |
| Secretos | Solo por entorno; `.env` ignorado por Git, `.dockerignore` y `.gitignore`; `env.example` sin valores reales |
| Contenedor | Usuario no root, imagen Alpine mínima, sin secretos horneados |
| Historial Git | No debe contener credenciales nunca (el `.zip` puede incluir `.git` y se revisa) |

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `DATABASE_URL` | URL de conexión con driver asyncpg | `postgresql+asyncpg://usuario:clave@host:5432/libreria` | **Sí** (la clave) |
| `SQL_ECHO` | Activa el log de consultas | `false` en despliegue; `true` para C-07 | No |

`env.example` (forma, sin secretos reales):

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@host:5432/base
SQL_ECHO=false
```

## Decisiones de infraestructura

- **Una sola imagen**, sin Compose, sin base embebida.
- **`--env-file`** en `docker run`: la configuración vive fuera del repositorio y de la imagen.
- **`--restart unless-stopped`**: recupera el contenedor si la base no estaba lista al arrancar.
- **`0.0.0.0:8000`** dentro del contenedor; publicación con `-p <puerto>:8000`.
- **`host.docker.internal`** para alcanzar PostgreSQL del host (en Linux, `--add-host=host.docker.internal:host-gateway`), o la dirección que provea la cátedra. **Nunca `localhost`** dentro del contenedor.

Detalle completo en [12_devops_y_despliegue.md](12_devops_y_despliegue.md).
