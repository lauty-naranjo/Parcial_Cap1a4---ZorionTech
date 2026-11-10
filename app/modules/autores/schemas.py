"""DTO de entrada y salida del módulo autores (C-03)."""

from sqlmodel import SQLModel

from app.modules.editoriales.schemas import EditorialRead


class AutorCreate(SQLModel):
    """Cuerpo de alta de un autor."""

    nombre: str
    nacionalidad: str


class AutorUpdate(SQLModel):
    """Cuerpo de PATCH: campos opcionales."""

    nombre: str | None = None
    nacionalidad: str | None = None


class AutorRead(SQLModel):
    """Contrato de lectura: ``id``, ``nombre`` y ``nacionalidad``."""

    id: int
    nombre: str
    nacionalidad: str


class AutorLibroRead(SQLModel):
    """Libro de un autor con el ``rol`` y ``orden`` de su autoría."""

    libro_id: int
    titulo: str
    rol: str
    orden: int
    editorial: EditorialRead
