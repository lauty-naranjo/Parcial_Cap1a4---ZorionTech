"""DTO de entrada y salida del módulo editoriales (C-03)."""

from pydantic import model_validator
from sqlmodel import SQLModel

from app.core.schemas import rechazar_nulos_explicitos


class EditorialCreate(SQLModel):
    """Cuerpo de alta: sin ``id`` (lo genera la base)."""

    nombre: str
    pais: str


class EditorialUpdate(SQLModel):
    """Cuerpo de PATCH: todos los campos opcionales (parcial)."""

    nombre: str | None = None
    pais: str | None = None

    @model_validator(mode="after")
    def _sin_nulos_explicitos(self) -> "EditorialUpdate":
        rechazar_nulos_explicitos(self, ("nombre", "pais"))
        return self


class EditorialRead(SQLModel):
    """Contrato de lectura: ``id``, ``nombre`` y ``pais``."""

    id: int
    nombre: str
    pais: str
