"""Lógica de negocio del módulo autores (C-03).

Las lecturas relacionales precargan libro y editorial: ninguna accede a una
relación sin ``joinedload`` (RN-G-03, C-06).
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException

from app.core.errors import traducir_integrity_error
from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorLibroRead, AutorUpdate
from app.modules.editoriales.schemas import EditorialRead
from app.modules.libros.models import Libro, LibroAutor

MENSAJE_NO_ENCONTRADO = "No encontrado"


async def crear(session: AsyncSession, datos: AutorCreate) -> Autor:
    """Da de alta un autor (sin unicidad de nombre, según la consigna)."""
    autor = Autor(nombre=datos.nombre, nacionalidad=datos.nacionalidad)
    session.add(autor)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    await session.refresh(autor)
    return autor


async def obtener(session: AsyncSession, autor_id: int) -> Autor:
    """Devuelve un autor o 404 si no existe."""
    autor = await session.get(Autor, autor_id)
    if autor is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
    return autor


async def actualizar(session: AsyncSession, autor_id: int, datos: AutorUpdate) -> Autor:
    """Aplica solo los campos enviados (PATCH)."""
    autor = await session.get(Autor, autor_id)
    if autor is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    autor.sqlmodel_update(datos.model_dump(exclude_unset=True))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None
    await session.refresh(autor)
    return autor


def _a_autor_libro_read(autoria: LibroAutor) -> AutorLibroRead:
    libro = autoria.libro
    editorial = libro.editorial
    return AutorLibroRead(
        libro_id=libro.id,
        titulo=libro.titulo,
        rol=autoria.rol,
        orden=autoria.orden,
        editorial=EditorialRead(
            id=editorial.id, nombre=editorial.nombre, pais=editorial.pais
        ),
    )


async def listar_libros(
    session: AsyncSession, autor_id: int, offset: int, limit: int
) -> list[AutorLibroRead]:
    """Libros de un autor con ``rol``/``orden`` y editorial precargados."""
    autor = await session.get(Autor, autor_id)
    if autor is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    resultado = await session.execute(
        select(LibroAutor)
        .where(LibroAutor.autor_id == autor_id)
        .options(joinedload(LibroAutor.libro).joinedload(Libro.editorial))
        .order_by(LibroAutor.orden)
        .offset(offset)
        .limit(limit)
    )
    return [_a_autor_libro_read(a) for a in resultado.scalars().all()]
