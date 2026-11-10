"""Router del módulo generos (C-03): alta, listado y libros del género."""

from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.pagination import Limit, Offset
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead
from app.modules.libros.schemas import LibroRead

router = APIRouter(prefix="/generos", tags=["Géneros"])


@router.post("/", response_model=GeneroRead, status_code=status.HTTP_201_CREATED)
async def crear(datos: GeneroCreate, session: SessionDep) -> GeneroRead:
    return await service.crear(session, datos)


@router.get("/", response_model=list[GeneroRead])
async def listar(session: SessionDep, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, offset, limit)


@router.get("/{genero_id}/libros", response_model=list[LibroRead])
async def libros(
    genero_id: int, session: SessionDep, limit: Limit = 20, offset: Offset = 0
):
    return await service.listar_libros(session, genero_id, offset, limit)
