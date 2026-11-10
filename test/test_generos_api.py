"""Pruebas del contrato de géneros (POST/GET y sus libros)."""

from decimal import Decimal

from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro


async def _crear(cliente_bd, nombre="Novela"):
    return await cliente_bd.post("/generos/", json={"nombre": nombre})


async def test_alta_genero_201(cliente_bd):
    respuesta = await _crear(cliente_bd)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] is not None
    assert cuerpo["nombre"] == "Novela"


async def test_alta_genero_nombre_repetido_409(cliente_bd):
    await _crear(cliente_bd, nombre="Poesía")

    repetido = await _crear(cliente_bd, nombre="Poesía")

    assert repetido.status_code == 409
    assert repetido.json()["detail"] == "El nombre ya está registrado"


async def test_listado_paginado_200(cliente_bd):
    await _crear(cliente_bd, nombre="A")
    await _crear(cliente_bd, nombre="B")

    respuesta = await cliente_bd.get("/generos/")

    assert respuesta.status_code == 200
    assert [g["nombre"] for g in respuesta.json()] == ["A", "B"]


async def test_listado_limit_fuera_de_rango_422(cliente_bd):
    respuesta = await cliente_bd.get("/generos/", params={"limit": 101})

    assert respuesta.status_code == 422


async def test_libros_de_genero_200(cliente_bd, sesion_bd):
    editorial = Editorial(nombre="E", pais="Argentina")
    sesion_bd.add(editorial)
    genero = Genero(nombre="Ensayo")
    sesion_bd.add(genero)
    await sesion_bd.flush()

    sesion_bd.add(
        Libro(
            isbn="978-000-0002",
            titulo="Respiración artificial",
            precio=Decimal("27000.00"),
            stock=3,
            editorial_id=editorial.id,
            genero_id=genero.id,
        )
    )
    await sesion_bd.commit()

    respuesta = await cliente_bd.get(f"/generos/{genero.id}/libros")

    assert respuesta.status_code == 200
    cuerpos = respuesta.json()
    assert [c["titulo"] for c in cuerpos] == ["Respiración artificial"]
    assert cuerpos[0]["genero"]["id"] == genero.id
    assert cuerpos[0]["precio"] == "27000.00"


async def test_libros_de_genero_404(cliente_bd):
    respuesta = await cliente_bd.get("/generos/9999/libros")

    assert respuesta.status_code == 404


async def test_genero_sin_libros_devuelve_lista_vacia(cliente_bd):
    creado = await _crear(cliente_bd, nombre="Sin libros")
    id_genero = creado.json()["id"]

    respuesta = await cliente_bd.get(f"/generos/{id_genero}/libros")

    assert respuesta.status_code == 200
    assert respuesta.json() == []
