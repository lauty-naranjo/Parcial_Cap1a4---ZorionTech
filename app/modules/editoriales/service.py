"""Lógica de negocio del módulo editoriales (C-03).

Las lecturas relacionales precargan editorial y género: ninguna accede a una
relación sin ``joinedload`` (RN-G-03, C-06).
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException

from app.core.errors import traducir_integrity_error
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.libros.models import Libro

MENSAJE_NO_ENCONTRADO = "No encontrado"


async def crear(session: AsyncSession, datos: EditorialCreate) -> Editorial:
    """Da de alta una editorial; un nombre repetido se traduce a 409."""
    editorial = Editorial(nombre=datos.nombre, pais=datos.pais)
    session.add(editorial)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    await session.refresh(editorial)
    return editorial


async def listar(session: AsyncSession, offset: int, limit: int) -> list[Editorial]:
    """Lista editoriales paginadas en orden de ``id``."""
    resultado = await session.execute(
        select(Editorial).order_by(Editorial.id).offset(offset).limit(limit)
    )
    return list(resultado.scalars().all())


async def obtener(session: AsyncSession, editorial_id: int) -> Editorial:
    """Devuelve una editorial o 404 si no existe."""
    editorial = await session.get(Editorial, editorial_id)
    if editorial is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
    return editorial


async def actualizar(
    session: AsyncSession, editorial_id: int, datos: EditorialUpdate
) -> Editorial:
    """Aplica solo los campos enviados (PATCH); nombre repetido → 409."""
    editorial = await session.get(Editorial, editorial_id)
    if editorial is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    editorial.sqlmodel_update(datos.model_dump(exclude_unset=True))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    await session.refresh(editorial)
    return editorial


async def listar_libros(
    session: AsyncSession, editorial_id: int, offset: int, limit: int
) -> list[Libro]:
    """Libros de una editorial con editorial/género precargados (RN-G-03)."""
    editorial = await session.get(Editorial, editorial_id)
    if editorial is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    resultado = await session.execute(
        select(Libro)
        .where(Libro.editorial_id == editorial_id)
        .options(joinedload(Libro.editorial), joinedload(Libro.genero))
        .order_by(Libro.id)
        .offset(offset)
        .limit(limit)
    )
    return list(resultado.scalars().all())
