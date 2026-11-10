# Design

## Context

C-03 dejó `schemas.py`/`service.py`/`router.py` en editoriales, géneros, autores, clientes y libros, con `app/core/errors.py` (mapa constraint → mensaje propio + 409) y `app/core/pagination.py`. El módulo `ventas` solo tiene `models.py` (C-02): `Venta` (`fecha DateTime(timezone=True)` con default UTC, `total Numeric(12,2)` CHECK `>= 0`), `RenglonVenta` (`venta_id` FK `ondelete="CASCADE"`, `libro_id` FK, `cantidad` CHECK `> 0`, `precio_unitario Numeric(10,2)` CHECK `> 0`) y `Venta.renglones` con `cascade="all, delete-orphan"`. `libros/schemas.py` ya tiene `LibroDetalleRead` y `LibroAutorRead`; `clientes/schemas.py` ya define `ClienteResumenRead`, `RenglonRead` y `VentaRead` (usados por `GET /clientes/{id}/ventas`).

Restricciones que condicionan el diseño:

- `lazy="raise"` en todas las relaciones (RN-G-03): toda lectura relacional precarga; un acceso perezoso lanza `InvalidRequestError`.
- Dinero `Decimal`/`Numeric` serializado como string decimal (RN-G-01); Pydantic v2 serializa `Decimal` a string.
- `IntegrityError` → 409 con mensaje propio por nombre de constraint; nunca `str(exc)` (RN-12, DD-05).
- Sin consulta previa de existencia en las altas (DD-05, Ejercicio 4): se escribe y se traduce el rechazo de la base.
- `fecha` de la venta en UTC, ISO 8601 con microsegundos y sufijo `Z` (IN-05 resuelto); si Pydantic emite `+00:00`, se normaliza en el DTO.

## Goals / Non-Goals

**Goals:**

- `POST /libros/` con `LibroCreate` + `autores: list[AutorLibroCreate]`, un único `commit`, y releída del detalle con precarga.
- Módulo `ventas` completo (`schemas.py`, `service.py`, `router.py`) con `POST /ventas/` que carga libros en una sola consulta, copia precio, calcula total y persiste por composición.
- Serialización de `fecha` con sufijo `Z` en el DTO de salida de la venta.

**Non-Goals:**

- `GET /ventas/`, `GET /ventas/{id}` y el conteo fijo de consultas de lectura (C-06); el aviso en `BackgroundTasks` (C-07).
- No hay `PATCH`/`PUT`/`DELETE` de ventas (RN-08, DD-03) ni alta de renglones por separado (RN-04).
- No se altera el esquema ni los endpoints ya existentes de C-03.

## Decisions

### 1. DTO de entrada de libro: `LibroCreate` y `AutorLibroCreate`

En `app/modules/libros/schemas.py`:

```python
VALORES_ROL = ("autor", "coautor", "traductor", "ilustrador")

class AutorLibroCreate(SQLModel):
    autor_id: int
    rol: Literal["autor", "coautor", "traductor", "ilustrador"]
    orden: int = Field(ge=1)

class LibroCreate(SQLModel):
    isbn: str
    titulo: str
    precio: Decimal = Field(gt=0)
    stock: int = Field(ge=0)
    editorial_id: int
    genero_id: int | None = None
    autores: list[AutorLibroCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _autores_sin_repetir(self):
        ids = [a.autor_id for a in self.autores]
        if len(ids) != len(set(ids)):
            raise ValueError("El autor no puede repetirse en el mismo libro")
        return self
```

- `rol` se valida con `Literal` (los cuatro valores de `libros/models.py:VALORES_ROL`, SU-02) y `orden` con `Field(ge=1)`; ambos → 422.
- `autores` exige `min_length=1` y el validador rechaza `autor_id` repetido en el mismo payload → 422 (RN-05 por analogía, aunque es autoría y no renglón). La PK compuesta `(libro_id, autor_id)` de `libro_autor` sigue siendo la defensa en base: si aun así se intentara un autor repetido, PostgreSQL lo rechaza con `libro_autor_pkey`.

**Alternativa considerada**: dejar el autor repetido solo a la base (409 por PK). Descartada en el borde: es un error de contrato detectable sin escribir y la consigna pide validar `libro_id` repetido en ventas de forma análoga.

### 2. DTO de entrada de venta: `VentaCreate` y `RenglonCreate`

En el nuevo `app/modules/ventas/schemas.py`:

```python
class RenglonCreate(SQLModel):
    libro_id: int
    cantidad: int = Field(gt=0)

class VentaCreate(SQLModel):
    cliente_id: int
    renglones: list[RenglonCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _libros_sin_repetir(self):
        ids = [r.libro_id for r in self.renglones]
        if len(ids) != len(set(ids)):
            raise ValueError("El libro no puede repetirse en la venta")
        return self
```

