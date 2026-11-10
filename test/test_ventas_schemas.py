"""Pruebas de los DTO de venta (C-04): entrada validada y fecha con sufijo ``Z``."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.clientes.schemas import ClienteResumenRead, RenglonRead, VentaRead
from app.modules.ventas.schemas import RenglonCreate, VentaCreate


def test_reexport_desde_clientes_es_la_misma_clase():
    from app.modules.ventas.schemas import VentaRead as VentaReadDeVentas

    assert VentaRead is VentaReadDeVentas


def test_renglon_create_rechaza_cantidad_cero():
    with pytest.raises(ValidationError):
        RenglonCreate(libro_id=1, cantidad=0)


def test_venta_create_rechaza_renglones_vacio():
    with pytest.raises(ValidationError):
        VentaCreate(cliente_id=1, renglones=[])


def test_venta_create_rechaza_cantidad_no_positiva():
    with pytest.raises(ValidationError):
        VentaCreate(cliente_id=1, renglones=[RenglonCreate(libro_id=1, cantidad=-1)])


def test_venta_create_rechaza_libro_repetido():
    with pytest.raises(ValidationError):
        VentaCreate(
            cliente_id=1,
            renglones=[
                RenglonCreate(libro_id=1, cantidad=1),
                RenglonCreate(libro_id=1, cantidad=2),
            ],
        )


def test_venta_create_acepta_dos_renglones_distintos():
    venta = VentaCreate(
        cliente_id=1,
        renglones=[
            RenglonCreate(libro_id=1, cantidad=2),
            RenglonCreate(libro_id=2, cantidad=1),
        ],
    )

    assert len(venta.renglones) == 2


def test_venta_read_serializa_fecha_con_z():
    fecha = datetime(2026, 10, 8, 21, 14, 11, 751581, tzinfo=timezone.utc)
    venta = VentaRead(
        id=2,
        fecha=fecha,
        total=Decimal("77000.00"),
        cliente=ClienteResumenRead(id=2, nombre="Tomás Ríos", email="tomas@example.com"),
        renglones=[
            RenglonRead(
                libro_id=1,
                titulo="Rayuela",
                cantidad=2,
                precio_unitario=Decimal("25000.00"),
                subtotal=Decimal("50000.00"),
            )
        ],
    )

    json_str = venta.model_dump_json()

    assert '"fecha":"2026-10-08T21:14:11.751581Z"' in json_str
    assert "+00:00" not in json_str
