"""Pruebas transversales de tipos y creación del esquema (C-02)."""

import os
from decimal import Decimal

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlmodel import SQLModel

TABLAS_DOMINIO = {
    "editorial",
    "genero",
    "autor",
    "libro",
    "libro_autor",
    "cliente",
    "perfil_cliente",
    "venta",
    "renglon_venta",
}


def _tabla(nombre: str) -> sa.Table:
    return SQLModel.metadata.tables[nombre]


def test_nueve_tablas_registradas_en_metadata():
    assert TABLAS_DOMINIO <= set(SQLModel.metadata.tables.keys())


def test_importes_son_decimal_en_python():
    from app.modules.libros.models import Libro
    from app.modules.ventas.models import RenglonVenta, Venta

    libro = Libro(isbn="x", titulo="y", precio=Decimal("25000.00"), stock=1, editorial_id=1)
    venta = Venta(cliente_id=1, total=Decimal("50000.00"))
    renglon = RenglonVenta(venta_id=1, libro_id=1, cantidad=2, precio_unitario=Decimal("25000.00"))

    assert isinstance(libro.precio, Decimal)
    assert isinstance(venta.total, Decimal)
    assert isinstance(renglon.precio_unitario, Decimal)


def test_importes_son_numeric_en_metadata():
    assert isinstance(_tabla("libro").columns["precio"].type, sa.Numeric)
    assert isinstance(_tabla("venta").columns["total"].type, sa.Numeric)
    assert isinstance(_tabla("renglon_venta").columns["precio_unitario"].type, sa.Numeric)


@pytest_asyncio.fixture
async def esquema_creado():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("requiere DATABASE_URL y un PostgreSQL accesible")

    from app.core.config import get_settings
    from app.core.database import build_engine

    motor = build_engine(get_settings())
    async with motor.begin() as conexion:
        await conexion.run_sync(SQLModel.metadata.create_all)
    yield
    await motor.dispose()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requiere DATABASE_URL y un PostgreSQL accesible",
)
async def test_create_all_crea_las_nueve_tablas(esquema_creado):
    from sqlalchemy import inspect

    from app.core.config import get_settings
    from app.core.database import build_engine

    motor = build_engine(get_settings())

    async def _tablas_existentes() -> set[str]:
        async with motor.connect() as conexion:
            return set(await conexion.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))

    try:
        tablas = await _tablas_existentes()
        assert TABLAS_DOMINIO <= tablas
    finally:
        await motor.dispose()
