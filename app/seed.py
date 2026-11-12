"""Datos iniciales idempotentes para una base de PostgreSQL vacía (C-05).

Se ejecuta con ``python -m app.seed`` en local y dentro del contenedor
(``docker exec libreria python -m app.seed``). Sembrar es seguro de repetir:
usa ids deterministas y ``ON CONFLICT DO NOTHING``, y nunca borra ni pisa filas
existentes (DD-10, SU-06).

El módulo no imprime la cadena de conexión ni credenciales: ``sembrar`` devuelve
los conteos y solo ``main`` los escribe, junto con errores genéricos en
``stderr`` (D.11).
"""

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from app.core.config import ConfigurationError, Settings, get_settings
from app.core.database import build_engine, build_session_factory

# Los seis imports deben ejecutarse antes de `create_all` para que
# `SQLModel.metadata` contenga las nueve tablas, igual que en `app/main.py`.
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta

TABLAS_CON_SECUENCIA = (
    "autor",
    "editorial",
    "genero",
    "libro",
    "cliente",
    "perfil_cliente",
    "venta",
    "renglon_venta",
)

TABLAS_SEMBRADAS = (
    "editorial",
    "genero",
    "autor",
    "libro",
    "libro_autor",
    "cliente",
    "perfil_cliente",
    "venta",
    "renglon_venta",
)

EDITORIALES = (
    {"id": 1, "nombre": "Sudamericana", "pais": "Argentina"},
)

GENEROS = (
    {"id": 1, "nombre": "Novela"},
)

AUTORES = (
    {"id": 1, "nombre": "Julio Cortázar", "nacionalidad": "Argentina"},
    {"id": 2, "nombre": "Ricardo Piglia", "nacionalidad": "Argentina"},
    {"id": 3, "nombre": "Gabriel García Márquez", "nacionalidad": "Colombia"},
    {"id": 4, "nombre": "Mario Vargas Llosa", "nacionalidad": "Perú"},
)

LIBROS = (
    {
        "id": 1,
        "isbn": "978-950-00-0001-1",
        "titulo": "Rayuela",
        "precio": Decimal("25000.00"),
        "stock": 10,
        "editorial_id": 1,
        "genero_id": 1,
    },
    {
        "id": 2,
        "isbn": "978-950-00-0002-8",
        "titulo": "Antología del cuento latinoamericano",
        "precio": Decimal("22000.00"),
        "stock": 6,
        "editorial_id": 1,
        "genero_id": 1,
    },
    {
        "id": 3,
        "isbn": "978-950-00-0003-5",
        "titulo": "La ciudad y los perros",
        "precio": Decimal("24000.00"),
        "stock": 5,
        "editorial_id": 1,
        "genero_id": 1,
    },
    {
        "id": 4,
        "isbn": "978-950-00-0004-2",
        "titulo": "Respiración artificial",
        "precio": Decimal("27000.00"),
        "stock": 8,
        "editorial_id": 1,
        "genero_id": 1,
    },
)

AUTORIAS = (
    {"libro_id": 1, "autor_id": 1, "rol": "autor", "orden": 1},
    {"libro_id": 2, "autor_id": 3, "rol": "autor", "orden": 1},
    {"libro_id": 2, "autor_id": 4, "rol": "coautor", "orden": 2},
    {"libro_id": 3, "autor_id": 4, "rol": "autor", "orden": 1},
    {"libro_id": 4, "autor_id": 2, "rol": "autor", "orden": 1},
)

CLIENTES = (
    {"id": 1, "nombre": "Ana Gómez", "email": "ana@example.com"},
    {"id": 2, "nombre": "Tomás Ríos", "email": "tomas@example.com"},
)

FECHA_VENTA = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

VENTAS = (
    {
        "id": 2,
        "cliente_id": 2,
        "fecha": FECHA_VENTA,
        "total": Decimal("77000.00"),
    },
)

RENGLONES = (
    {
        "id": 1,
        "venta_id": 2,
        "libro_id": 1,
        "cantidad": 2,
        "precio_unitario": Decimal("25000.00"),
    },
    {
        "id": 2,
        "venta_id": 2,
        "libro_id": 4,
        "cantidad": 1,
        "precio_unitario": Decimal("27000.00"),
    },
)


