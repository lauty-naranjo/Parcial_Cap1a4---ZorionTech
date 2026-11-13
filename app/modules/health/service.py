"""Servicio del módulo health: la verificación de la base.

El router no conoce el SQL del chequeo: lo delega acá, igual que el resto de los
módulos delega su lógica en ``service.py``.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

logger = logging.getLogger(__name__)


async def base_responde(sesion: AsyncSession) -> bool:
    """Ejecuta ``SELECT 1`` y devuelve si la base respondió.

    Nunca propaga la causa: el detalle se registra en el log del servidor y al
    cliente solo le llega ``{"estado": "no_listo", "base": "error"}`` (RN-12).
    """

    try:
        resultado = await sesion.execute(select(1))
        resultado.scalar_one()
    except Exception:
        logger.exception("Falló la verificación de la base en /health/ready")
        return False
    return True
