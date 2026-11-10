"""Modelos de tabla del módulo libros: libro y su autoría (C-02)."""

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.autores.models import Autor
    from app.modules.editoriales.models import Editorial
    from app.modules.generos.models import Genero
    from app.modules.ventas.models import RenglonVenta

VALORES_ROL = ("autor", "coautor", "traductor", "ilustrador")


class Libro(SQLModel, table=True):
    """Libro del catálogo; agregación con editorial y género (opcional)."""

    __tablename__ = "libro"
    __table_args__ = (
        sa.UniqueConstraint("isbn", name="uq_libro_isbn"),
        sa.CheckConstraint("precio > 0", name="ck_libro_precio_positivo"),
        sa.CheckConstraint("stock >= 0", name="ck_libro_stock_no_negativo"),
        sa.Index("ix_libro_titulo", "titulo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))
    titulo: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))
    precio: Decimal = Field(sa_column=sa.Column(sa.Numeric(10, 2), nullable=False))
    stock: int = Field(sa_column=sa.Column(sa.Integer, nullable=False))
    editorial_id: int = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("editorial.id", name="fk_libro_editorial_id"),
            nullable=False,
            index=True,
        ),
    )
    genero_id: int | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("genero.id", name="fk_libro_genero_id"),
            nullable=True,
            index=True,
        ),
    )

    editorial: "Editorial" = Relationship(
        back_populates="libros",
        sa_relationship_kwargs={"lazy": "raise"},
    )
    genero: Optional["Genero"] = Relationship(
        back_populates="libros",
        sa_relationship_kwargs={"lazy": "raise"},
    )
    autorias: list["LibroAutor"] = Relationship(
        back_populates="libro",
        sa_relationship_kwargs={"lazy": "raise"},
    )
    renglones: list["RenglonVenta"] = Relationship(
        back_populates="libro",
        sa_relationship_kwargs={"lazy": "raise"},
    )


class LibroAutor(SQLModel, table=True):
    """Autoría: objeto de asociación entre libro y autor con rol y orden."""

    __tablename__ = "libro_autor"
    __table_args__ = (
        sa.CheckConstraint(
            f"rol IN ({', '.join(repr(v) for v in VALORES_ROL)})",
            name="ck_libro_autor_rol",
        ),
        sa.CheckConstraint("orden >= 1", name="ck_libro_autor_orden"),
    )

    libro_id: int = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("libro.id", name="fk_libro_autor_libro_id"),
            primary_key=True,
        ),
    )
    autor_id: int = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("autor.id", name="fk_libro_autor_autor_id"),
            primary_key=True,
            index=True,
        ),
    )
    rol: str = Field(sa_column=sa.Column(sa.String(20), nullable=False))
    orden: int = Field(sa_column=sa.Column(sa.Integer, nullable=False))

    libro: "Libro" = Relationship(
        back_populates="autorias",
        sa_relationship_kwargs={"lazy": "raise"},
    )
    autor: "Autor" = Relationship(
        back_populates="autorias",
        sa_relationship_kwargs={"lazy": "raise"},
    )
