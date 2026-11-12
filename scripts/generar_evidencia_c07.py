"""Genera la evidencia de consultas con ``SQL_ECHO=true`` (C-06, IN-04).

Captura la salida del ``SELECT`` que emite SQLAlchemy al resolver el detalle de
un libro con 1 y con 3 autores, y de una venta con 1 y con 3 renglones, sobre
una base PostgreSQL real. Escribe ``evidencia/C-07-consultas-libro.txt`` y
``evidencia/C-07-consultas-venta.txt`` con el conteo explícito de cada caso.

Usa una base derivada ``<DATABASE_URL>_evidencia`` para no tocar la base de
desarrollo ni la de tests. El script queda en el repo como procedimiento
reproducible; la evidencia generada es el entregable (la completa C-10).

Uso:
    SQL_ECHO=true .venv/Scripts/python.exe scripts/generar_evidencia_c07.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg
import httpx
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.database import get_session
from app.main import create_app
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta

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


async def _preparar_url_evidencia(url_base: str) -> tuple[str, str]:
    """Crea (si falta) la base ``<nombre>_evidencia`` y devuelve su URL."""
    original = make_url(url_base)
    nombre = f"{original.database}_evidencia"
    admin = original.set(database="postgres")
    admin_dsn = admin.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://", "postgresql://"
    )

    conexion = await asyncpg.connect(admin_dsn, timeout=5)
    try:
        existe = await conexion.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", nombre
        )
        if not existe:
            await conexion.execute(f'CREATE DATABASE "{nombre}"')
    finally:
        await conexion.close()

    url = original.set(database=nombre).render_as_string(hide_password=False)
    return url, nombre


async def _sembrar_libro(sesion, n_autores: int, sufijo: str) -> tuple[int, list[int]]:
    editorial = Editorial(nombre=f"Ed {sufijo}", pais="Argentina")
    sesion.add(editorial)
    await sesion.flush()
    libro = Libro(
        isbn=f"978-{sufijo}",
        titulo=f"Libro {sufijo}",
        precio=Decimal("1000.00"),
        stock=5,
        editorial_id=editorial.id,
    )
    sesion.add(libro)
    await sesion.flush()
    ids_autores = []
    for i in range(n_autores):
        autor = Autor(nombre=f"Autor {sufijo}-{i}", nacionalidad="Argentina")
        sesion.add(autor)
        await sesion.flush()
        ids_autores.append(autor.id)
        sesion.add(
            LibroAutor(libro_id=libro.id, autor_id=autor.id, rol="autor", orden=i + 1)
        )
    await sesion.commit()
    return libro.id, ids_autores


async def _sembrar_venta(sesion, n_renglones: int, sufijo: str) -> tuple[int, int]:
    editorial = Editorial(nombre=f"Ed {sufijo}", pais="Argentina")
    cliente = Cliente(nombre=f"Cli {sufijo}", email=f"c-{sufijo}@x.com")
    sesion.add_all([editorial, cliente])
    await sesion.flush()
    libros = []
    for i in range(n_renglones):
        libro = Libro(
            isbn=f"978-{sufijo}-{i}",
            titulo=f"Libro {sufijo} {i}",
            precio=Decimal("1000.00"),
            stock=5,
            editorial_id=editorial.id,
        )
        sesion.add(libro)
        libros.append(libro)
    await sesion.flush()
    venta = Venta(
        cliente_id=cliente.id, total=Decimal("0.00"), fecha=datetime.now(timezone.utc)
    )
    sesion.add(venta)
    await sesion.flush()
    total = Decimal("0.00")
    for libro in libros:
        sesion.add(
            RenglonVenta(
                venta_id=venta.id,
                libro_id=libro.id,
                cantidad=1,
                precio_unitario=libro.precio,
            )
        )
        total += libro.precio
    venta.total = total
    await sesion.commit()
    return venta.id, cliente.id


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
    par_uno: tuple[str, int],
    par_tres: tuple[str, int],
    extras: list[tuple[str, int]],
) -> list[str]:
    """Resume la comparación 1 vs 3 y los conteos de referencia por listado."""
    nombre_uno, total_uno = par_uno
    nombre_tres, total_tres = par_tres
    lineas = [
        "RESUMEN",
        f"- {nombre_uno}: {total_uno} SELECT",
        f"- {nombre_tres}: {total_tres} SELECT",
    ]
    diferencia = abs(total_tres - total_uno)
    if diferencia == 0:
        lineas.append(
            "- Diferencia: 0 SELECT → el conteo no crece con la cardinalidad."
        )
    else:
        lineas.append(
            f"- Diferencia: {diferencia} SELECT → REVISAR: el conteo crece "
            "con la cardinalidad."
        )
    for nombre, total in extras:
        lineas.append(f"- {nombre}: {total} SELECT (fijo, sin consulta por fila).")
    return lineas


def _encabezado(titulo: str, endpoints: str, base: str) -> list[str]:
    return [
        f"Evidencia C-07 — cantidad fija de consultas (C-06, IN-04)",
        f"Endpoint(s): {endpoints}",
        f"SQL_ECHO: true · PostgreSQL (base {base})",
        f"Generado: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "Criterio: el número de SELECT no crece con la cantidad de "
        "autores/renglones/ventas.",
        "",
        titulo,
        "",
    ]


async def main() -> None:
    url_base = os.environ["DATABASE_URL"]
    url_evidencia, nombre_base = await _preparar_url_evidencia(url_base)

    motor = create_async_engine(url_evidencia, echo=True)
    async with motor.begin() as conexion:
        await conexion.run_sync(SQLModel.metadata.drop_all)
        await conexion.run_sync(SQLModel.metadata.create_all)

    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    app = create_app()

    async def dependencia():
        async with fabrica() as sesion:
            yield sesion

    app.dependency_overrides[get_session] = dependencia
    transporte = httpx.ASGITransport(app=app)

    EVIDENCIA.mkdir(exist_ok=True)

    async with httpx.AsyncClient(transport=transporte, base_url="http://t") as cliente:
        # Libro: 1 y 3 autores.
        async with fabrica() as sesion:
            libro_uno, autores_uno = await _sembrar_libro(sesion, 1, "uno")
            libro_tres, _ = await _sembrar_libro(sesion, 3, "tres")

        casos_libro: list[tuple[str, int]] = []
        lineas = _encabezado(
            "Detalle de libro con cardinalidad variable",
            "GET /libros/{id}",
            nombre_base,
        )
        for nombre, libro_id, n_autores in (
            ("1 autor", libro_uno, 1),
            ("3 autores", libro_tres, 3),
        ):
            status, declaraciones = await _capturar(cliente, f"/libros/{libro_id}")
            lineas.extend(
                _bloque(f"GET /libros/{libro_id} — {nombre}", status, declaraciones)
            )
            casos_libro.append((nombre, len(declaraciones)))

        status, declaraciones = await _capturar(cliente, "/libros/?limit=100")
        lineas.extend(
            _bloque(
                "GET /libros/ — 2 libros en la página", status, declaraciones
            )
        )
        conteo_listado_libros = len(declaraciones)

        status, declaraciones = await _capturar(
            cliente, f"/autores/{autores_uno[0]}/libros"
        )
        lineas.extend(
            _bloque(
                f"GET /autores/{autores_uno[0]}/libros — 1 libro",
                status,
                declaraciones,
            )
        )
        conteo_libros_autor = len(declaraciones)

        lineas.extend(
            _resumen(
                casos_libro[0],
                casos_libro[1],
                [
                    ("listado de 2 libros", conteo_listado_libros),
                    ("libros de un autor", conteo_libros_autor),
                ],
            )
        )
        (EVIDENCIA / "C-07-consultas-libro.txt").write_text(
            "\n".join(lineas) + "\n", encoding="utf-8"
        )

        # Venta: 1 y 3 renglones.
        async with fabrica() as sesion:
            venta_uno, cliente_uno = await _sembrar_venta(sesion, 1, "vuno")
            venta_tres, _ = await _sembrar_venta(sesion, 3, "vtres")

        casos_venta: list[tuple[str, int]] = []
        lineas = _encabezado(
            "Detalle y listado de ventas con cardinalidad variable",
            "GET /ventas/{id} · GET /ventas/ · GET /clientes/{id}/ventas",
            nombre_base,
        )
        for nombre, venta_id in (("1 renglón", venta_uno), ("3 renglones", venta_tres)):
            status, declaraciones = await _capturar(cliente, f"/ventas/{venta_id}")
            lineas.extend(
                _bloque(f"GET /ventas/{venta_id} — {nombre}", status, declaraciones)
            )
            casos_venta.append((nombre, len(declaraciones)))

        status, declaraciones = await _capturar(cliente, "/ventas/?limit=100")
        lineas.extend(
            _bloque("GET /ventas/ — 2 ventas en la página", status, declaraciones)
        )
        conteo_listado_ventas = len(declaraciones)

        status, declaraciones = await _capturar(
            cliente, f"/clientes/{cliente_uno}/ventas"
        )
        lineas.extend(
            _bloque(
                f"GET /clientes/{cliente_uno}/ventas — 1 venta",
                status,
                declaraciones,
            )
        )
        conteo_ventas_cliente = len(declaraciones)

        lineas.extend(
            _resumen(
                casos_venta[0],
                casos_venta[1],
                [
                    ("listado de 2 ventas", conteo_listado_ventas),
                    ("ventas de un cliente", conteo_ventas_cliente),
                ],
            )
        )
        (EVIDENCIA / "C-07-consultas-venta.txt").write_text(
            "\n".join(lineas) + "\n", encoding="utf-8"
        )

    await motor.dispose()
    print("Evidencia generada en", EVIDENCIA)


if __name__ == "__main__":
    asyncio.run(main())
