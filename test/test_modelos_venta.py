"""Pruebas de metadata de venta y renglones por composición (C-02)."""

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlmodel import SQLModel


def _tabla(nombre: str) -> sa.Table:
    return SQLModel.metadata.tables[nombre]


def _nombres(tabla: sa.Table, tipo: type) -> set[str]:
    return {c.name for c in tabla.constraints if isinstance(c, tipo)}


def test_venta_tiene_columnas_exactas():
    tabla = _tabla("venta")

    assert set(tabla.columns.keys()) == {"id", "cliente_id", "fecha", "total"}


def test_venta_checks_y_fk():
    tabla = _tabla("venta")

    assert "ck_venta_total_no_negativo" in _nombres(tabla, sa.CheckConstraint)
    assert "fk_venta_cliente_id" in _nombres(tabla, sa.ForeignKeyConstraint)
    assert tabla.columns["cliente_id"].nullable is False


def test_venta_total_es_numeric_12_2_con_default_decimal():
    tabla = _tabla("venta")
    columna = tabla.columns["total"]

    assert isinstance(columna.type, sa.Numeric)
    assert columna.type.precision == 12
    assert columna.type.scale == 2
    assert columna.default.arg == Decimal("0.00")


def test_venta_fecha_es_tz_aware_utc():
    from app.modules.ventas.models import utc_now

    tabla = _tabla("venta")
    columna = tabla.columns["fecha"]

    assert isinstance(columna.type, sa.DateTime)
    assert columna.type.timezone is True
    assert columna.default is not None

    ahora = utc_now()
    assert isinstance(ahora, datetime)
    assert ahora.tzinfo is not None
    assert ahora.utcoffset() == timezone.utc.utcoffset(None)


def test_renglon_venta_tiene_columnas_exactas():
    tabla = _tabla("renglon_venta")

    assert set(tabla.columns.keys()) == {
        "id",
        "venta_id",
        "libro_id",
        "cantidad",
        "precio_unitario",
    }


def test_renglon_venta_checks_y_fks():
    tabla = _tabla("renglon_venta")
    checks = _nombres(tabla, sa.CheckConstraint)
    fks = _nombres(tabla, sa.ForeignKeyConstraint)

    assert "ck_renglon_venta_cantidad_positiva" in checks
    assert "ck_renglon_venta_precio_positivo" in checks
    assert "fk_renglon_venta_venta_id" in fks
    assert "fk_renglon_venta_libro_id" in fks


def test_renglon_venta_precio_unitario_es_numeric_10_2():
    tabla = _tabla("renglon_venta")
    columna = tabla.columns["precio_unitario"].type

    assert isinstance(columna, sa.Numeric)
    assert columna.precision == 10
    assert columna.scale == 2


def test_renglon_venta_venta_id_cascadea_en_borrado():
    tabla = _tabla("renglon_venta")
    fk = next(c for c in tabla.foreign_keys if c.parent.name == "venta_id")

    assert fk.ondelete == "CASCADE"


def test_venta_renglones_por_composicion():
    from app.modules.ventas.models import Venta

    rel = Venta.__mapper__.relationships["renglones"]

    assert rel.back_populates == "venta"
    assert rel.mapper.class_.__name__ == "RenglonVenta"
    assert "delete-orphan" in rel.cascade
    assert rel.passive_deletes is True
    assert rel.lazy == "raise"


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requiere DATABASE_URL y un PostgreSQL accesible",
)
async def test_venta_con_renglones_se_persiste_y_cascadea():
    """Persiste una venta por composición y verifica el ON DELETE CASCADE.

    Todo corre dentro de una transacción que se revierte al final, de modo que
    no queda basura en la base real del desarrollador.
    """
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.core.database import build_engine, build_session_factory
    from app.modules.clientes.models import Cliente
    from app.modules.editoriales.models import Editorial
    from app.modules.libros.models import Libro
    from app.modules.ventas.models import RenglonVenta, Venta

    motor = build_engine(get_settings())
    fabrica = build_session_factory(motor)
    async with motor.begin() as conexion:
        await conexion.run_sync(SQLModel.metadata.create_all)

    try:
        async with fabrica() as sesion:
            editorial = Editorial(nombre="Editorial C02 test", pais="Argentina")
            sesion.add(editorial)
            await sesion.flush()

            libro = Libro(
                isbn="c02-integracion",
                titulo="Libro C02 test",
                precio=Decimal("100.00"),
                stock=5,
                editorial_id=editorial.id,
            )
            sesion.add(libro)
            await sesion.flush()

            cliente = Cliente(nombre="Cliente C02 test", email="c02-integracion@example.com")
            sesion.add(cliente)
            await sesion.flush()

            venta = Venta(cliente_id=cliente.id)
            venta.renglones = [
                RenglonVenta(libro_id=libro.id, cantidad=1, precio_unitario=Decimal("100.00")),
                RenglonVenta(libro_id=libro.id, cantidad=2, precio_unitario=Decimal("100.00")),
            ]
            sesion.add(venta)
            await sesion.flush()

            resultado = await sesion.execute(
                select(RenglonVenta).where(RenglonVenta.venta_id == venta.id)
            )
            assert len(resultado.scalars().all()) == 2

            await sesion.delete(venta)
            await sesion.flush()

            resultado = await sesion.execute(
                select(RenglonVenta).where(RenglonVenta.venta_id == venta.id)
            )
            assert resultado.scalars().all() == []

            await sesion.rollback()
    finally:
        await motor.dispose()
