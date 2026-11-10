"""DTO de entrada y salida del módulo ventas (C-04).

Es dueño del contrato de la venta; los DTO de salida se reexportan desde
``clientes/schemas.py`` para no romper C-03 (``GET /clientes/{id}/ventas``).
"""

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import Field, field_serializer, model_validator
from sqlmodel import SQLModel


class RenglonCreate(SQLModel):
    """Renglón de entrada: ``cantidad`` mayor a 0; sin ``precio_unitario`` (RN-05)."""

    libro_id: int
    cantidad: int = Field(gt=0)


class VentaCreate(SQLModel):
    """Cuerpo de registro de venta: al menos un renglón y sin libros repetidos."""

    cliente_id: int
    renglones: list[RenglonCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _libros_sin_repetir(self) -> "VentaCreate":
        ids = [r.libro_id for r in self.renglones]
        if len(ids) != len(set(ids)):
            raise ValueError("El libro no puede repetirse en la venta")
        return self


class ClienteResumenRead(SQLModel):
    """Cliente resumido embebido en una venta (sin perfil)."""

    id: int
    nombre: str
    email: str


class RenglonRead(SQLModel):
    """Renglón de venta: ``titulo`` desde el libro y ``subtotal`` calculado."""

    libro_id: int
    titulo: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaRead(SQLModel):
    """Contrato de lectura de una venta (se completa en C-06)."""

    id: int
    fecha: datetime
    total: Decimal
    cliente: ClienteResumenRead
    renglones: list[RenglonRead]

    @field_serializer("fecha")
    def _fecha_z(self, valor: datetime) -> str:
        """Serializa la fecha en UTC ISO 8601 con microsegundos y sufijo ``Z``."""
        return (
            valor.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
