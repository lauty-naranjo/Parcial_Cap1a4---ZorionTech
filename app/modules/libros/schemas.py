"""DTO de entrada y salida del módulo libros (C-03, lectura y edición)."""

from decimal import Decimal

from pydantic import Field
from sqlmodel import SQLModel

from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead


class LibroRead(SQLModel):
    """Contrato de listado: editorial y género anidados, ``precio`` decimal."""

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: EditorialRead
    genero: GeneroRead | None = None


class LibroAutorRead(SQLModel):
    """Autoría en el detalle de un libro: ``autor_id``, ``nombre``, ``rol``, ``orden``."""

    autor_id: int
    nombre: str
    rol: str
    orden: int


class LibroDetalleRead(LibroRead):
    """Contrato de detalle: lo del listado más la lista de autores."""

    autores: list[LibroAutorRead]


class LibroUpdate(SQLModel):
    """PATCH de libro: solo campos escalares, sin ``autores`` (IN-01)."""

    isbn: str | None = None
    titulo: str | None = None
    precio: Decimal | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    editorial_id: int | None = None
    genero_id: int | None = None
