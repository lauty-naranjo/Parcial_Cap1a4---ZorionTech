"""Pruebas de asincronía sin bloqueos (C-07): aviso en segundo plano y concurrencia.

Con ``httpx.ASGITransport`` el retorno del cliente ocurre recién cuando la app
terminó, incluidas las ``BackgroundTasks``. Por eso la latencia del cuerpo se
mide con un observador ASGI que marca el mensaje final ``http.response.body``
(ver ``design.md`` §Decisión 4), no con el retorno de ``await cliente.post``.
"""

import asyncio
import inspect
import logging
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.main import create_app
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro
from app.modules.ventas import tasks as ventas_tasks

RUTA_APP = Path(__file__).resolve().parents[1] / "app"
RUTAS_INTERNAS_DOCS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
PATRONES_BLOQUEANTES = ("time.sleep(", "requests.", "httpx.", "run_in_executor")
# Windows redondea el temporizador del event loop (~15 ms): 0.5 s puede medirse
# como 0.49 s. La tolerancia no debilita la prueba, que aún descarta tiempos ~0.
TOLERANCIA_SLEEP = 0.45


class ObservadorASGI:
    """Middleware ASGI que registra cuándo se envía el cuerpo final de cada respuesta."""

    def __init__(self, aplicacion: object) -> None:
        self.aplicacion = aplicacion
        self.cuerpos: list[tuple[float, float]] = []

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.aplicacion(scope, receive, send)
            return

        inicio = time.perf_counter()

        async def _send(mensaje: dict) -> None:
            if (
                mensaje["type"] == "http.response.body"
                and not mensaje.get("more_body", False)
            ):
                self.cuerpos.append((time.perf_counter() - inicio, time.time()))
            await send(mensaje)

        await self.aplicacion(scope, receive, _send)


@pytest_asyncio.fixture
async def cliente_observado(aplicacion, fabrica_sesion_bd):
    """Cliente ASGI con la base de test y el observador de respuestas."""

    async def _dependencia():
        async with fabrica_sesion_bd() as sesion:
            yield sesion

    aplicacion.dependency_overrides[get_session] = _dependencia
    observador = ObservadorASGI(aplicacion)
    transporte = ASGITransport(app=observador)
    async with AsyncClient(transport=transporte, base_url="http://test") as http:
        yield http, observador
    aplicacion.dependency_overrides.clear()


async def _sembrar(sesion_bd):
    editorial = Editorial(nombre="Sudamericana", pais="Argentina")
    cliente = Cliente(nombre="Ana Gómez", email="ana@example.com")
    sesion_bd.add_all([editorial, cliente])
    await sesion_bd.flush()
    libro = Libro(
        isbn="978-3", titulo="Cien años de soledad", precio=Decimal("15000.00"),
        stock=10, editorial_id=editorial.id,
    )
    sesion_bd.add(libro)
    await sesion_bd.commit()
    return {"cliente_id": cliente.id, "libro_id": libro.id, "email": cliente.email}


def _peticion(datos: dict, cantidad: int = 1) -> dict:
    return {
        "cliente_id": datos["cliente_id"],
        "renglones": [{"libro_id": datos["libro_id"], "cantidad": cantidad}],
    }


@pytest.mark.parametrize(
    "venta_id,email,total",
    [
        (1, "ana@example.com", Decimal("15000.00")),
        (42, "bruno@example.com", Decimal("1234567.89")),
    ],
)
async def test_avisar_comprobante_duerme_y_registra(venta_id, email, total, caplog):
    from app.modules.ventas.tasks import avisar_comprobante

    with caplog.at_level(logging.INFO, logger="app.modules.ventas.tasks"):
        inicio = time.perf_counter()
        await avisar_comprobante(venta_id, email, total)
        transcurrido = time.perf_counter() - inicio

    assert transcurrido >= TOLERANCIA_SLEEP
    registros = [r for r in caplog.records if r.name == "app.modules.ventas.tasks"]
    assert len(registros) == 1
    mensaje = registros[0].getMessage()
    assert f"venta={venta_id}" in mensaje
    assert email in mensaje
    assert f"{total:.2f}" in mensaje
    assert "postgresql://" not in mensaje
    assert "postgresql+asyncpg" not in mensaje
    assert "password" not in mensaje.lower()


async def test_aviso_que_falla_al_dormir_no_relanza(monkeypatch, caplog):
    async def _sleep_que_falla(_segundos: float) -> None:
        raise RuntimeError("fallo simulado del temporizador")

    monkeypatch.setattr(ventas_tasks, "asyncio", SimpleNamespace(sleep=_sleep_que_falla))

    with caplog.at_level(logging.ERROR, logger="app.modules.ventas.tasks"):
        await ventas_tasks.avisar_comprobante(7, "ana@example.com", Decimal("15000.00"))

    registros = [r for r in caplog.records if r.name == "app.modules.ventas.tasks"]
    assert len(registros) == 1
    assert registros[0].levelno == logging.ERROR
    assert registros[0].exc_info is not None
    assert "fallo simulado del temporizador" in str(registros[0].exc_info[1])
    assert "venta 7" in registros[0].getMessage()


