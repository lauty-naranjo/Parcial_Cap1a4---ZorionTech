"""Pruebas del contrato de editoriales (POST/GET/PATCH y sus libros)."""

from decimal import Decimal

import pytest

from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro


async def _crear(cliente_bd, nombre="Emece", pais="Argentina"):
    return await cliente_bd.post("/editoriales/", json={"nombre": nombre, "pais": pais})


async def test_alta_editorial_201(cliente_bd):
    respuesta = await _crear(cliente_bd)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] is not None
    assert cuerpo["nombre"] == "Emece"
    assert cuerpo["pais"] == "Argentina"


async def test_alta_editorial_nombre_repetido_409(cliente_bd):
    await _crear(cliente_bd, nombre="Sudamericana")

    repetida = await _crear(cliente_bd, nombre="Sudamericana", pais="Uruguay")

    assert repetida.status_code == 409
    assert repetida.json()["detail"] == "El nombre ya está registrado"


async def test_alta_editorial_contrato_invalido_422(cliente_bd):
    respuesta = await cliente_bd.post("/editoriales/", json={"nombre": "Sin país"})

    assert respuesta.status_code == 422


async def test_listado_paginado_200(cliente_bd):
    await _crear(cliente_bd, nombre="A")
    await _crear(cliente_bd, nombre="B")
    await _crear(cliente_bd, nombre="C")

    respuesta = await cliente_bd.get("/editoriales/")

    assert respuesta.status_code == 200
    cuerpos = respuesta.json()
    assert [c["nombre"] for c in cuerpos] == ["A", "B", "C"]


async def test_listado_limit_fuera_de_rango_422(cliente_bd):
    respuesta = await cliente_bd.get("/editoriales/", params={"limit": 0})

    assert respuesta.status_code == 422


async def test_detalle_200(cliente_bd):
    creada = await _crear(cliente_bd, nombre="Planeta")
    id_creada = creada.json()["id"]

    respuesta = await cliente_bd.get(f"/editoriales/{id_creada}")

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Planeta"


async def test_detalle_404(cliente_bd):
    respuesta = await cliente_bd.get("/editoriales/9999")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No encontrado"


async def test_detalle_id_no_entero_422(cliente_bd):
    respuesta = await cliente_bd.get("/editoriales/abc")

    assert respuesta.status_code == 422


async def test_patch_parcial_200(cliente_bd):
    creada = await _crear(cliente_bd, nombre="Alfaguara", pais="España")
    id_creada = creada.json()["id"]

    respuesta = await cliente_bd.patch(f"/editoriales/{id_creada}", json={"pais": "Argentina"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["pais"] == "Argentina"
    assert cuerpo["nombre"] == "Alfaguara"


async def test_patch_404(cliente_bd):
    respuesta = await cliente_bd.patch("/editoriales/9999", json={"pais": "X"})

    assert respuesta.status_code == 404


async def test_patch_nombre_repetido_409(cliente_bd):
    await _crear(cliente_bd, nombre="Existente")
    otra = await _crear(cliente_bd, nombre="Otra")
    id_otra = otra.json()["id"]

    respuesta = await cliente_bd.patch(f"/editoriales/{id_otra}", json={"nombre": "Existente"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El nombre ya está registrado"


async def test_libros_de_editorial_200(cliente_bd, sesion_bd):
    creada = await _crear(cliente_bd, nombre="Con libros")
    id_editorial = creada.json()["id"]

    sesion_bd.add(
        Libro(
            isbn="978-000-0001",
            titulo="Rayuela",
            precio=Decimal("25000.00"),
            stock=4,
            editorial_id=id_editorial,
        )
    )
    await sesion_bd.commit()

    respuesta = await cliente_bd.get(f"/editoriales/{id_editorial}/libros")

    assert respuesta.status_code == 200
    cuerpos = respuesta.json()
    assert [c["titulo"] for c in cuerpos] == ["Rayuela"]
    assert cuerpos[0]["precio"] == "25000.00"


async def test_libros_de_editorial_404(cliente_bd):
    respuesta = await cliente_bd.get("/editoriales/9999/libros")

    assert respuesta.status_code == 404


async def test_editorial_sin_libros_devuelve_lista_vacia(cliente_bd):
    creada = await _crear(cliente_bd, nombre="Sin libros")
    id_editorial = creada.json()["id"]

    respuesta = await cliente_bd.get(f"/editoriales/{id_editorial}/libros")

    assert respuesta.status_code == 200
    assert respuesta.json() == []
