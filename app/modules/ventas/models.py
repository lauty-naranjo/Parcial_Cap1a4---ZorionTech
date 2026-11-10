"""Modelos de tabla del módulo ventas: venta y renglones por composición (C-02)."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import Libro


def utc_now() -> datetime:
    """Fecha y hora actuales en UTC con zona horaria (IN-05)."""
    return datetime.now(timezone.utc)


class Venta(SQLModel, table=True):
    """Hecho de venta inmutable (RN-08); composición con sus renglones."""

    __tablename__ = "venta"
    __table_args__ = (sa.CheckConstraint("total >= 0", name="ck_venta_total_no_negativo"),)

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("cliente.id", name="fk_venta_cliente_id"),
            nullable=False,
            index=True,
        ),
    )
    fecha: datetime = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, default=utc_now),
    )
    total: Decimal = Field(
        default=None,
        sa_column=sa.Column(sa.Numeric(12, 2), nullable=False, default=Decimal("0.00")),
    )

    cliente: "Cliente" = Relationship(
        back_populates="ventas",
        sa_relationship_kwargs={"lazy": "raise"},
    )
    renglones: list["RenglonVenta"] = Relationship(
        back_populates="venta",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "raise",
        },
    )


class RenglonVenta(SQLModel, table=True):
    """Renglón de una venta; nace y muere con ella (composición)."""

    __tablename__ = "renglon_venta"
    __table_args__ = (
        sa.CheckConstraint("cantidad > 0", name="ck_renglon_venta_cantidad_positiva"),
        sa.CheckConstraint("precio_unitario > 0", name="ck_renglon_venta_precio_positivo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    venta_id: int = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("venta.id", name="fk_renglon_venta_venta_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    libro_id: int = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("libro.id", name="fk_renglon_venta_libro_id"),
            nullable=False,
            index=True,
        ),
    )
    cantidad: int = Field(sa_column=sa.Column(sa.Integer, nullable=False))
    precio_unitario: Decimal = Field(sa_column=sa.Column(sa.Numeric(10, 2), nullable=False))

    venta: "Venta" = Relationship(
        back_populates="renglones",
        sa_relationship_kwargs={"lazy": "raise"},
    )
    libro: "Libro" = Relationship(
        back_populates="renglones",
        sa_relationship_kwargs={"lazy": "raise"},
    )
