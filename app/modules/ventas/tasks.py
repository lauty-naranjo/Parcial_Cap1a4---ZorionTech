"""Tarea de fondo del módulo ventas (C-07): aviso de comprobante.

La tarea corre después de enviada la respuesta, cuando la sesión de la petición
ya se cerró. Por eso recibe solo escalares y no ejecuta consultas (RN-G-02,
US-032). Un fallo aquí no se propaga al servidor.
"""

import asyncio
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

ESPERA_AVISO_SEGUNDOS = 0.5


async def avisar_comprobante(venta_id: int, email: str, total: Decimal) -> None:
    """Simula el envío del comprobante y lo deja en el log estándar (D-07).

    Espera de forma no bloqueante (``asyncio.sleep``) para que el event loop
    siga atendiendo otras peticiones, y registra solo el id de venta, el email
    y el total; nunca credenciales ni la URL de la base.
    """
    try:
        await asyncio.sleep(ESPERA_AVISO_SEGUNDOS)
        logger.info(
            "Aviso de comprobante enviado: venta=%s email=%s total=%s",
            venta_id,
            email,
            f"{total:.2f}",
        )
    except Exception:  # noqa: BLE001 - el aviso no debe tumbar al servidor
        logger.exception("No se pudo avisar el comprobante de la venta %s", venta_id)
