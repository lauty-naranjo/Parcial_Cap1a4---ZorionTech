"""Healthchecks de liveness y readiness (IN-03, D-06)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.database import SessionDep
from app.modules.health.schemas import EstadoListo, EstadoNoListo, EstadoVivo
from app.modules.health.service import base_responde

router = APIRouter(prefix="/health", tags=["Salud"])


@router.get("/live", response_model=EstadoVivo)
async def live() -> EstadoVivo:
    """Confirma que el proceso está vivo sin tocar la base de datos."""
    return EstadoVivo()


@router.get("/ready", response_model=None)
async def ready(session: SessionDep) -> JSONResponse:
    """Confirma que la base responde ``SELECT 1``; cualquier fallo es 503."""
    if not await base_responde(session):
        return JSONResponse(status_code=503, content=EstadoNoListo().model_dump())
    return JSONResponse(status_code=200, content=EstadoListo().model_dump())
