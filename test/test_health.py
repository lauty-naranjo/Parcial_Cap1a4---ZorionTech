"""Pruebas del contrato de los healthchecks (IN-03, D-06)."""

import os

import httpx
import pytest

from app.main import create_app

CUERPO_VIVO = {"estado": "vivo"}
CUERPO_LISTO = {"estado": "listo", "base": "ok"}
CUERPO_NO_LISTO = {"estado": "no_listo", "base": "error"}


async def test_live_responde_vivo_sin_que_exista_la_base(aplicacion, cliente):
    respuesta = await cliente.get("/health/live")

    assert respuesta.status_code == 200
    assert respuesta.json() == CUERPO_VIVO
    assert not hasattr(aplicacion.state, "engine")


async def test_live_sigue_vivo_aunque_la_dependencia_de_sesion_falle(
    cliente, usar_sesion, sesion_que_falla
):
    usar_sesion(sesion_que_falla)

    respuesta = await cliente.get("/health/live")

    assert respuesta.status_code == 200
    assert respuesta.json() == CUERPO_VIVO


async def test_ready_listo_cuando_la_base_responde(cliente, usar_sesion, sesion_disponible):
    usar_sesion(sesion_disponible)

    respuesta = await cliente.get("/health/ready")

    assert respuesta.status_code == 200
    assert respuesta.json() == CUERPO_LISTO


async def test_ready_no_listo_sin_filtrar_la_causa(cliente, usar_sesion, sesion_que_falla):
    usar_sesion(sesion_que_falla)

    respuesta = await cliente.get("/health/ready")

    assert respuesta.status_code == 503
    assert respuesta.json() == CUERPO_NO_LISTO
    assert "detail" not in respuesta.json()
    assert "password" not in respuesta.text
    assert "postgres" not in respuesta.text


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requiere DATABASE_URL y un PostgreSQL accesible",
)
async def test_ready_contra_postgresql_real():
    aplicacion = create_app()
    transporte = httpx.ASGITransport(app=aplicacion)

    async with aplicacion.router.lifespan_context(aplicacion):
        async with httpx.AsyncClient(transport=transporte, base_url="http://test") as http:
            respuesta = await http.get("/health/ready")

    assert respuesta.status_code == 200
    assert respuesta.json() == CUERPO_LISTO
