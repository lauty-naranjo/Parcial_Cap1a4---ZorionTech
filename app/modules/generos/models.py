"""Modelo de tabla del módulo generos (C-02)."""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.libros.models import Libro


class Genero(SQLModel, table=True):
    """Género del catálogo; agregación opcional desde el libro."""

    __tablename__ = "genero"
    __table_args__ = (sa.UniqueConstraint("nombre", name="uq_genero_nombre"),)

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))

    libros: list["Libro"] = Relationship(
        back_populates="genero",
        sa_relationship_kwargs={"lazy": "raise"},
    )
