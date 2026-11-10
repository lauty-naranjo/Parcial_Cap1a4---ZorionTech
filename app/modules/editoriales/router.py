"""Router del módulo editoriales (C-03): alta, listado, detalle y libros."""

from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.pagination import Limit, Offset
from app.modules.editoriales import service
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialRead,
    EditorialUpdate,
)
from app.modules.libros.schemas import LibroRead

router = APIRouter(prefix="/editoriales", tags=["Editoriales"])


@router.post("/", response_model=EditorialRead, status_code=status.HTTP_201_CREATED)
async def crear(datos: EditorialCreate, session: SessionDep) -> EditorialRead:
    return await service.crear(session, datos)


@router.get("/", response_model=list[EditorialRead])
async def listar(session: SessionDep, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, offset, limit)


@router.get("/{editorial_id}", response_model=EditorialRead)
async def obtener(editorial_id: int, session: SessionDep) -> EditorialRead:
    return await service.obtener(session, editorial_id)


@router.patch("/{editorial_id}", response_model=EditorialRead)
async def actualizar(
    editorial_id: int, datos: EditorialUpdate, session: SessionDep
) -> EditorialRead:
    return await service.actualizar(session, editorial_id, datos)


@router.get("/{editorial_id}/libros", response_model=list[LibroRead])
async def libros(
    editorial_id: int, session: SessionDep, limit: Limit = 20, offset: Offset = 0
):
    return await service.listar_libros(session, editorial_id, offset, limit)
