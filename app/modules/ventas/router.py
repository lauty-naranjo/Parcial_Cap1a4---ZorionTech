"""Router del módulo ventas (C-04/C-06/C-07): registro y lectura de venta."""

from fastapi import APIRouter, BackgroundTasks, status

from app.core.database import SessionDep
from app.core.pagination import Limit, Offset
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaRead
from app.modules.ventas.tasks import avisar_comprobante

router = APIRouter(prefix="/ventas", tags=["Ventas"])


@router.post("/", response_model=VentaRead, status_code=status.HTTP_201_CREATED)
async def crear(
    datos: VentaCreate,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> VentaRead:
    """Registra la venta y agenda el aviso de comprobante **después** del ``commit``.

    ``service.crear`` hace el ``commit`` y devuelve el ``VentaRead`` con el
    cliente precargado; recién entonces se agenda ``avisar_comprobante`` con
    escalares (id, email, total), sin pasarle la sesión de la petición, que ya
    se cierra al responder. Si el servicio lanza (409/422) no se agenda nada.
    """
    venta = await service.crear(session, datos)
    background_tasks.add_task(
        avisar_comprobante, venta.id, venta.cliente.email, venta.total
    )
    return venta


@router.get("/", response_model=list[VentaRead])
async def listar(session: SessionDep, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, offset, limit)


@router.get("/{venta_id}", response_model=VentaRead)
async def obtener(venta_id: int, session: SessionDep) -> VentaRead:
    return await service.obtener(session, venta_id)
