"""Router del módulo autores (C-03): alta, detalle, edición y libros."""

from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.pagination import Limit, Offset
from app.modules.autores import service
from app.modules.autores.schemas import (
    AutorCreate,
    AutorLibroRead,
    AutorRead,
    AutorUpdate,
)

router = APIRouter(prefix="/autores", tags=["Autores"])


@router.post("/", response_model=AutorRead, status_code=status.HTTP_201_CREATED)
async def crear(datos: AutorCreate, session: SessionDep) -> AutorRead:
    return await service.crear(session, datos)


@router.get("/{autor_id}", response_model=AutorRead)
async def obtener(autor_id: int, session: SessionDep) -> AutorRead:
    return await service.obtener(session, autor_id)


@router.patch("/{autor_id}", response_model=AutorRead)
async def actualizar(autor_id: int, datos: AutorUpdate, session: SessionDep) -> AutorRead:
    return await service.actualizar(session, autor_id, datos)


@router.get("/{autor_id}/libros", response_model=list[AutorLibroRead])
async def libros(
    autor_id: int, session: SessionDep, limit: Limit = 20, offset: Offset = 0
):
    return await service.listar_libros(session, autor_id, offset, limit)
