"""Contratos de salida de los healthchecks (IN-03).

Los cuerpos son fijos: el de ``/health/live`` y los dos posibles de
``/health/ready``. Modelarlos acá mantiene la misma estructura que el resto de
los módulos (``router.py`` + ``service.py`` + ``schemas.py`` + ``models.py``) y
evita que el router arme diccionarios a mano.
"""

from typing import Literal

from pydantic import BaseModel


class EstadoVivo(BaseModel):
    """Cuerpo de ``GET /health/live``: el proceso está en marcha."""

    estado: Literal["vivo"] = "vivo"


class EstadoListo(BaseModel):
    """Cuerpo de ``GET /health/ready`` cuando la base responde."""

    estado: Literal["listo"] = "listo"
    base: Literal["ok"] = "ok"


class EstadoNoListo(BaseModel):
    """Cuerpo de ``GET /health/ready`` cuando la base no responde."""

    estado: Literal["no_listo"] = "no_listo"
    base: Literal["error"] = "error"
