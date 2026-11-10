"""DTO de entrada y salida del módulo libros (C-03, lectura y edición)."""

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator
from sqlmodel import SQLModel

from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead


class AutorLibroCreate(SQLModel):
    """Autoría de entrada: ``rol`` entre los cuatro valores y ``orden`` >= 1."""

    autor_id: int
    rol: Literal["autor", "coautor", "traductor", "ilustrador"]
    orden: int = Field(ge=1)


class LibroCreate(SQLModel):
    """Cuerpo de alta de libro con editorial, género opcional y autorías."""

    isbn: str
    titulo: str
    precio: Decimal = Field(gt=0)
    stock: int = Field(ge=0)
    editorial_id: int
    genero_id: int | None = None
    autores: list[AutorLibroCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _autores_sin_repetir(self) -> "LibroCreate":
        ids = [a.autor_id for a in self.autores]
        if len(ids) != len(set(ids)):
            raise ValueError("El autor no puede repetirse en el mismo libro")
        return self


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
