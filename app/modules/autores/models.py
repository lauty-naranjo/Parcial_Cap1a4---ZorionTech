"""Modelo de tabla del módulo autores (C-02)."""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.libros.models import LibroAutor


class Autor(SQLModel, table=True):
    """Autor del catálogo; sin unicidad de nombre (restricción de la consigna)."""

    __tablename__ = "autor"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))
    nacionalidad: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))

    autorias: list["LibroAutor"] = Relationship(
        back_populates="autor",
        sa_relationship_kwargs={"lazy": "raise"},
    )