async def _insertar(
    sesion: AsyncSession, tabla, filas, columnas_clave
) -> None:
    """Inserta ``filas`` ignorando solo los conflictos de la clave indicada."""
    sentencia = (
        insert(tabla)
        .values(list(filas))
        .on_conflict_do_nothing(index_elements=columnas_clave)
    )
    await sesion.execute(sentencia)


async def _reposicionar_secuencias(sesion: AsyncSession) -> None:
    """Alinea cada secuencia con el máximo id para que la API no choque.

    ``is_called`` queda en ``false`` cuando la tabla está vacía (por ejemplo
    ``perfil_cliente``), de modo que el próximo ``nextval`` devuelve 1 y no 2.
    Los nombres de tabla provienen de la tupla constante del módulo.
    """
    for tabla in TABLAS_CON_SECUENCIA:
        await sesion.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {tabla}), 1), "
                f"(SELECT MAX(id) FROM {tabla}) IS NOT NULL)"
            )
        )


async def _contar(sesion: AsyncSession) -> dict[str, int]:
    """Devuelve ``{tabla: count(*)}`` para las nueve tablas del dominio."""
    conteos: dict[str, int] = {}
    for tabla in TABLAS_SEMBRADAS:
        resultado = await sesion.execute(text(f"SELECT count(*) FROM {tabla}"))
        conteos[tabla] = resultado.scalar_one()
    return conteos


async def sembrar(url: str | None = None) -> dict[str, int]:
    """Crea el esquema, carga el conjunto inicial y devuelve los conteos.

    Con ``url`` explícita apunta a esa base (los tests usan ``url_bd_test``);
    sin ``url`` usa ``DATABASE_URL`` a través de ``get_settings``. El seed nunca
    hereda ``SQL_ECHO``: su motor se crea siempre con ``sql_echo=False`` para
    que la salida solo tenga conteos (design §6). Todas las inserciones y el
    reposicionamiento de secuencias ocurren en una transacción y el motor se
    libera siempre en el ``finally``.
    """
    if url is None:
        url = get_settings().database_url
    engine = build_engine(Settings(database_url=url, sql_echo=False))
    factory = build_session_factory(engine)
    try:
        async with engine.begin() as conexion:
            await conexion.run_sync(SQLModel.metadata.create_all)

        async with factory() as sesion:
            await _insertar(sesion, Editorial.__table__, EDITORIALES, ["id"])
            await _insertar(sesion, Genero.__table__, GENEROS, ["id"])
            await _insertar(sesion, Autor.__table__, AUTORES, ["id"])
            await _insertar(sesion, Libro.__table__, LIBROS, ["id"])
            await _insertar(
                sesion, LibroAutor.__table__, AUTORIAS, ["libro_id", "autor_id"]
            )
            await _insertar(sesion, Cliente.__table__, CLIENTES, ["id"])
            await _insertar(sesion, Venta.__table__, VENTAS, ["id"])
            await _insertar(sesion, RenglonVenta.__table__, RENGLONES, ["id"])
            await _reposicionar_secuencias(sesion)
            await sesion.commit()
            return await _contar(sesion)
    finally:
        await engine.dispose()


def main() -> int:
    """Ejecuta el seed y traduce el resultado a código de salida.

    ``ConfigurationError`` → 2; ``IntegrityError`` y demás ``SQLAlchemyError``
    → 1. Los mensajes son genéricos y nunca incluyen la URL ni credenciales.
    """
    try:
        url = get_settings().database_url
        conteos = asyncio.run(sembrar(url))
    except ConfigurationError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 2
    except IntegrityError:
        print(
            "Error: los datos existentes no son compatibles con los ids del "
            "seed. Revisá el estado de la base; el seed no borra ni pisa filas.",
            file=sys.stderr,
        )
        return 1
    except SQLAlchemyError:
        print(
            "Error de conexión o de base de datos. Revisá DATABASE_URL y que el "
            "servidor PostgreSQL esté disponible.",
            file=sys.stderr,
        )
        return 1

    print("Seed aplicado: " + " ".join(f"{tabla}={n}" for tabla, n in conteos.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
