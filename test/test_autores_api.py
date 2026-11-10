"""Pruebas del contrato de autores (POST/GET/PATCH y sus libros con rol/orden)."""

from decimal import Decimal

from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro, LibroAutor


async def _crear(cliente_bd, nombre="Julio Cortázar", nacionalidad="Argentina"):
    return await cliente_bd.post("/autores/", json={"nombre": nombre, "nacionalidad": nacionalidad})


async def test_alta_autor_201(cliente_bd):
    respuesta = await _crear(cliente_bd)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] is not None
    assert cuerpo["nombre"] == "Julio Cortázar"
    assert cuerpo["nacionalidad"] == "Argentina"


async def test_alta_autor_contrato_invalido_422(cliente_bd):
    respuesta = await cliente_bd.post("/autores/", json={"nombre": "Sin nacionalidad"})

    assert respuesta.status_code == 422


async def test_detalle_autor_200(cliente_bd):
    creado = await _crear(cliente_bd, nombre="Borges")
    id_autor = creado.json()["id"]

    respuesta = await cliente_bd.get(f"/autores/{id_autor}")

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Borges"


async def test_detalle_autor_404(cliente_bd):
    respuesta = await cliente_bd.get("/autores/9999")

    assert respuesta.status_code == 404


async def test_detalle_autor_id_no_entero_422(cliente_bd):
    respuesta = await cliente_bd.get("/autores/abc")

    assert respuesta.status_code == 422


async def test_patch_autor_parcial_200(cliente_bd):
    creado = await _crear(cliente_bd, nombre="Bioy", nacionalidad="Argentina")
    id_autor = creado.json()["id"]

    respuesta = await cliente_bd.patch(f"/autores/{id_autor}", json={"nacionalidad": "Uruguaya"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nacionalidad"] == "Uruguaya"
    assert cuerpo["nombre"] == "Bioy"


async def test_patch_autor_404(cliente_bd):
    respuesta = await cliente_bd.patch("/autores/9999", json={"nombre": "X"})

    assert respuesta.status_code == 404


async def test_patch_autor_contrato_invalido_422(cliente_bd):
    creado = await _crear(cliente_bd)
    id_autor = creado.json()["id"]

    respuesta = await cliente_bd.patch(f"/autores/{id_autor}", json={"nacionalidad": 123})

    assert respuesta.status_code == 422


async def test_libros_de_autor_con_rol_y_orden_200(cliente_bd, sesion_bd):
    editorial = Editorial(nombre="E", pais="Argentina")
    sesion_bd.add(editorial)
    autor = Autor(nombre="Autora", nacionalidad="Argentina")
    sesion_bd.add(autor)
    await sesion_bd.flush()

    libro = Libro(
        isbn="978-000-0003",
        titulo="Bestiario",
        precio=Decimal("18000.00"),
        stock=2,
        editorial_id=editorial.id,
    )
    sesion_bd.add(libro)
    await sesion_bd.flush()

    sesion_bd.add(LibroAutor(libro_id=libro.id, autor_id=autor.id, rol="autor", orden=1))
    await sesion_bd.commit()

    respuesta = await cliente_bd.get(f"/autores/{autor.id}/libros")

    assert respuesta.status_code == 200
    cuerpos = respuesta.json()
    assert len(cuerpos) == 1
    assert cuerpos[0]["titulo"] == "Bestiario"
    assert cuerpos[0]["rol"] == "autor"
    assert cuerpos[0]["orden"] == 1
    assert cuerpos[0]["editorial"]["nombre"] == "E"


async def test_libros_de_autor_404(cliente_bd):
    respuesta = await cliente_bd.get("/autores/9999/libros")

    assert respuesta.status_code == 404


async def test_autor_sin_libros_devuelve_lista_vacia(cliente_bd):
    creado = await _crear(cliente_bd, nombre="Sin libros")
    id_autor = creado.json()["id"]

    respuesta = await cliente_bd.get(f"/autores/{id_autor}/libros")

    assert respuesta.status_code == 200
    assert respuesta.json() == []
