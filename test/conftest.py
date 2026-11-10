"""Fixtures compartidas: cliente ASGI y sesiones de base controladas."""

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.exc import OperationalError

from app.core.database import get_session
from app.main import create_app

MENSAJE_INTERNO = "fallo interno: password authentication failed for user postgres"


class _ResultadoFalso:
    def __init__(self, valor: int) -> None:
        self._valor = valor

    def scalar_one(self) -> int:
        return self._valor


class SesionQueResponde:
    """Sesión falsa cuyo ``SELECT 1`` devuelve 1."""

    def __init__(self) -> None:
        self.consultas: list[object] = []

    async def execute(self, sentencia: object) -> _ResultadoFalso:
        self.consultas.append(sentencia)
        return _ResultadoFalso(1)


class SesionQueFalla:
    """Sesión falsa que falla al consultar la base."""

    async def execute(self, sentencia: object) -> _ResultadoFalso:
        raise OperationalError(sentencia, {}, Exception(MENSAJE_INTERNO))


@pytest.fixture
def aplicacion():
    """Aplicación nueva por prueba; el transporte ASGI no corre el lifespan."""
    return create_app()


@pytest_asyncio.fixture
async def cliente(aplicacion):
    transporte = httpx.ASGITransport(app=aplicacion)
    async with httpx.AsyncClient(transport=transporte, base_url="http://test") as http:
        yield http


@pytest.fixture
def sesion_disponible() -> SesionQueResponde:
    return SesionQueResponde()


@pytest.fixture
def sesion_que_falla() -> SesionQueFalla:
    return SesionQueFalla()


@pytest.fixture
def usar_sesion(aplicacion):
    """Sustituye la dependencia de sesión por la sesión recibida."""

    def _usar(sesion: object) -> None:
        async def _dependencia():
            yield sesion

        aplicacion.dependency_overrides[get_session] = _dependencia

    yield _usar
    aplicacion.dependency_overrides.clear()
