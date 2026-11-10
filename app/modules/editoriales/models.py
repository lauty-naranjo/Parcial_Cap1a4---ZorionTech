"""Modelo de tabla del módulo editoriales (C-02)."""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.libros.models import Libro


class Editorial(SQLModel, table=True):
    """Editorial del catálogo; existe por sí misma (agregación)."""

    __tablename__ = "editorial"
    __table_args__ = (sa.UniqueConstraint("nombre", name="uq_editorial_nombre"),)

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))
    pais: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))

    libros: list["Libro"] = Relationship(
        back_populates="editorial",
        sa_relationship_kwargs={"lazy": "raise"},
    )