async def test_aviso_que_falla_al_registrar_no_relanza(monkeypatch, caplog):
    def _info_que_falla(*_args, **_kwargs) -> None:
        raise RuntimeError("fallo simulado del logger")

    monkeypatch.setattr(ventas_tasks.logger, "info", _info_que_falla)

    with caplog.at_level(logging.ERROR, logger="app.modules.ventas.tasks"):
        await ventas_tasks.avisar_comprobante(8, "bruno@example.com", Decimal("10.00"))

    registros = [r for r in caplog.records if r.name == "app.modules.ventas.tasks"]
    assert len(registros) == 1
    assert registros[0].levelno == logging.ERROR
    assert registros[0].exc_info is not None
    assert "fallo simulado del logger" in str(registros[0].exc_info[1])
    assert "venta 8" in registros[0].getMessage()


async def test_respuesta_201_antes_del_aviso(cliente_observado, sesion_bd, caplog):
    cliente, observador = cliente_observado
    datos = await _sembrar(sesion_bd)

    with caplog.at_level(logging.INFO, logger="app.modules.ventas.tasks"):
        inicio = time.perf_counter()
        respuesta = await cliente.post("/ventas/", json=_peticion(datos))
        transcurrido = time.perf_counter() - inicio

    assert respuesta.status_code == 201
    assert len(observador.cuerpos) == 1
    latencia_cuerpo, cuerpo_wall_ts = observador.cuerpos[0]
    assert latencia_cuerpo < 0.5
    # El transporte ASGI espera la tarea de fondo: prueba de que el aviso corrió.
    assert transcurrido >= TOLERANCIA_SLEEP

    registros = [r for r in caplog.records if r.name == "app.modules.ventas.tasks"]
    assert len(registros) == 1
    assert registros[0].created >= cuerpo_wall_ts
    mensaje = registros[0].getMessage()
    assert str(respuesta.json()["id"]) in mensaje
    assert datos["email"] in mensaje


async def test_dos_ventas_concurrentes_no_se_bloquean(cliente_observado, sesion_bd, caplog):
    cliente, observador = cliente_observado
    datos = await _sembrar(sesion_bd)

    with caplog.at_level(logging.INFO, logger="app.modules.ventas.tasks"):
        inicio = time.perf_counter()
        primera, segunda = await asyncio.gather(
            cliente.post("/ventas/", json=_peticion(datos)),
            cliente.post("/ventas/", json=_peticion(datos, cantidad=2)),
        )
        total = time.perf_counter() - inicio

    assert primera.status_code == 201
    assert segunda.status_code == 201
    assert primera.json()["id"] != segunda.json()["id"]
    assert total < 0.9  # dos sleeps de 0.5 s solapados; si bloqueara serian ~1.0 s
    assert len(observador.cuerpos) == 2
    assert all(latencia < 0.5 for latencia, _ in observador.cuerpos)

    mensajes = [r.getMessage() for r in caplog.records if r.name == "app.modules.ventas.tasks"]
    assert len(mensajes) == 2
    assert all(datos["email"] in m for m in mensajes)


@pytest.mark.parametrize(
    "estado", [409, 422], ids=["cliente-inexistente-409", "contrato-invalido-422"]
)
async def test_venta_rechazada_no_agenda_aviso(
    cliente_observado, sesion_bd, caplog, estado
):
    cliente, observador = cliente_observado
    datos = await _sembrar(sesion_bd)
    if estado == 409:
        cuerpo = {
            "cliente_id": 9999,
            "renglones": [{"libro_id": datos["libro_id"], "cantidad": 1}],
        }
    else:
        cuerpo = {"cliente_id": datos["cliente_id"]}  # sin renglones → 422

    with caplog.at_level(logging.INFO, logger="app.modules.ventas.tasks"):
        respuesta = await cliente.post("/ventas/", json=cuerpo)

    assert respuesta.status_code == estado
    # Criterio determinista de "no se agendó": si la tarea hubiera corrido, el
    # cliente ASGI habria esperado su sleep y habria dejado su linea de log.
    assert len(observador.cuerpos) == 1
    assert [r for r in caplog.records if r.name == "app.modules.ventas.tasks"] == []


