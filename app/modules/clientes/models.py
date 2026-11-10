"""Modelos de tabla del módulo clientes: cliente y perfil uno a uno (C-02)."""

from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.ventas.models import Venta


class Cliente(SQLModel, table=True):
    """Cliente del dominio; email único (RN-02)."""

    __tablename__ = "cliente"
    __table_args__ = (sa.UniqueConstraint("email", name="uq_cliente_email"),)

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))
    email: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))

    perfil: Optional["PerfilCliente"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"uselist": False, "lazy": "raise"},
    )
    ventas: list["Venta"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"lazy": "raise"},
    )


class PerfilCliente(SQLModel, table=True):
    """Perfil del cliente; la FK UNIQUE garantiza uno a uno (RN-09)."""

    __tablename__ = "perfil_cliente"
    __table_args__ = (sa.UniqueConstraint("cliente_id", name="uq_perfil_cliente_cliente_id"),)

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(
        default=None,
        sa_column=sa.Column(
            sa.Integer,
            sa.ForeignKey("cliente.id", name="fk_perfil_cliente_cliente_id"),
            nullable=False,
            index=True,
        ),
    )
    telefono: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))
    direccion: str = Field(sa_column=sa.Column(sa.String(255), nullable=False))

    cliente: "Cliente" = Relationship(
        back_populates="perfil",
        sa_relationship_kwargs={"lazy": "raise"},
    )
