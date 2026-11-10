"""Lógica de negocio del módulo generos (C-03)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException

from app.core.errors import traducir_integrity_error
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate
from app.modules.libros.models import Libro

MENSAJE_NO_ENCONTRADO = "No encontrado"


async def crear(session: AsyncSession, datos: GeneroCreate) -> Genero:
    """Da de alta un género; nombre repetido → 409."""
    genero = Genero(nombre=datos.nombre)
    session.add(genero)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    await session.refresh(genero)
    return genero


async def listar(session: AsyncSession, offset: int, limit: int) -> list[Genero]:
    """Lista géneros paginados en orden de ``id``."""
    resultado = await session.execute(
        select(Genero).order_by(Genero.id).offset(offset).limit(limit)
    )
    return list(resultado.scalars().all())


async def listar_libros(
    session: AsyncSession, genero_id: int, offset: int, limit: int
) -> list[Libro]:
    """Libros de un género con editorial/género precargados (RN-G-03)."""
    genero = await session.get(Genero, genero_id)
    if genero is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    resultado = await session.execute(
        select(Libro)
        .where(Libro.genero_id == genero_id)
        .options(joinedload(Libro.editorial), joinedload(Libro.genero))
        .order_by(Libro.id)
        .offset(offset)
        .limit(limit)
    )
    return list(resultado.scalars().all())
