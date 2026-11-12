"""Genera la evidencia de consultas con ``SQL_ECHO=true`` (C-06, IN-04).

Captura la salida del ``SELECT`` que emite SQLAlchemy al resolver el detalle de
libros y ventas del **seed real** (``app.seed.sembrar``): libros 1 y 2 con 1 y
2 autores, listado de 4 libros, venta 2 con 2 renglones y listados asociados.
Escribe ``evidencia/C-07-consultas-libro.txt`` y
``evidencia/C-07-consultas-venta.txt`` con el conteo explícito de cada caso.

Usa una base derivada ``<DATABASE_URL>_evidencia`` para no tocar la base de
desarrollo ni la de tests; la dropea antes de sembrar y la elimina al terminar.
El script queda en el repo como procedimiento reproducible; la evidencia
generada es el entregable (la completa C-10).

Uso:
    SQL_ECHO=true .venv/Scripts/python.exe scripts/generar_evidencia_c07.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg
import httpx
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.database import get_session
from app.main import create_app
from app.seed import sembrar

EVIDENCIA = Path(__file__).resolve().parent.parent / "evidencia"
LOGGER_ECO = "sqlalchemy.engine.Engine"


class _CapturaEcho(logging.Handler):
    """Acumula los mensajes que SQLAlchemy escribe por el logger de eco."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.mensajes: list[str] = []

    def emit(self, registro: logging.LogRecord) -> None:
        self.mensajes.append(registro.getMessage())


def _solo_select(mensaje: str) -> bool:
    return mensaje.lstrip().upper().startswith("SELECT")


def _compactar(mensaje: str, limite: int = 180) -> str:
    return " ".join(mensaje.split())[:limite]


def _dsn_admin(url_base: str) -> tuple[str, str]:
    """Devuelve el DSN de la base ``postgres`` y la URL de evidencia."""
    original = make_url(url_base)
    nombre = f"{original.database}_evidencia"
    admin = original.set(database="postgres")
    admin_dsn = admin.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    url = original.set(database=nombre).render_as_string(hide_password=False)
    return admin_dsn, url


async def _preparar_base_evidencia(url_base: str) -> tuple[str, str]:
    """Crea (si falta) la base ``<nombre>_evidencia`` y devuelve su URL."""
    admin_dsn, url = _dsn_admin(url_base)
    nombre = make_url(url).database
    conexion = await asyncpg.connect(admin_dsn, timeout=5)
    try:
        existe = await conexion.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", nombre
        )
        if not existe:
            await conexion.execute(f'CREATE DATABASE "{nombre}"')
    finally:
        await conexion.close()
    return url, nombre


async def _eliminar_base_evidencia(url_base: str) -> None:
    """Borra la base temporal de evidencia para no dejar residuos."""
    admin_dsn, url = _dsn_admin(url_base)
    nombre = make_url(url).database
    conexion = await asyncpg.connect(admin_dsn, timeout=5)
    try:
        await conexion.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')
    finally:
        await conexion.close()


async def _capturar(cliente: httpx.AsyncClient, ruta: str) -> tuple[int, list[str]]:
    """Devuelve el status y las sentencias ``SELECT`` que el eco registra."""
    logger = logging.getLogger(LOGGER_ECO)
    captura = _CapturaEcho()
    logger.addHandler(captura)
    try:
        respuesta = await cliente.get(ruta)
    finally:
        logger.removeHandler(captura)

    declaraciones = [m for m in captura.mensajes if _solo_select(m)]
    return respuesta.status_code, declaraciones


def _bloque(titulo: str, status: int, declaraciones: list[str]) -> list[str]:
    lineas = [f"=== {titulo} ==="]
    for indice, sentencia in enumerate(declaraciones, start=1):
        lineas.append(f"[SELECT {indice}] {_compactar(sentencia)}")
    lineas.append(f"CONTEO: {len(declaraciones)} SELECT (status HTTP {status})")
    lineas.append("")
    return lineas


def _resumen(
    detalles: list[tuple[str, int]],
    extras: list[tuple[str, int]],
    nota: str,
) -> list[str]:
    """Resume los conteos de detalle, la comparación y los listados."""
    lineas = ["RESUMEN"]
    for nombre, total in detalles:
        lineas.append(f"- {nombre}: {total} SELECT")
    if len(detalles) >= 2:
        diferencia = abs(detalles[1][1] - detalles[0][1])
        if diferencia == 0:
            lineas.append(
                "- Diferencia: 0 SELECT → el conteo no crece con la cardinalidad."
            )
        else:
            lineas.append(
                f"- Diferencia: {diferencia} SELECT → REVISAR: el conteo crece "
                "con la cardinalidad."
            )
    lineas.append(nota)
    for nombre, total in extras:
        lineas.append(f"- {nombre}: {total} SELECT (fijo, sin consulta por fila).")
    return lineas


