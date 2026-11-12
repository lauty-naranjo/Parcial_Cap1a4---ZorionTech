"""Router del módulo ventas (C-04/C-06): registro y lectura de venta."""

from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.core.pagination import Limit, Offset
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaRead

router = APIRouter(prefix="/ventas", tags=["Ventas"])


@router.post("/", response_model=VentaRead, status_code=status.HTTP_201_CREATED)
async def crear(datos: VentaCreate, session: SessionDep) -> VentaRead:
    return await service.crear(session, datos)


@router.get("/", response_model=list[VentaRead])
async def listar(session: SessionDep, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, offset, limit)


@router.get("/{venta_id}", response_model=VentaRead)
async def obtener(venta_id: int, session: SessionDep) -> VentaRead:
    return await service.obtener(session, venta_id)
