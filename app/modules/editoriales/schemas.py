"""DTO de entrada y salida del módulo editoriales (C-03)."""

from sqlmodel import SQLModel


class EditorialCreate(SQLModel):
    """Cuerpo de alta: sin ``id`` (lo genera la base)."""

    nombre: str
    pais: str


class EditorialUpdate(SQLModel):
    """Cuerpo de PATCH: todos los campos opcionales (parcial)."""

    nombre: str | None = None
    pais: str | None = None


class EditorialRead(SQLModel):
    """Contrato de lectura: ``id``, ``nombre`` y ``pais``."""

    id: int
    nombre: str
    pais: str
