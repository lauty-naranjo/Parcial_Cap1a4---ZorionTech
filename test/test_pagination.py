"""Pruebas de los alias de paginación reutilizables (RN-10)."""

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from app.core.pagination import Limit, Offset


def _app_de_prueba() -> FastAPI:
    app = FastAPI()

    @app.get("/items")
    async def items(limit: Limit = 20, offset: Offset = 0):
        return {"limit": limit, "offset": offset}

    return app


@pytest_asyncio.fixture
async def cliente_pag():
    app = _app_de_prueba()
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://test") as http:
        yield http


async def test_defaults_son_20_y_0(cliente_pag):
    respuesta = await cliente_pag.get("/items")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"limit": 20, "offset": 0}


async def test_respeta_limit_y_offset_enviados(cliente_pag):
    respuesta = await cliente_pag.get("/items", params={"limit": 5, "offset": 10})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"limit": 5, "offset": 10}


@pytest.mark.parametrize("limit", [0, 101, -1])
async def test_limit_fuera_de_rango_devuelve_422(cliente_pag, limit):
    respuesta = await cliente_pag.get("/items", params={"limit": limit})

    assert respuesta.status_code == 422


@pytest.mark.parametrize("offset", [-1, -50])
async def test_offset_negativo_devuelve_422(cliente_pag, offset):
    respuesta = await cliente_pag.get("/items", params={"offset": offset})

    assert respuesta.status_code == 422
