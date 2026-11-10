"""Capa de datos asincrónica: motor, fábrica de sesiones y sesión por petición.

El motor y la fábrica se crean exclusivamente en el ``lifespan`` y se publican
en ``app.state``; este módulo solo contiene las funciones que los construyen y
la dependencia que entrega una sesión por petición (D-01).
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    """Crea el motor asincrónico; no abre conexiones hasta la primera consulta."""
    return create_async_engine(settings.database_url, echo=settings.sql_echo)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Crea la fábrica de sesiones que no expira los objetos al confirmar."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Entrega una sesión de la fábrica de ``app.state`` y la cierra al salir."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

