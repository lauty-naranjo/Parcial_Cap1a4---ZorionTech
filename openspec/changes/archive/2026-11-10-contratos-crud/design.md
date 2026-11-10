# Design

## Context

C-02 dejó las nueve tablas con constraints nombrados (`uq_*`, `ck_*`, `fk_*`), índices y navegación ORM bidireccional, y **todas las relaciones con `lazy="raise"`** (RN-G-03). También dejó `app/core/database.py` con `SessionDep = Annotated[AsyncSession, Depends(get_session)]` y el `lifespan` importando los `models` de los siete módulos. Hoy solo existe `app/modules/health/router.py`; los módulos de negocio no tienen `schemas.py`, `service.py` ni `router.py`.

La motivación está en `proposal.md`. Este diseño fija **cómo** se construye el contrato REST sobre ese esquema, respetando las reglas duras A/B/C/D de `AGENTS.md`.

Restricciones que condicionan el diseño:

- `lazy="raise"` significa que **toda lectura relacional debe precargarse** (`joinedload`/`selectinload`); un acceso perezoso lanza `InvalidRequestError`.
- Nombres de tablas/columnas obligatorios; los DTO no renombran campos del contrato.
- Dinero `Decimal`/`Numeric` serializado como string decimal (RN-G-01).
- `IntegrityError` → 409 con mensaje propio mapeado por nombre de constraint; nunca `str(exc)` ni texto de PostgreSQL (RN-12).
- Handlers `async def`, sin llamadas bloqueantes (RN-G-02).

## Goals / Non-Goals

**Goals:**

- Un `schemas.py` por módulo con DTO separados de las tablas (`Create` sin `id`, `Update` con todos los campos opcionales, `Read`).
- Un helper de errores y otro de paginación reutilizables en `app/core/`.
- Los 20 endpoints del CRUD de referencia con los códigos HTTP exactos de la matriz.
- Toda lectura con precarga explícita para cumplir `lazy="raise"` y RN-G-03.

**Non-Goals:**

- `POST /libros/` y `POST /ventas/` (C-04); `GET /ventas/` y `GET /ventas/{id}` (C-06/C-07).
- No hay `DELETE` (SU-05) ni edición de autorías por `PATCH` (IN-01).
- No se optimiza el conteo exacto de consultas (C-06); sí se precarga para no romper `lazy="raise"`.
- No se toca el esquema, el `lifespan` ni `/health/*`.

## Decisions

### 1. Estructura de archivos por módulo

Cada módulo de negocio (`editoriales`, `generos`, `autores`, `libros`, `clientes`) recibe:

- `schemas.py`: `XCreate` (sin `id`), `XUpdate` (todos opcionales), `XRead` (campos del contrato). Los modelos de tabla ya viven en `models.py` (C-02) y no se redefinen.
- `service.py`: funciones asíncronas que reciben `session` y los datos, hacen `select`/`get`/`commit` y devuelven el objeto de dominio (o `None`/excepción).
- `router.py`: `APIRouter` con `prefix`, `tags` y, cuando corresponde, `dependencies`; handlers `async def` finos que delegan en el servicio.

**Razón**: routers finos + lógica en `service.py` (fastapi-templates) mantiene la validación en el borde y el mapeo de errores cerca del `commit`.

### 2. DTO y serialización de `Decimal`

- `XCreate`: campos obligatorios del alta sin `id`. `precio: Decimal = Field(gt=0)` y `stock: int = Field(ge=0)` en `LibroUpdate` (RN-03). `email` con validación de formato (EmailStr no está disponible sin `pydantic[email]`; se valida con un patrón simple o `Field` y se confía en el UNIQUE para la unicidad).
- `XUpdate`: todos los campos `Optional`, para soportar PATCH parcial.
- `XRead`: campos exactos de la tabla de DTO de salida de `11_contratos_api.md`. Los importes son `Decimal`; **Pydantic v2 serializa `Decimal` a string en JSON**, de modo que declarar `response_model=XRead` ya produce `"25000.00"`.
- El contrato de entrada acepta `precio` como string decimal o número (`"21000.00"`); Pydantic lo coacciona a `Decimal`.

**Alternativa considerada**: usar `Field(json_schema_extra=...)` o serializadores manuales por campo. Descartada: innecesario con Pydantic v2.

### 3. Helper de errores `app/core/errors.py`

Traduce `IntegrityError` a un `HTTPException` 409 con mensaje propio, sin exponer texto de la base.

- Mapa `CONSTRAINT_MENSAJE: dict[str, str]` con la lista completa (se reutiliza en C-04):

| Constraint | Mensaje (409) |
|---|---|
| `uq_editorial_nombre` | "El nombre ya está registrado" |
| `uq_genero_nombre` | "El nombre ya está registrado" |
| `uq_libro_isbn` | "El ISBN ya está registrado" |
| `uq_cliente_email` | "El email ya está registrado" |
| `uq_perfil_cliente_cliente_id` | "El cliente ya tiene un perfil" |
| `fk_libro_editorial_id` | "La editorial indicada no existe" |
| `fk_libro_genero_id` | "El género indicado no existe" |
| `fk_libro_autor_autor_id` | "El autor indicado no existe" |
| `fk_venta_cliente_id` | "El cliente indicado no existe" |
| `fk_renglon_venta_libro_id` | "El libro indicado no existe" |

