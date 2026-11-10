"""Verificación de consultas (C-04, DD-05): sin ``SELECT`` de existencia y
carga de libros en una sola consulta. Corre contra PostgreSQL y se salta sin
``DATABASE_URL``.
"""

from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros import service as libros_service
from app.modules.libros.models import Libro
from app.modules.libros.schemas import AutorLibroCreate, LibroCreate
from app.modules.ventas import service as ventas_service
from app.modules.ventas.schemas import RenglonCreate, VentaCreate


def _motor_con_captura(url):
    """Motor asincrónico sobre ``url`` que captura cada sentencia ejecutada."""
    motor = create_async_engine(url)
    declaraciones = []

    def _capturar(conn, cursor, statement, parameters, context, executemany):
        declaraciones.append(str(statement))

    event.listen(motor.sync_engine, "before_cursor_execute", _capturar)
    return motor, declaraciones


def _indice_insert(declaraciones):
    return next(
        i for i, s in enumerate(declaraciones) if s.lstrip().upper().startswith("INSERT")
    )


@pytest.mark.integration
async def test_alta_libro_sin_select_de_existencia(url_bd_test):
    motor, declaraciones = _motor_con_captura(url_bd_test)
    async with motor.begin() as conexion:
        await conexion.run_sync(SQLModel.metadata.drop_all)
        await conexion.run_sync(SQLModel.metadata.create_all)

    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion:
        editorial = Editorial(nombre="Sudamericana", pais="Argentina")
        genero = Genero(nombre="Novela")
        autor = Autor(nombre="Julio Cortázar", nacionalidad="Argentina")
        sesion.add_all([editorial, genero, autor])
        await sesion.commit()

        declaraciones.clear()
        datos = LibroCreate(
            isbn="978-1",
            titulo="Rayuela",
            precio=Decimal("25000.00"),
            stock=4,
            editorial_id=editorial.id,
            genero_id=genero.id,
            autores=[AutorLibroCreate(autor_id=autor.id, rol="autor", orden=1)],
        )
        await libros_service.crear(sesion, datos)

    await motor.dispose()

    previas = declaraciones[:_indice_insert(declaraciones)]
    assert all("SELECT" not in s.upper() for s in previas)


@pytest.mark.integration
async def test_venta_carga_libros_en_una_consulta(url_bd_test):
    motor, declaraciones = _motor_con_captura(url_bd_test)
    async with motor.begin() as conexion:
        await conexion.run_sync(SQLModel.metadata.drop_all)
        await conexion.run_sync(SQLModel.metadata.create_all)

    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    async with fabrica() as sesion:
        editorial = Editorial(nombre="Sudamericana", pais="Argentina")
        cliente = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
        sesion.add_all([editorial, cliente])
        await sesion.flush()
        l1 = Libro(
            isbn="978-1", titulo="Rayuela", precio=Decimal("25000.00"), stock=4,
            editorial_id=editorial.id,
        )
        l2 = Libro(
            isbn="978-2", titulo="Respiración artificial", precio=Decimal("27000.00"),
            stock=4, editorial_id=editorial.id,
        )
        sesion.add_all([l1, l2])
        await sesion.commit()

        declaraciones.clear()
        datos = VentaCreate(
            cliente_id=cliente.id,
            renglones=[
                RenglonCreate(libro_id=l1.id, cantidad=2),
                RenglonCreate(libro_id=l2.id, cantidad=1),
            ],
        )
        await ventas_service.crear(sesion, datos)

    await motor.dispose()

    desde_libro = [s for s in declaraciones if "FROM libro" in s]
    assert len(desde_libro) == 1
    assert "IN" in desde_libro[0]

    indice_select = next(i for i, s in enumerate(declaraciones) if "FROM libro" in s)
    assert indice_select < _indice_insert(declaraciones)
