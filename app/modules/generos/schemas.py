"""DTO de entrada y salida del módulo generos (C-03)."""

from sqlmodel import SQLModel


class GeneroCreate(SQLModel):
    """Cuerpo de alta de un género: solo ``nombre``."""

    nombre: str


class GeneroRead(SQLModel):
    """Contrato de lectura: ``id`` y ``nombre``."""

    id: int
    nombre: str
