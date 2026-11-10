"""Router del módulo clientes (C-03): alta, detalle, edición, perfil y ventas."""

from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.pagination import Limit, Offset
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
    VentaRead,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def crear(datos: ClienteCreate, session: SessionDep) -> ClienteRead:
    return await service.crear(session, datos)


@router.get("/{cliente_id}", response_model=ClienteRead)
async def obtener(cliente_id: int, session: SessionDep) -> ClienteRead:
    return await service.obtener(session, cliente_id)


@router.patch("/{cliente_id}", response_model=ClienteRead)
async def actualizar(
    cliente_id: int, datos: ClienteUpdate, session: SessionDep
) -> ClienteRead:
    return await service.actualizar(session, cliente_id, datos)


@router.post(
    "/{cliente_id}/perfil", response_model=PerfilRead, status_code=status.HTTP_201_CREATED
)
async def crear_perfil(
    cliente_id: int, datos: PerfilCreate, session: SessionDep
) -> PerfilRead:
    return await service.crear_perfil(session, cliente_id, datos)


@router.get("/{cliente_id}/ventas", response_model=list[VentaRead])
async def ventas(
    cliente_id: int, session: SessionDep, limit: Limit = 20, offset: Offset = 0
):
    return await service.listar_ventas(session, cliente_id, offset, limit)
