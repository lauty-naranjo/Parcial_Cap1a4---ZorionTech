"""Alias de paginación reutilizables para toda colección (RN-10).

``limit`` va de 1 a 100 (default 20) y ``offset`` desde 0 (default 0). Todo
listado los declara y FastAPI devuelve 422 automáticamente si están fuera de
rango, sin ejecutar el handler.

Nota de compatibilidad: FastAPI >= 0.100 exige que el default se indique con
``=`` en la firma del handler y no dentro de ``Query(...)`` dentro de
``Annotated``. Por eso los alias declaran solo las restricciones (``ge``/``le``)
y cada handler asigna el default: ``limit: Limit = 20``, ``offset: Offset = 0``.
"""

from typing import Annotated

from fastapi import Query

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
