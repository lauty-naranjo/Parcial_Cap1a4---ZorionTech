"""Router del módulo ventas (C-04): registro de venta."""

from fastapi import APIRouter, status

from app.core.database import SessionDep
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaRead

router = APIRouter(prefix="/ventas", tags=["Ventas"])


@router.post("/", response_model=VentaRead, status_code=status.HTTP_201_CREATED)
async def crear(datos: VentaCreate, session: SessionDep) -> VentaRead:
    return await service.crear(session, datos)
