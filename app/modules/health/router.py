"""Healthchecks de liveness y readiness (IN-03, D-06)."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlmodel import select

from app.core.database import SessionDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Salud"])


@router.get("/live")
async def live() -> dict[str, str]:
    """Confirma que el proceso está vivo sin tocar la base de datos."""
    return {"estado": "vivo"}


@router.get("/ready", response_model=None)
async def ready(session: SessionDep) -> JSONResponse:
    """Confirma que la base responde ``SELECT 1``; cualquier fallo es 503."""
    try:
        resultado = await session.execute(select(1))
        resultado.scalar_one()
    except Exception:
        logger.exception("Falló la verificación de la base en /health/ready")
        return JSONResponse(status_code=503, content={"estado": "no_listo", "base": "error"})
    return JSONResponse(status_code=200, content={"estado": "listo", "base": "ok"})
