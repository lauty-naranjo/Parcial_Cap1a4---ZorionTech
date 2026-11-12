"""Lógica de negocio del módulo clientes (C-03).

Las lecturas relacionales precargan perfil, cliente, renglones y libro: ninguna
accede a una relación sin ``joinedload``/``selectinload`` (RN-G-03, C-06).
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from fastapi import HTTPException

from app.core.errors import traducir_integrity_error
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteResumenRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
    RenglonRead,
    VentaRead,
)
from app.modules.ventas.models import RenglonVenta, Venta

MENSAJE_NO_ENCONTRADO = "No encontrado"


def _perfil_a_read(perfil: PerfilCliente | None) -> PerfilRead | None:
    if perfil is None:
        return None
    return PerfilRead(
        id=perfil.id,
        cliente_id=perfil.cliente_id,
        telefono=perfil.telefono,
        direccion=perfil.direccion,
    )


def _cliente_a_read(cliente: Cliente) -> ClienteRead:
    return ClienteRead(
        id=cliente.id,
        nombre=cliente.nombre,
        email=cliente.email,
        perfil=_perfil_a_read(cliente.perfil),
    )


async def crear(session: AsyncSession, datos: ClienteCreate) -> ClienteRead:
    """Da de alta un cliente; email repetido → 409."""
    cliente = Cliente(nombre=datos.nombre, email=datos.email)
    session.add(cliente)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    await session.refresh(cliente)
    return ClienteRead(id=cliente.id, nombre=cliente.nombre, email=cliente.email)


async def _obtener_con_perfil(session: AsyncSession, cliente_id: int) -> Cliente | None:
    resultado = await session.execute(
        select(Cliente)
        .where(Cliente.id == cliente_id)
        .options(joinedload(Cliente.perfil))
    )
    return resultado.scalar_one_or_none()


async def obtener(session: AsyncSession, cliente_id: int) -> ClienteRead:
    """Devuelve el cliente con su perfil (objeto o ``null``) o 404."""
    cliente = await _obtener_con_perfil(session, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
    return _cliente_a_read(cliente)


async def actualizar(
    session: AsyncSession, cliente_id: int, datos: ClienteUpdate
) -> ClienteRead:
    """Aplica solo los campos enviados (PATCH); email repetido → 409."""
    cliente = await _obtener_con_perfil(session, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    cliente.sqlmodel_update(datos.model_dump(exclude_unset=True))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    return _cliente_a_read(cliente)


async def crear_perfil(
    session: AsyncSession, cliente_id: int, datos: PerfilCreate
) -> PerfilRead:
    """Da de alta el perfil; segundo perfil o cliente inexistente → 409/404."""
    cliente = await session.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    perfil = PerfilCliente(
        cliente_id=cliente_id, telefono=datos.telefono, direccion=datos.direccion
    )
    session.add(perfil)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    await session.refresh(perfil)
    return _perfil_a_read(perfil)


def _venta_a_read(venta: Venta) -> VentaRead:
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


async def listar_ventas(
    session: AsyncSession, cliente_id: int, offset: int, limit: int
) -> list[VentaRead]:
    """Ventas del cliente con renglones, libro y cliente precargados (RN-G-03)."""
    cliente = await session.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    resultado = await session.execute(
        select(Venta)
        .where(Venta.cliente_id == cliente_id)
        .options(
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )
        .order_by(Venta.id)
        .offset(offset)
        .limit(limit)
    )
    return [_venta_a_read(v) for v in resultado.scalars().all()]