async def test_fallo_del_aviso_no_altera_la_venta(cliente_observado, sesion_bd, caplog, monkeypatch):
    """El 201 y la venta persistida sobreviven a un fallo real dentro del aviso.

    Se rompe el ``asyncio.sleep`` del módulo de tareas: la excepción ocurre ya
    con el cuerpo enviado. Como ``avisar_comprobante`` la atrapa y registra con
    ``logger.exception``, no se propaga al transporte ASGI y el cliente recibe
    el 201 normalmente.
    """
    async def _sleep_que_falla(_segundos: float) -> None:
        raise RuntimeError("fallo simulado del aviso")

    monkeypatch.setattr(ventas_tasks, "asyncio", SimpleNamespace(sleep=_sleep_que_falla))
    cliente, observador = cliente_observado
    datos = await _sembrar(sesion_bd)

    with caplog.at_level(logging.ERROR, logger="app.modules.ventas.tasks"):
        respuesta = await cliente.post("/ventas/", json=_peticion(datos))

    assert respuesta.status_code == 201
    venta = respuesta.json()
    assert venta["total"] == "15000.00"
    assert len(observador.cuerpos) == 1

    persistida = await cliente.get(f"/ventas/{venta['id']}")
    assert persistida.status_code == 200
    assert persistida.json()["id"] == venta["id"]
    assert persistida.json()["total"] == "15000.00"
    assert persistida.json()["cliente"]["email"] == datos["email"]

    registros = [r for r in caplog.records if r.name == "app.modules.ventas.tasks"]
    assert len(registros) == 1
    assert registros[0].levelno == logging.ERROR
    assert registros[0].exc_info is not None
    assert f"venta {venta['id']}" in registros[0].getMessage()


@pytest.mark.integration
async def test_aviso_en_segundo_plano_contra_postgres(cliente_observado, sesion_bd, caplog):
    """Extremo a extremo con PostgreSQL real: 201 rápido, log posterior y concurrencia."""
    cliente, observador = cliente_observado
    datos = await _sembrar(sesion_bd)

    with caplog.at_level(logging.INFO, logger="app.modules.ventas.tasks"):
        inicio = time.perf_counter()
        primera, segunda = await asyncio.gather(
            cliente.post("/ventas/", json=_peticion(datos)),
            cliente.post("/ventas/", json=_peticion(datos, cantidad=3)),
        )
        total = time.perf_counter() - inicio

    assert (primera.status_code, segunda.status_code) == (201, 201)
    ids = {primera.json()["id"], segunda.json()["id"]}
    assert len(ids) == 2
    assert len(observador.cuerpos) == 2
    assert total < 0.9
    for latencia_cuerpo, cuerpo_wall_ts in observador.cuerpos:
        assert latencia_cuerpo < 0.5
        registros = [
            r
            for r in caplog.records
            if r.name == "app.modules.ventas.tasks" and r.created >= cuerpo_wall_ts
        ]
        assert registros, "el aviso debe registrarse despues de la respuesta"
        assert datos["email"] in registros[0].getMessage()
    mensajes = [r.getMessage() for r in caplog.records if r.name == "app.modules.ventas.tasks"]
    assert len(mensajes) == 2
    for venta_id in ids:
        assert any(f"venta={venta_id} " in mensaje for mensaje in mensajes)


def _rutas_api(rutas, prefijo: str = "") -> list[tuple[str, object]]:
    """Aplana los routers incluidos (FastAPI los anida de forma perezosa)."""
    encontradas: list[tuple[str, object]] = []
    for ruta in rutas:
        original = getattr(ruta, "original_router", None)
        if original is not None:
            contexto = getattr(ruta, "include_context", None)
            subprefijo = getattr(contexto, "prefix", "") or ""
            encontradas.extend(_rutas_api(original.routes, prefijo + subprefijo))
        elif isinstance(ruta, APIRoute):
            encontradas.append((prefijo + ruta.path, ruta.endpoint))
    return encontradas


def test_configurar_logging_idempotente_stdout():
    import sys

    from app.core.logging import configurar_logging

    raiz = logging.getLogger()
    configurar_logging()
    configurar_logging()

    propios = [h for h in raiz.handlers if getattr(h, "_libreria_stdout", False)]
    assert len(propios) == 1
    assert propios[0].stream is sys.stdout
    formato = propios[0].formatter._fmt
    assert all(
        campo in formato
        for campo in ("%(asctime)s", "%(levelname)s", "%(name)s", "%(message)s")
    )
    assert raiz.level == logging.INFO


def test_dos_apps_no_duplican_el_handler_stdout():
    raiz = logging.getLogger()
    create_app()
    create_app()

    propios = [h for h in raiz.handlers if getattr(h, "_libreria_stdout", False)]
    assert len(propios) == 1


def test_todos_los_handlers_son_corrutinas(aplicacion):
    rutas = [
        (ruta, endpoint)
        for ruta, endpoint in _rutas_api(aplicacion.router.routes)
        if ruta not in RUTAS_INTERNAS_DOCS
    ]
    assert len(rutas) >= 20
    sincronas = [
        f"{ruta} -> {endpoint.__name__}"
        for ruta, endpoint in rutas
        if not inspect.iscoroutinefunction(endpoint)
    ]
    assert sincronas == []


def test_app_no_contiene_llamadas_bloqueantes():
    archivos = sorted(RUTA_APP.rglob("*.py"))
    assert len(archivos) >= 10
    hallazgos = [
        f"{patron} en {archivo.relative_to(RUTA_APP.parent)}"
        for archivo in archivos
        for patron in PATRONES_BLOQUEANTES
        if patron in archivo.read_text(encoding="utf-8")
    ]
    assert hallazgos == []

