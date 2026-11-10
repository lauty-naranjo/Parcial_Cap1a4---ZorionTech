"""Lógica de negocio del módulo ventas (C-04): registro de venta con renglones."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.errors import traducir_integrity_error
from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import (
    ClienteResumenRead,
    RenglonRead,
    VentaCreate,
    VentaRead,
)


def _a_venta_read(venta: Venta) -> VentaRead:
    """Convierte una venta (con relaciones precargadas) a su DTO de salida."""
    cliente = venta.cliente
    return VentaRead(
        id=venta.id,
        fecha=venta.fecha,
        total=venta.total,
        cliente=ClienteResumenRead(
            id=cliente.id, nombre=cliente.nombre, email=cliente.email
        ),
        renglones=[
            RenglonRead(
                libro_id=r.libro_id,
                titulo=r.libro.titulo,
                cantidad=r.cantidad,
                precio_unitario=r.precio_unitario,
                subtotal=r.precio_unitario * r.cantidad,
            )
            for r in venta.renglones
        ],
    )


async def _releer(session: AsyncSession, venta_id: int) -> VentaRead:
    """Relee una venta con cliente, renglones y libros precargados (RN-G-03)."""
    resultado = await session.execute(
        select(Venta)
        .where(Venta.id == venta_id)
        .options(
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )
    )
    return _a_venta_read(resultado.scalar_one())


async def crear(session: AsyncSession, datos: VentaCreate) -> VentaRead:
    """Registra una venta copiando el precio y calculando el total (C-04).

    Los libros se cargan en una sola consulta (``WHERE id IN (...)``); si falta
    alguno se responde 409. El cliente inexistente lo rechaza la FK y se traduce
    a 409. El ``precio_unitario`` es una copia (RN-06) y el ``total`` la suma de
    ``cantidad × precio_unitario`` en ``Decimal`` (RN-07).
    """
    ids = [r.libro_id for r in datos.renglones]
    resultado = await session.execute(select(Libro).where(Libro.id.in_(ids)))
    libros = {l.id: l for l in resultado.scalars().all()}
    faltante = next((i for i in ids if i not in libros), None)
    if faltante is not None:
        raise HTTPException(status_code=409, detail="El libro indicado no existe")

    venta = Venta(cliente_id=datos.cliente_id, total=Decimal("0.00"))
    for r in datos.renglones:
        libro = libros[r.libro_id]
        venta.renglones.append(
            RenglonVenta(
                libro_id=r.libro_id,
                cantidad=r.cantidad,
                precio_unitario=libro.precio,
            )
        )
    venta.total = sum(
        (rg.cantidad * rg.precio_unitario for rg in venta.renglones), Decimal("0.00")
    )
    venta.fecha = datetime.now(timezone.utc)

    session.add(venta)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None

    return await _releer(session, venta.id)
