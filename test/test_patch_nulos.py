"""PATCH con ``null`` explícito: 422 por contrato y recurso intacto.

Un campo que el contrato declara no nulo, enviado explícitamente como ``null``,
no cumple el cuerpo del PATCH: debe rechazarse en la validación de FastAPI
(422), nunca llegar al ``NOT NULL`` de la base ni traducirse a 409.

La clave es distinguir **omitido** (válido en un PATCH parcial) de **null
explícito** (violación de contrato). ``genero_id`` de libro es nullable y
conserva su semántica: ``null`` sigue devolviendo 200.
"""

from decimal import Decimal

import pytest

from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor


async def _crear_editorial(cliente_bd, nombre="Emece", pais="Argentina"):
    respuesta = await cliente_bd.post(
        "/editoriales/", json={"nombre": nombre, "pais": pais}
    )
    assert respuesta.status_code == 201
    return respuesta.json()


async def _crear_autor(cliente_bd, nombre="Julio Cortázar", nacionalidad="Argentina"):
    respuesta = await cliente_bd.post(
        "/autores/", json={"nombre": nombre, "nacionalidad": nacionalidad}
    )
    assert respuesta.status_code == 201
    return respuesta.json()


async def _crear_cliente(cliente_bd, nombre="Tomás Ríos", email="tomas@example.com"):
    respuesta = await cliente_bd.post(
        "/clientes/", json={"nombre": nombre, "email": email}
    )
    assert respuesta.status_code == 201
    return respuesta.json()


async def _sembrar_libro(sesion_bd):
    """Crea editorial, género, autor, libro y autoría; devuelve sus ids."""
    editorial = Editorial(nombre="Ed", pais="Argentina")
    genero = Genero(nombre="Gen")
    autor = Autor(nombre="Aut", nacionalidad="Argentina")
    sesion_bd.add_all([editorial, genero, autor])
    await sesion_bd.flush()

    libro = Libro(
        isbn="978-000-0001",
        titulo="Rayuela",
        precio=Decimal("25000.00"),
        stock=3,
        editorial_id=editorial.id,
        genero_id=genero.id,
    )
    sesion_bd.add(libro)
    await sesion_bd.flush()
    sesion_bd.add(
        LibroAutor(libro_id=libro.id, autor_id=autor.id, rol="autor", orden=1)
    )
    await sesion_bd.commit()

    return {
        "libro_id": libro.id,
        "editorial_id": editorial.id,
        "genero_id": genero.id,
    }


# --- Editoriales -----------------------------------------------------------


async def test_patch_editorial_nombre_null_422(cliente_bd):
    editorial = await _crear_editorial(cliente_bd)
    url = f"/editoriales/{editorial['id']}"
    antes = (await cliente_bd.get(url)).json()

    respuesta = await cliente_bd.patch(url, json={"nombre": None})

    assert respuesta.status_code == 422
    assert "detail" in respuesta.json()
    assert (await cliente_bd.get(url)).json() == antes


async def test_patch_editorial_pais_null_422(cliente_bd):
    editorial = await _crear_editorial(cliente_bd)
    url = f"/editoriales/{editorial['id']}"
    antes = (await cliente_bd.get(url)).json()

    respuesta = await cliente_bd.patch(url, json={"pais": None})

    assert respuesta.status_code == 422
    assert (await cliente_bd.get(url)).json() == antes


# --- Autores ---------------------------------------------------------------


async def test_patch_autor_nombre_null_422(cliente_bd):
    autor = await _crear_autor(cliente_bd)
    url = f"/autores/{autor['id']}"
    antes = (await cliente_bd.get(url)).json()

    respuesta = await cliente_bd.patch(url, json={"nombre": None})

    assert respuesta.status_code == 422
    assert (await cliente_bd.get(url)).json() == antes


async def test_patch_autor_nacionalidad_null_422(cliente_bd):
    autor = await _crear_autor(cliente_bd)
    url = f"/autores/{autor['id']}"
    antes = (await cliente_bd.get(url)).json()

    respuesta = await cliente_bd.patch(url, json={"nacionalidad": None})

    assert respuesta.status_code == 422
    assert (await cliente_bd.get(url)).json() == antes