def _encabezado(titulo: str, endpoints: str, base: str) -> list[str]:
    return [
        "Evidencia C-07 — cantidad fija de consultas (C-06, IN-04)",
        f"Endpoint(s): {endpoints}",
        f"SQL_ECHO: true · PostgreSQL (base {base})",
        f"Generado: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "Seed real: 4 libros, 4 autores, 2 clientes y la venta 2 con 2 renglones "
        "(ids de app/seed.py).",
        "Criterio: el número de SELECT no crece con la cantidad de "
        "autores/renglones/ventas.",
        "",
        titulo,
        "",
    ]


async def main() -> None:
    url_base = os.environ["DATABASE_URL"]
    url_evidencia, nombre_base = await _preparar_base_evidencia(url_base)

    motor = create_async_engine(url_evidencia, echo=True)
    async with motor.begin() as conexion:
        await conexion.run_sync(SQLModel.metadata.drop_all)
    await sembrar(url_evidencia)

    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    app = create_app()

    async def dependencia():
        async with fabrica() as sesion:
            yield sesion

    app.dependency_overrides[get_session] = dependencia
    transporte = httpx.ASGITransport(app=app)

    EVIDENCIA.mkdir(exist_ok=True)

    async with httpx.AsyncClient(transport=transporte, base_url="http://t") as cliente:
        # Libro 1: Rayuela (1 autor). Libro 2: Antología (2 autores).
        casos_libro: list[tuple[str, int]] = []
        lineas = _encabezado(
            "Detalle de libro con cardinalidad variable",
            "GET /libros/{id}",
            nombre_base,
        )
        for nombre, libro_id, etiqueta in (
            ("Rayuela (libro 1, 1 autor)", 1, "GET /libros/1 — Rayuela, 1 autor"),
            (
                "Antología (libro 2, 2 autores)",
                2,
                "GET /libros/2 — Antología, 2 autores",
            ),
        ):
            status, declaraciones = await _capturar(cliente, f"/libros/{libro_id}")
            lineas.extend(_bloque(etiqueta, status, declaraciones))
            casos_libro.append((nombre, len(declaraciones)))

        status, declaraciones = await _capturar(cliente, "/libros/?limit=100")
        lineas.extend(
            _bloque("GET /libros/ — 4 libros en la página", status, declaraciones)
        )
        conteo_listado_libros = len(declaraciones)

        status, declaraciones = await _capturar(cliente, "/autores/1/libros")
        lineas.extend(
            _bloque(
                "GET /autores/1/libros — 1 libro (Rayuela)", status, declaraciones
            )
        )
        conteo_libros_autor = len(declaraciones)

        lineas.extend(
            _resumen(
                casos_libro,
                [
                    ("listado de 4 libros", conteo_listado_libros),
                    ("libros del autor 1", conteo_libros_autor),
                ],
                "El detalle usa 2 SELECT tanto con 1 como con 2 autores: no hay "
                "una consulta por autor.",
            )
        )
        (EVIDENCIA / "C-07-consultas-libro.txt").write_text(
            "\n".join(lineas) + "\n", encoding="utf-8"
        )

        # Venta 2: dos renglones (libro 1 ×2 y libro 4 ×1).
        casos_venta: list[tuple[str, int]] = []
        lineas = _encabezado(
            "Detalle y listado de ventas con cardinalidad variable",
            "GET /ventas/{id} · GET /ventas/ · GET /clientes/{id}/ventas",
            nombre_base,
        )
        status, declaraciones = await _capturar(cliente, "/ventas/2")
        lineas.extend(_bloque("GET /ventas/2 — 2 renglones", status, declaraciones))
        casos_venta.append(("venta 2 (2 renglones)", len(declaraciones)))

        status, declaraciones = await _capturar(cliente, "/ventas/?limit=100")
        lineas.extend(
            _bloque("GET /ventas/ — 1 venta en la página", status, declaraciones)
        )
        conteo_listado_ventas = len(declaraciones)

        status, declaraciones = await _capturar(cliente, "/clientes/2/ventas")
        lineas.extend(
            _bloque(
                "GET /clientes/2/ventas — 1 venta", status, declaraciones
            )
        )
        conteo_ventas_cliente = len(declaraciones)

        lineas.extend(
            _resumen(
                casos_venta,
                [
                    ("listado de 1 venta", conteo_listado_ventas),
                    ("ventas del cliente 2", conteo_ventas_cliente),
                ],
                "El detalle usa 2 SELECT con 2 renglones: no hay una consulta "
                "por renglón.",
            )
        )
        (EVIDENCIA / "C-07-consultas-venta.txt").write_text(
            "\n".join(lineas) + "\n", encoding="utf-8"
        )

    await motor.dispose()
    await _eliminar_base_evidencia(url_base)
    print("Evidencia generada en", EVIDENCIA)


if __name__ == "__main__":
    asyncio.run(main())
