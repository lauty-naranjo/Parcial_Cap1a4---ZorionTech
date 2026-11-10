"""Router del módulo libros (C-03): listado, detalle y edición escalar."""

from fastapi import APIRouter, Query, status

from app.core.database import SessionDep
from app.core.pagination import Limit, Offset
from app.modules.libros import service
from app.modules.libros.schemas import (
    LibroCreate,
    LibroDetalleRead,
    LibroRead,
    LibroUpdate,
)

router = APIRouter(prefix="/libros", tags=["Libros"])


@router.post("/", response_model=LibroDetalleRead, status_code=status.HTTP_201_CREATED)
async def crear(datos: LibroCreate, session: SessionDep) -> LibroDetalleRead:
    return await service.crear(session, datos)


@router.get("/", response_model=list[LibroRead])
async def listar(
    session: SessionDep,
    limit: Limit = 20,
    offset: Offset = 0,
    titulo: str | None = Query(default=None),
    genero_id: int | None = Query(default=None),
):
    return await service.listar(
        session, offset, limit, titulo=titulo, genero_id=genero_id
    )


@router.get("/{libro_id}", response_model=LibroDetalleRead)
async def obtener(libro_id: int, session: SessionDep) -> LibroDetalleRead:
    return await service.obtener(session, libro_id)


@router.patch("/{libro_id}", response_model=LibroDetalleRead)
async def actualizar(
    libro_id: int, datos: LibroUpdate, session: SessionDep
) -> LibroDetalleRead:
    return await service.actualizar(session, libro_id, datos)
