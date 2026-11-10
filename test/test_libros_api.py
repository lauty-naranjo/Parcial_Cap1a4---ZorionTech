"""Pruebas del contrato de libros (listado, detalle y edición escalar)."""

from decimal import Decimal

from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor


async def _sembrar_libro(
    sesion_bd,
    *,
    titulo="Rayuela",
    isbn="978-000-0001",
    precio="25000.00",
    con_genero=True,
    con_autor=True,
):
    """Crea editorial, género, autor, libro y autoría; devuelve sus ids."""
    editorial = Editorial(nombre=f"Ed {titulo}", pais="Argentina")
    sesion_bd.add(editorial)
    genero = Genero(nombre=f"Gen {titulo}") if con_genero else None
    if genero is not None:
        sesion_bd.add(genero)
    autor = Autor(nombre=f"Aut {titulo}", nacionalidad="Argentina") if con_autor else None
    if autor is not None:
        sesion_bd.add(autor)
    await sesion_bd.flush()

    libro = Libro(
        isbn=isbn,
        titulo=titulo,
        precio=Decimal(precio),
        stock=5,
        editorial_id=editorial.id,
        genero_id=genero.id if genero is not None else None,
    )
    sesion_bd.add(libro)
    await sesion_bd.flush()

    if autor is not None:
        sesion_bd.add(LibroAutor(libro_id=libro.id, autor_id=autor.id, rol="autor", orden=1))
    await sesion_bd.commit()

    return {
        "libro_id": libro.id,
        "editorial_id": editorial.id,
        "genero_id": genero.id if genero is not None else None,
        "autor_id": autor.id if autor is not None else None,
    }


async def test_listado_200_con_editorial_y_genero(cliente_bd, sesion_bd):
    await _sembrar_libro(sesion_bd)

    respuesta = await cliente_bd.get("/libros/")

    assert respuesta.status_code == 200
    cuerpos = respuesta.json()
    assert len(cuerpos) == 1
    assert cuerpos[0]["titulo"] == "Rayuela"
    assert cuerpos[0]["precio"] == "25000.00"
    assert cuerpos[0]["editorial"]["nombre"] == "Ed Rayuela"
    assert cuerpos[0]["genero"]["nombre"] == "Gen Rayuela"


async def test_filtro_titulo_parcial_insensible_a_mayusculas(cliente_bd, sesion_bd):
    await _sembrar_libro(sesion_bd, titulo="Rayuela")

    respuesta = await cliente_bd.get("/libros/", params={"titulo": "RAYU"})

    assert respuesta.status_code == 200
    assert [c["titulo"] for c in respuesta.json()] == ["Rayuela"]


async def test_filtro_genero_id(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd, titulo="Uno")
    await _sembrar_libro(sesion_bd, titulo="Dos", isbn="978-000-0002")

    respuesta = await cliente_bd.get("/libros/", params={"genero_id": sem["genero_id"]})

    assert respuesta.status_code == 200
    assert [c["titulo"] for c in respuesta.json()] == ["Uno"]


async def test_busqueda_injection_sql_devuelve_lista_vacia(cliente_bd, sesion_bd):
    await _sembrar_libro(sesion_bd, titulo="Rayuela")

    respuesta = await cliente_bd.get("/libros/", params={"titulo": "' OR '1'='1"})

    assert respuesta.status_code == 200
    assert respuesta.json() == []


async def test_listado_limit_fuera_de_rango_422(cliente_bd):
    respuesta = await cliente_bd.get("/libros/", params={"limit": 0})

    assert respuesta.status_code == 422


async def test_listado_offset_negativo_422(cliente_bd):
    respuesta = await cliente_bd.get("/libros/", params={"offset": -1})

    assert respuesta.status_code == 422


async def test_detalle_200_con_autores(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd, titulo="Bestiario", isbn="978-000-0003")

    respuesta = await cliente_bd.get(f"/libros/{sem['libro_id']}")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["titulo"] == "Bestiario"
    assert cuerpo["editorial"]["nombre"] == "Ed Bestiario"
    autores = cuerpo["autores"]
    assert len(autores) == 1
    assert autores[0]["nombre"] == "Aut Bestiario"
    assert autores[0]["rol"] == "autor"
    assert autores[0]["orden"] == 1


async def test_detalle_404(cliente_bd):
    respuesta = await cliente_bd.get("/libros/9999")

    assert respuesta.status_code == 404


async def test_patch_parcial_200(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd)

    respuesta = await cliente_bd.patch(
        f"/libros/{sem['libro_id']}", json={"titulo": "Rayuela (nueva)"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["titulo"] == "Rayuela (nueva)"
    assert cuerpo["isbn"] == "978-000-0001"
    assert cuerpo["precio"] == "25000.00"


async def test_patch_404(cliente_bd):
    respuesta = await cliente_bd.patch("/libros/9999", json={"titulo": "X"})

    assert respuesta.status_code == 404


async def test_patch_isbn_repetido_409(cliente_bd, sesion_bd):
    await _sembrar_libro(sesion_bd, titulo="Uno", isbn="978-000-0001")
    sem2 = await _sembrar_libro(sesion_bd, titulo="Dos", isbn="978-000-0002")

    respuesta = await cliente_bd.patch(f"/libros/{sem2['libro_id']}", json={"isbn": "978-000-0001"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El ISBN ya está registrado"


async def test_patch_editorial_inexistente_409(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd)

    respuesta = await cliente_bd.patch(f"/libros/{sem['libro_id']}", json={"editorial_id": 9999})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "La editorial indicada no existe"


async def test_patch_genero_inexistente_409(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd)

    respuesta = await cliente_bd.patch(f"/libros/{sem['libro_id']}", json={"genero_id": 9999})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El género indicado no existe"


async def test_patch_precio_invalido_422(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd)

    respuesta = await cliente_bd.patch(f"/libros/{sem['libro_id']}", json={"precio": 0})

    assert respuesta.status_code == 422


async def test_patch_stock_negativo_422(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd)

    respuesta = await cliente_bd.patch(f"/libros/{sem['libro_id']}", json={"stock": -1})

    assert respuesta.status_code == 422


async def test_patch_ignora_autores_y_conserva_autorias(cliente_bd, sesion_bd):
    sem = await _sembrar_libro(sesion_bd, titulo="Original")

    respuesta = await cliente_bd.patch(
        f"/libros/{sem['libro_id']}",
        json={"titulo": "Nuevo", "autores": []},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["titulo"] == "Nuevo"
    assert len(cuerpo["autores"]) == 1