- `cantidad > 0` (RN-05), `min_length=1` y rechazo de `libro_id` repetido → 422.
- No se declaran `precio_unitario`, `total` ni `fecha` (RN-06, RN-07, RN-G-06). El comportamiento por defecto de Pydantic **ignora** campos extra; se documenta que esos campos "no se aceptan" (el flujo 3 de la KB admite "se ignoran o se rechazan"). Si se quisiera rechazar estrictamente, se pondría `model_config = ConfigDict(extra="forbid")`; se deja como decisión del apply, sin cambiar el contrato (el precio/total/fecha nunca se toman del cuerpo).

### 3. DTO de salida de la venta y serialización de `fecha`

Los DTO de salida de venta viven hoy en `clientes/schemas.py` (`ClienteResumenRead`, `RenglonRead`, `VentaRead`). Para que `ventas` sea dueño de su contrato, se **mueven** a `ventas/schemas.py` y `clientes/schemas.py` los reexporta, de modo que `clientes/service.py` y `clientes/router.py` siguen importando desde `clientes.schemas` sin cambios:

```python
# ventas/schemas.py
from pydantic import field_serializer
from datetime import datetime

class ClienteResumenRead(SQLModel):
    id: int
    nombre: str
    email: str

class RenglonRead(SQLModel):
    libro_id: int
    titulo: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal

class VentaRead(SQLModel):
    id: int
    fecha: datetime
    total: Decimal
    cliente: ClienteResumenRead
    renglones: list[RenglonRead]

    @field_serializer("fecha")
    def _fecha_z(self, valor: datetime) -> str:
        return valor.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
```

- `RenglonRead` ya incluye `titulo` y `subtotal` (calculado en el DTO, `cantidad × precio_unitario`), como pide el contrato.
- El `field_serializer` de `fecha` normaliza el `+00:00` de Pydantic a `Z` (IN-05). Se aplica también a `GET /clientes/{id}/ventas`, que pasa a emitir el mismo formato coherente.
- No hay ciclo de imports en runtime: `ventas/schemas.py` no importa de `clientes`; `clientes/schemas.py` importa de `ventas/schemas.py`. Los `TYPE_CHECKING` cruzados de `models.py` no importan en runtime.

**Alternativa considerada**: duplicar los DTO en `ventas` y dejar los de `clientes` duplicados. Descartada: dos fuentes de verdad para el mismo contrato.

### 4. `libros/service.py`: `crear` sin `SELECT` previo

```python
async def crear(session, datos: LibroCreate) -> LibroDetalleRead:
    libro = Libro(
        isbn=datos.isbn, titulo=datos.titulo, precio=datos.precio,
        stock=datos.stock, editorial_id=datos.editorial_id, genero_id=datos.genero_id,
        autorias=[
            LibroAutor(autor_id=a.autor_id, rol=a.rol, orden=a.orden) for a in datos.autores
        ],
    )
    session.add(libro)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    return await obtener(session, libro.id)
```

- **No** hay `SELECT` de editorial/género/autor: se asignan los ids tal como llegan y la FK dispara `IntegrityError` (DD-05). Las autorías se agregan a `libro.autorias` (composición de la relación) en el mismo `add`.
- `obtener` (ya existente en C-03) relee con `joinedload` de editorial/género y `selectinload(Libro.autorias).joinedload(LibroAutor.autor)`; con `expire_on_commit=False` los atributos escalares sobreviven al commit y la releída solo precarga relaciones.
- El `isbn`/FK/CHECK los valida la base; el mapa de `errors.py` cubre `uq_libro_isbn`, `fk_libro_editorial_id`, `fk_libro_genero_id` y `fk_libro_autor_autor_id`.

### 5. Constraint de autoría duplicada (`libro_autor`)

La PK compuesta `(libro_id, autor_id)` de `libro_autor` no tiene nombre explícito en C-02; PostgreSQL la nombra por convención `libro_autor_pkey`. Se amplía el mapa de `app/core/errors.py` con:

| Constraint | Mensaje (409) |
|---|---|
| `libro_autor_pkey` | "El autor ya está asociado a este libro" |

- En la práctica el autor repetido se detecta **antes** en el validador del DTO (422); el mapa es la red de seguridad si el duplicado llega a la base (p. ej. una corrida concurrente). Como `LibroAutor` es una entidad recién creada (no hay libro preexistente en `POST /libros/`), la vía real es el 422 del validador.
- Si el nombre real del constraint difiriera, el fallback es el 409 genérico ("Conflicto con los datos existentes"), sin exponer el nombre (RN-12); un test de integración contra PostgreSQL verificará el nombre real y, si hace falta, se ajusta la clave del mapa.

**Alternativa considerada**: mapear por fragmento del mensaje de PostgreSQL. Descartada por RN-12 y fragilidad.

### 6. `ventas/service.py`: `crear` con una sola consulta de libros

