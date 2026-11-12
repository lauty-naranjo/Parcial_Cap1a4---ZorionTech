"""Replay automático de los archivos ``.http`` contra la app ASGI (C-10, D4).

Cada archivo se ejecuta completo, en orden y sobre una base recién sembrada:
un archivo por prueba, con ``motor_bd`` (esquema limpio), ``sembrar`` y
``cliente_bd``. Así los pares crear → duplicado del mismo archivo funcionan y
ningún bloque depende de una corrida anterior.

El aviso de comprobante (``BackgroundTasks``) se reemplaza por un no-op: el
comportamiento real está cubierto por ``test_asincronia.py`` y esperar 0.5 s
por venta solo haría lento el replay.

Los desvíos se acumulan y se reportan juntos con archivo, línea, esperado y
obtenido, de modo que un fallo no oculte los siguientes.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.seed import sembrar
from http_runner import ARCHIVOS_HTTP, BloqueHttp, coincide, leer_archivo

TEST = Path(__file__).resolve().parent
MAXIMO_CUERPO_EN_MENSAJE = 400


async def _noop(*args, **kwargs) -> None:
    """Sustituye el envío real del comprobante durante el replay."""


def _describir_desvio(bloque: BloqueHttp, respuesta: httpx.Response) -> str:
    fragmentos = " | ".join(bloque.esperado.fragmentos)
    cuerpo = respuesta.text
    if len(cuerpo) > MAXIMO_CUERPO_EN_MENSAJE:
        cuerpo = cuerpo[:MAXIMO_CUERPO_EN_MENSAJE] + "…"
    return (
        f"{bloque.archivo.name}:{bloque.linea} [{bloque.caso}] "
        f"{bloque.metodo} {bloque.ruta}\n"
        f"  esperado: {bloque.esperado.codigo} — {fragmentos}\n"
        f"  obtenido: {respuesta.status_code} — {cuerpo}"
    )


@pytest.mark.parametrize("nombre", ARCHIVOS_HTTP)
async def test_replay_de_archivo_http(
    nombre: str,
    motor_bd,
    cliente_bd,
    url_bd_test,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.modules.ventas.router.avisar_comprobante", _noop)
    await sembrar(url_bd_test)

    bloques = leer_archivo(TEST / nombre)
    assert bloques, f"test/{nombre} no declara requests ejecutables"

    desvios: list[str] = []
    for bloque in bloques:
        respuesta = await cliente_bd.request(
            bloque.metodo,
            bloque.ruta,
            content=bloque.cuerpo,
            headers=bloque.headers,
        )
        fallo_codigo = respuesta.status_code != bloque.esperado.codigo
        fallo_fragmento = [
            fragmento
            for fragmento in bloque.esperado.fragmentos
            if not coincide(respuesta.text, fragmento)
        ]
        if fallo_codigo or fallo_fragmento:
            desvios.append(_describir_desvio(bloque, respuesta))

    assert not desvios, "desvíos entre los .http y la API:\n\n" + "\n\n".join(desvios)


def test_el_mensaje_de_desvio_nombra_archivo_linea_y_esperado() -> None:
    bloque = BloqueHttp(
        archivo=TEST / "ventas.http",
        linea=17,
        descripcion="Caso C-06",
        caso="C-06",
        metodo="POST",
        ruta="/ventas/",
        headers={"Content-Type": "application/json"},
        cuerpo="{}",
        esperado=leer_archivo(TEST / "ventas.http")[-1].esperado,
    )
    respuesta = httpx.Response(status_code=500, text='{"detail": "boom"}')

    mensaje = _describir_desvio(bloque, respuesta)

    assert "ventas.http:17" in mensaje
    assert "[C-06]" in mensaje
    assert "POST /ventas/" in mensaje
    assert f"esperado: {bloque.esperado.codigo}" in mensaje
    assert "obtenido: 500" in mensaje
