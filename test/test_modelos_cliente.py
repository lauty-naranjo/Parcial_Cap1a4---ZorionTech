"""Pruebas de metadata de cliente y perfil uno a uno (C-02)."""

import sqlalchemy as sa
from sqlmodel import SQLModel


def _tabla(nombre: str) -> sa.Table:
    return SQLModel.metadata.tables[nombre]


def _nombres(tabla: sa.Table, tipo: type) -> set[str]:
    return {c.name for c in tabla.constraints if isinstance(c, tipo)}


def test_cliente_tiene_columnas_exactas():
    tabla = _tabla("cliente")

    assert set(tabla.columns.keys()) == {"id", "nombre", "email"}


def test_cliente_email_unico_y_not_null():
    tabla = _tabla("cliente")

    assert tabla.columns["email"].nullable is False
    assert "uq_cliente_email" in _nombres(tabla, sa.UniqueConstraint)


def test_perfil_cliente_tiene_columnas_exactas():
    tabla = _tabla("perfil_cliente")

    assert set(tabla.columns.keys()) == {"id", "cliente_id", "telefono", "direccion"}


def test_perfil_cliente_cliente_id_unico_y_fk():
    tabla = _tabla("perfil_cliente")

    assert tabla.columns["cliente_id"].nullable is False
    assert "uq_perfil_cliente_cliente_id" in _nombres(tabla, sa.UniqueConstraint)
    assert "fk_perfil_cliente_cliente_id" in _nombres(tabla, sa.ForeignKeyConstraint)


def test_cliente_perfil_es_escalar():
    from app.modules.clientes.models import Cliente

    rel = Cliente.__mapper__.relationships["perfil"]

    assert rel.uselist is False
    assert rel.back_populates == "cliente"
    assert rel.mapper.class_.__name__ == "PerfilCliente"


def test_cliente_ventas_relacion_bidireccional():
    from app.modules.clientes.models import Cliente

    rel = Cliente.__mapper__.relationships["ventas"]

    assert rel.back_populates == "cliente"
    assert rel.mapper.class_.__name__ == "Venta"
