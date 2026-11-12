"""Contador de consultas SQL para verificar la ausencia de N+1 (C-06, IN-04).

Registra el evento ``before_cursor_execute`` del motor síncrono subyacente de
SQLAlchemy (el mismo que usa el motor asincrónico) y cuenta cada ejecución de
sentencia durante un bloque. Se usa como context manager:

.. code-block:: python

    with contador_consultas(motor) as cuenta:
        await cliente.get(f"/libros/{id}")
    assert cuenta.total == 2
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine


class ContadorConsultas:
    """Acumula las sentencias SQL ejecutadas mientras está activo."""

    def __init__(self) -> None:
        self.consultas: list[str] = []

    @property
    def total(self) -> int:
        """Cantidad de sentencias ejecutadas desde que se activó el contador."""
        return len(self.consultas)


@contextmanager
def contador_consultas(motor: AsyncEngine) -> Iterator[ContadorConsultas]:
    """Cuenta las ejecuciones de cursor del motor durante el bloque.

    Escucha ``before_cursor_execute`` sobre ``motor.sync_engine``: SQLAlchemy
    emite el evento en el ``Engine`` síncrono subyacente, el mismo que usa el
    motor asincrónico, así que el conteo cubre las consultas de la aplicación.
    El listener se remueve al salir para no contaminar otras pruebas.
    """
    contador = ContadorConsultas()

    def _contar(conn, cursor, statement, parameters, context, executemany):
        contador.consultas.append(str(statement))

    event.listen(motor.sync_engine, "before_cursor_execute", _contar)
    try:
        yield contador
    finally:
        event.remove(motor.sync_engine, "before_cursor_execute", _contar)