```python
async def crear(session, datos: VentaCreate) -> VentaRead:
    ids = [r.libro_id for r in datos.renglones]
    resultado = await session.execute(select(Libro).where(Libro.id.in_(ids)))
    libros = {l.id: l for l in resultado.scalars().all()}
    faltante = next((i for i in ids if i not in libros), None)
    if faltante is not None:
        raise HTTPException(status_code=409, detail="El libro indicado no existe")

    venta = Venta(cliente_id=datos.cliente_id, total=Decimal("0.00"))
    for r in datos.renglones:
        libro = libros[r.libro_id]
        venta.renglones.append(RenglonVenta(
            libro_id=r.libro_id, cantidad=r.cantidad, precio_unitario=libro.precio,
        ))
    venta.total = sum((rg.cantidad * rg.precio_unitario for rg in venta.renglones), Decimal("0.00"))
    venta.fecha = datetime.now(timezone.utc)

    session.add(venta)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None

    return await _releer(session, venta.id)
```

- Los libros se cargan en **una** consulta (`WHERE id IN (...)`), nunca N selects (postgresql-optimization). El `titulo` y el `precio` salen de esos objetos.
- Libro faltante → 409 con "El libro indicado no existe" (RI-04, C-05). Es equivalente y más explícito que dejar que la FK `fk_renglon_venta_libro_id` falle (flujo 3 de la KB admite ambas); se elige la detección por mensaje claro y para no depender del orden de inserción.
- Cliente inexistente → la FK `fk_venta_cliente_id` dispara `IntegrityError` → 409 "El cliente indicado no existe" (RI-03); **no** se hace `SELECT` previo del cliente (DD-05).
- `precio_unitario = libro.precio` es una **copia** (RN-06): cambiar el precio del libro después no altera el renglón ya persistido. `total = sum(cantidad × precio_unitario)` en `Decimal` (RN-07).
- `fecha = datetime.now(timezone.utc)` explícita (IN-05); el default de la columna existe pero se fija acá para claridad y test. Se usa `datetime.now(timezone.utc)`, nunca `datetime.utcnow()`.
- `_releer` hace `select(Venta).where(Venta.id == ...).options(joinedload(Venta.cliente), selectinload(Venta.renglones).joinedload(RenglonVenta.libro))` y arma `VentaRead` con `subtotal = cantidad × precio_unitario` por renglón (contrato de salida). C-06 reutilizará esta precarga.

### 7. `ventas/router.py` y registro

```python
router = APIRouter(prefix="/ventas", tags=["Ventas"])

@router.post("/", response_model=VentaRead, status_code=status.HTTP_201_CREATED)
async def crear(datos: VentaCreate, session: SessionDep) -> VentaRead:
    return await service.crear(session, datos)
```

Se agrega `include_router(ventas_router)` en `app/main.py` (el módulo `ventas` hoy no tiene router). No se agregan `PATCH`/`PUT`/`DELETE` (RN-08). `libros/router.py` agrega el `POST /libros/` con `response_model=LibroDetalleRead` y `status_code=201`.

## Risks / Trade-offs

- **Nombre real de la PK de `libro_autor` podría no ser `libro_autor_pkey`** → un test de integración contra PostgreSQL lo confirma; si difiere, se ajusta una clave del mapa. El fallback es 409 genérico, nunca 500 ni el texto del constraint.
- **Acceso perezoso olvidado (`lazy="raise"`)** → las releídas usan `joinedload`/`selectinload`; los tests de contrato ejercitan las dos altas con relaciones.
- **`SELECT` de existencia accidental** → el test con `SQL_ECHO` asevera que el alta de libro no emite `SELECT` de editorial/género/autor y que la venta hace una sola consulta de libros antes del `INSERT`.
- **Mover los DTO de venta a `ventas/schemas.py`** toca `clientes/schemas.py` → es un cambio de ubicación de import (reexport), sin cambio de comportamiento; los tests de C-03 siguen pasando. Riesgo de ciclo de import descartado por la dirección de las dependencias (ventas no importa de clientes en schemas).
- **Campos extra (`precio_unitario`/`total`/`fecha`) en el cuerpo** → Pydantic los ignora por defecto; el contrato dice "no se aceptan". Si la corrección esperara 422 estricto, se activa `extra="forbid"` en `VentaCreate`/`RenglonCreate` (cambio acotado al DTO, sin tocar servicio ni router).

## Migration Plan

Sin migración de datos ni de esquema: los cambios son aditivos (dos endpoints y un módulo). Sobre la base ya creada por C-02 no se altera el esquema (RN-G-05). No hay rollback de datos: ante un error se revierte el commit y se redeploya. La única tarea "no aditiva" es el reexport de los DTO de venta en `clientes/schemas.py`, que es transparente para el resto del código.

## Open Questions

Ninguna que cambie specs, enfoque o desglose. Los puntos de borde (nombre exacto de `libro_autor_pkey` y si los campos extra del cuerpo se ignoran o se rechazan) se resuelven con un test de integración y una constante del DTO, respectivamente, sin alterar el contrato.
