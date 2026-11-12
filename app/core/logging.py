"""Configuración de logging de la aplicación (C-07): salida estándar e idempotencia.

El aviso de comprobante debe verse con ``docker logs libreria`` (D-07), así que
los mensajes de los módulos se escriben en stdout con un ``StreamHandler`` que
hace ``flush()`` tras cada emisión. La configuración se aplica una sola vez por
proceso aunque se creen varias instancias de la aplicación.
"""

import logging
import sys

MARCA_HANDLER = "_libreria_stdout"
FORMATO = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configurar_logging() -> None:
    """Asocia a la raíz un handler de stdout, sin duplicarlo en llamadas siguientes."""
    raiz = logging.getLogger()
    if any(getattr(handler, MARCA_HANDLER, False) for handler in raiz.handlers):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FORMATO))
    setattr(handler, MARCA_HANDLER, True)
    raiz.addHandler(handler)
    raiz.setLevel(logging.INFO)
