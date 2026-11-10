"""Fixtures compartidas: cliente ASGI y sesiones de base controladas."""

import asyncio
import os

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

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


@pytest.fixture(scope="session")
def url_bd_test() -> str:
    """URL de una base de test derivada de ``DATABASE_URL``; la crea si falta.

    Nunca toca la base real: usa ``<nombre_de_la_base>_test`` y crea el esquema
    desde cero en cada prueba. Si ``DATABASE_URL`` no está definida, se salta.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("requiere DATABASE_URL para los tests de contrato de API")

    original = make_url(url)
    nombre_test = f"{original.database}_test"
    admin = original.set(database="postgres")
    admin_dsn = admin.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    url_test = original.set(database=nombre_test).render_as_string(hide_password=False)

    async def _crear() -> None:
        import asyncpg

        conexion = await asyncpg.connect(admin_dsn, timeout=5)
        try:
            existe = await conexion.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", nombre_test
            )
            if not existe:
                await conexion.execute(f'CREATE DATABASE "{nombre_test}"')
        finally:
            await conexion.close()

    try:
        asyncio.run(_crear())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"no se pudo preparar la base de test: {type(exc).__name__}")

    return url_test


@pytest_asyncio.fixture
async def fabrica_sesion_bd(url_bd_test):
    """Motor y fábrica sobre la base de test con el esquema limpio por prueba."""
    motor = create_async_engine(url_bd_test)
    async with motor.begin() as conexion:
        await conexion.run_sync(SQLModel.metadata.drop_all)
        await conexion.run_sync(SQLModel.metadata.create_all)

    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    yield fabrica
    await motor.dispose()


@pytest_asyncio.fixture
async def cliente_bd(aplicacion, fabrica_sesion_bd):
    """Cliente ASGI con la sesión real de la base de test inyectada."""
    async def _dependencia():
        async with fabrica_sesion_bd() as sesion:
            yield sesion

    aplicacion.dependency_overrides[get_session] = _dependencia
    transporte = httpx.ASGITransport(app=aplicacion)
    async with httpx.AsyncClient(transport=transporte, base_url="http://test") as http:
        yield http
    aplicacion.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sesion_bd(fabrica_sesion_bd):
    """Sesión directa sobre la base de test para sembrar datos en cada prueba."""
    async with fabrica_sesion_bd() as sesion:
        yield sesion