- `traducir_integrity_error(exc) -> HTTPException`: recorre `exc.orig` y su `__cause__`/`__context__` buscando el nombre del constraint (asyncpg 0.32 lo expone como `constraint_name` directo en la excepción cruda; también se contempla `diag.constraint_name` por compatibilidad); si el nombre está en el mapa devuelve el mensaje propio, y si no, un 409 genérico ("Conflicto con los datos existentes"). Nunca incluye `str(exc)`.
- El mensaje para nombre duplicado de editorial/género **no está fijado en la KB**; se adopta "El nombre ya está registrado" como decisión (propio, sin texto interno).

**Alternativa considerada**: filtrar `str(exc)` con regex. Descartada por RN-12 y por fragilidad frente a cambios de mensaje del driver.

### 4. Helper de paginación `app/core/pagination.py`

```python
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
```

Los routers declaran `limit: Limit = 20, offset: Offset = 0` (el default se asigna en el handler, no en `Query`, porque FastAPI 0.162+ rechaza el default posicional dentro de `Annotated`) y aplican `select(...).offset(offset).limit(limit)`. RN-10 aplica a **toda colección** (editoriales, géneros, `/{id}/libros` de editorial/género/autor, libros y `/clientes/{id}/ventas`), aunque la matriz no muestre los parámetros en todas las rutas.

### 5. PATCH parcial con `exclude_unset`

En todos los `PATCH` (`editoriales`, `autores`, `clientes`, `libros`): `datos = update.model_dump(exclude_unset=True); db_obj.sqlmodel_update(datos); await session.commit(); await session.refresh(db_obj)`. Solo se persisten los campos realmente enviados.

### 6. Búsqueda de libros por `titulo`

`titulo` es `str | None = Query(None)`. El filtro usa `Libro.titulo.ilike(f"%{titulo}%")` con **parámetro ligado** (nunca concatenación de SQL), lo que hace que `' OR '1'='1` sea un literal y devuelva lista vacía (RN-11, C-08). `genero_id` es `int | None = Query(None)` con `==` exacto.

### 7. Precarga en toda lectura

Para cumplir `lazy="raise"`:

- `GET /libros/` y `/{id}/libros` de editorial/género: `joinedload(Libro.editorial)` + `joinedload(Libro.genero)`.
- `GET /libros/{id}`: `joinedload(Libro.editorial)` + `joinedload(Libro.genero)` + `selectinload(Libro.autorias).joinedload(LibroAutor.autor)`.
- `GET /autores/{id}/libros`: join desde `LibroAutor` con `selectinload(LibroAutor.libro).joinedload(Libro.editorial)` para exponer cada libro con el `rol`/`orden` de esa autoría.
- `GET /clientes/{id}`: `joinedload(Cliente.perfil)` (perfil objeto o `None`, nunca lista).
- `GET /clientes/{id}/ventas`: `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)` para devolver `VentaRead` completo. C-06 optimizará el conteo de consultas sin cambiar el contrato.

### 8. `PATCH /libros/{id}` solo campos escalares (IN-01)

`LibroUpdate` declara únicamente `isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id` (todos opcionales). **No** incluye `autores`: las autorías se cargan solo en `POST /libros/` (C-04) y no se editan por `PATCH`. Documentado en `README.md`.

### 9. Registro de routers en `app/main.py`

`create_app()` incluye los cinco routers nuevos (`editoriales`, `generos`, `autores`, `clientes`, `libros`) junto al de health. El `lifespan` y la inyección de sesión no cambian.

## Risks / Trade-offs

- **Acceso perezoso olvidado rompe en runtime (`InvalidRequestError`)** → mitigación: toda lectura del change precarga; los tests de contrato ejercitan los endpoints con relaciones.
- **Nombre de constraint mal referenciado en `errors.py` → 409 incorrecto o 500** → mitigación: el mapa usa exactamente los nombres fijados en C-02 (`uq_libro_isbn`, `fk_libro_editorial_id`, etc.); tests asertan el 409 con mensaje propio.
- **`GET /clientes/{id}/ventas` con renglones duplica trabajo que C-06 optimizará** → mitigación: C-03 entrega el contrato con precarga funcional; C-06 refactoriza el conteo de consultas sin cambiar códigos ni payload (ya previsto en su scope).
- **Mensaje de nombre duplicado de editorial/género no está en la KB** → mitigación: se adopta "El nombre ya está registrado" (propio, sin texto interno) y se registra como decisión; si la corrección pide otro texto, es un cambio de una constante.
- **`Decimal` como string depende de Pydantic v2** → mitigación: test de contrato aserta que `precio` sale como `"25000.00"` (string), no número.

## Migration Plan

Sin migración de datos ni de esquema: los endpoints son aditivos sobre las tablas de C-02. Sobre una base ya creada por C-02, el próximo arranque no altera el esquema (RN-G-05). No hay rollback de datos; ante un error de código se revierte el commit y se redeploya.

## Open Questions

Ninguna que cambie specs, enfoque o desglose de tareas. Las decisiones de IN-01 (PATCH escalar), RN-10 (paginación en toda colección) e IN-02 (409 para `genero_id` inexistente, heredado en el mapa de FK) ya están cerradas por `knowledge-base/10_preguntas_abiertas.md` y `CHANGES.md`.
