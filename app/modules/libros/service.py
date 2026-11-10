"""Lógica de negocio del módulo libros (C-03, lectura y edición escalar)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from fastapi import HTTPException

from app.core.errors import traducir_integrity_error
from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import LibroAutorRead, LibroDetalleRead, LibroUpdate

MENSAJE_NO_ENCONTRADO = "No encontrado"


def _a_detalle(libro: Libro) -> LibroDetalleRead:
    """Convierte un libro (con relaciones precargadas) a su DTO de detalle."""
    return LibroDetalleRead(
        id=libro.id,
        isbn=libro.isbn,
        titulo=libro.titulo,
        precio=libro.precio,
        stock=libro.stock,
        editorial=EditorialRead(
            id=libro.editorial.id,
            nombre=libro.editorial.nombre,
            pais=libro.editorial.pais,
        ),
        genero=(
            GeneroRead(id=libro.genero.id, nombre=libro.genero.nombre)
            if libro.genero is not None
            else None
        ),
        autores=[
            LibroAutorRead(
                autor_id=autoria.autor_id,
                nombre=autoria.autor.nombre,
                rol=autoria.rol,
                orden=autoria.orden,
            )
            for autoria in libro.autorias
        ],
    )


async def listar(
    session: AsyncSession,
    offset: int,
    limit: int,
    titulo: str | None = None,
    genero_id: int | None = None,
) -> list[Libro]:
    """Lista libros con filtros y editorial/género precargados (RN-11, RN-G-03)."""
    sentencia = select(Libro)
    if titulo:
        sentencia = sentencia.where(Libro.titulo.ilike(f"%{titulo}%"))
    if genero_id is not None:
        sentencia = sentencia.where(Libro.genero_id == genero_id)

    sentencia = sentencia.options(joinedload(Libro.editorial), joinedload(Libro.genero))
    sentencia = sentencia.order_by(Libro.id).offset(offset).limit(limit)

    resultado = await session.execute(sentencia)
    return list(resultado.scalars().all())


async def _obtener_orm(session: AsyncSession, libro_id: int) -> Libro | None:
    resultado = await session.execute(
        select(Libro)
        .where(Libro.id == libro_id)
        .options(
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
            selectinload(Libro.autorias).joinedload(LibroAutor.autor),
        )
    )
    return resultado.scalar_one_or_none()


async def obtener(session: AsyncSession, libro_id: int) -> LibroDetalleRead:
    """Detalle de un libro con editorial, género y autores; 404 si no existe."""
    libro = await _obtener_orm(session, libro_id)
    if libro is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)
    return _a_detalle(libro)


async def actualizar(
    session: AsyncSession, libro_id: int, datos: LibroUpdate
) -> LibroDetalleRead:
    """Aplica solo los campos escalares enviados (IN-01); las autorías no cambian."""
    libro = await session.get(Libro, libro_id)
    if libro is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    libro.sqlmodel_update(datos.model_dump(exclude_unset=True))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise traducir_integrity_error(exc) from None

    return await obtener(session, libro_id)