# --- Clientes --------------------------------------------------------------


async def test_patch_cliente_nombre_null_422(cliente_bd):
    cliente = await _crear_cliente(cliente_bd)
    url = f"/clientes/{cliente['id']}"
    antes = (await cliente_bd.get(url)).json()

    respuesta = await cliente_bd.patch(url, json={"nombre": None})

    assert respuesta.status_code == 422
    assert (await cliente_bd.get(url)).json() == antes


async def test_patch_cliente_email_null_422(cliente_bd):
    cliente = await _crear_cliente(cliente_bd)
    url = f"/clientes/{cliente['id']}"
    antes = (await cliente_bd.get(url)).json()

    respuesta = await cliente_bd.patch(url, json={"email": None})

    assert respuesta.status_code == 422
    assert (await cliente_bd.get(url)).json() == antes


# --- Libros: campos escalares no nulos -------------------------------------


@pytest.mark.parametrize(
    "campo",
    ["isbn", "titulo", "precio", "stock", "editorial_id"],
)
async def test_patch_libro_campo_no_nulo_en_null_422_sin_cambios(
    cliente_bd, sesion_bd, campo
):
    sem = await _sembrar_libro(sesion_bd)
    url = f"/libros/{sem['libro_id']}"
    antes = (await cliente_bd.get(url)).json()

    respuesta = await cliente_bd.patch(url, json={campo: None})

    assert respuesta.status_code == 422
    assert (await cliente_bd.get(url)).json() == antes


# --- Libros: ``genero_id`` es nullable -------------------------------------


async def test_patch_libro_genero_id_null_sigue_siendo_200(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd)
    url = f"/libros/{sem['libro_id']}"

    respuesta = await cliente_bd.patch(url, json={"genero_id": None})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["genero"] is None
    assert cuerpo["titulo"] == "Rayuela"


# --- Combinado: el rechazo no debe aplicar el resto ------------------------


async def test_patch_libro_null_combinado_422_no_aplica_el_resto(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd)
    url = f"/libros/{sem['libro_id']}"
    antes = (await cliente_bd.get(url)).json()

    respuesta = await cliente_bd.patch(url, json={"titulo": None, "stock": 5})

    assert respuesta.status_code == 422
    despues = (await cliente_bd.get(url)).json()
    assert despues == antes
    assert despues["stock"] == 3


# --- Omitir un campo sigue siendo válido (PATCH parcial) -------------------


async def test_patch_omitir_campo_actualiza_el_resto_editorial(cliente_bd):
    editorial = await _crear_editorial(cliente_bd)

    respuesta = await cliente_bd.patch(
        f"/editoriales/{editorial['id']}", json={"pais": "Uruguay"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["pais"] == "Uruguay"
    assert cuerpo["nombre"] == "Emece"


async def test_patch_omitir_campo_actualiza_el_resto_autor(cliente_bd):
    autor = await _crear_autor(cliente_bd)

    respuesta = await cliente_bd.patch(
        f"/autores/{autor['id']}", json={"nacionalidad": "Uruguaya"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nacionalidad"] == "Uruguaya"
    assert cuerpo["nombre"] == "Julio Cortázar"


async def test_patch_omitir_campo_actualiza_el_resto_cliente(cliente_bd):
    cliente = await _crear_cliente(cliente_bd)

    respuesta = await cliente_bd.patch(
        f"/clientes/{cliente['id']}", json={"nombre": "Nuevo Nombre"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Nuevo Nombre"
    assert cuerpo["email"] == "tomas@example.com"


async def test_patch_omitir_campo_actualiza_el_resto_libro(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd)

    respuesta = await cliente_bd.patch(f"/libros/{sem['libro_id']}", json={"stock": 9})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["stock"] == 9
    assert cuerpo["titulo"] == "Rayuela"
    assert cuerpo["precio"] == "25000.00"
