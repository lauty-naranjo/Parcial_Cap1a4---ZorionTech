"""DTO de entrada y salida del módulo clientes (C-03)."""

from pydantic import Field
from sqlmodel import SQLModel

# Los DTO de salida de la venta viven en ``ventas/schemas.py`` (C-04); se
# reexportan acá para no romper C-03 (``GET /clientes/{id}/ventas``).
from app.modules.ventas.schemas import ClienteResumenRead, RenglonRead, VentaRead  # noqa: F401

# Patrón simple de email (sin dependencia de ``pydantic[email]``); la unicidad
# la garantiza el UNIQUE de la base (RN-02).
PATRON_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class ClienteCreate(SQLModel):
    """Cuerpo de alta de un cliente."""

    nombre: str
    email: str = Field(pattern=PATRON_EMAIL)


class ClienteUpdate(SQLModel):
    """Cuerpo de PATCH: campos opcionales."""

    nombre: str | None = None
    email: str | None = Field(default=None, pattern=PATRON_EMAIL)


class PerfilCreate(SQLModel):
    """Cuerpo de alta del perfil; ``cliente_id`` viaja en la ruta."""

    telefono: str
    direccion: str


class PerfilRead(SQLModel):
    """Contrato de lectura del perfil."""

    id: int
    cliente_id: int
    telefono: str
    direccion: str


class ClienteRead(SQLModel):
    """Contrato de lectura: ``perfil`` como objeto único o ``null``."""

    id: int
    nombre: str
    email: str
    perfil: PerfilRead | None = None
