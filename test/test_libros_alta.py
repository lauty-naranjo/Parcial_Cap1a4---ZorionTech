"""Pruebas del alta de libro con autorías (POST /libros/, C-04)."""


async def _ids_base(cliente_bd):
    editorial = await cliente_bd.post(
        "/editoriales/", json={"nombre": "Sudamericana", "pais": "Argentina"}
    )
    assert editorial.status_code == 201
    genero = await cliente_bd.post("/generos/", json={"nombre": "Novela"})
    assert genero.status_code == 201
    autor = await cliente_bd.post(
        "/autores/", json={"nombre": "Julio Cortázar", "nacionalidad": "Argentina"}
    )
    assert autor.status_code == 201
    return {
        "editorial_id": editorial.json()["id"],
        "genero_id": genero.json()["id"],
        "autor_id": autor.json()["id"],
    }


def _cuerpo(ids, **sobre):
    cuerpo = {
        "isbn": "978-950-00-0006-6",
        "titulo": "Rayuela",
        "precio": "25000.00",
        "stock": 4,
        "editorial_id": ids["editorial_id"],
        "genero_id": ids["genero_id"],
        "autores": [{"autor_id": ids["autor_id"], "rol": "autor", "orden": 1}],
    }
    cuerpo.update(sobre)
    return cuerpo


async def test_alta_libro_201_con_relaciones(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post("/libros/", json=_cuerpo(ids))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] is not None
    assert cuerpo["titulo"] == "Rayuela"
    assert cuerpo["precio"] == "25000.00"
    assert cuerpo["editorial"]["nombre"] == "Sudamericana"
    assert cuerpo["genero"]["nombre"] == "Novela"
    autores = cuerpo["autores"]
    assert len(autores) == 1
    assert autores[0]["autor_id"] == ids["autor_id"]
    assert autores[0]["nombre"] == "Julio Cortázar"
    assert autores[0]["rol"] == "autor"
    assert autores[0]["orden"] == 1


async def test_alta_libro_isbn_repetido_409(cliente_bd):
    ids = await _ids_base(cliente_bd)
    await cliente_bd.post("/libros/", json=_cuerpo(ids))

    repetido = await cliente_bd.post("/libros/", json=_cuerpo(ids, titulo="Otro"))

    assert repetido.status_code == 409
    assert repetido.json()["detail"] == "El ISBN ya está registrado"


async def test_alta_libro_editorial_inexistente_409(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post("/libros/", json=_cuerpo(ids, editorial_id=9999))

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "La editorial indicada no existe"


async def test_alta_libro_autor_inexistente_409(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post(
        "/libros/",
        json=_cuerpo(ids, autores=[{"autor_id": 9999, "rol": "autor", "orden": 1}]),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El autor indicado no existe"


async def test_alta_libro_genero_inexistente_409(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post("/libros/", json=_cuerpo(ids, genero_id=9999))

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El género indicado no existe"


async def test_alta_libro_precio_invalido_422(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post("/libros/", json=_cuerpo(ids, precio="0"))

    assert respuesta.status_code == 422


async def test_alta_libro_stock_negativo_422(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post("/libros/", json=_cuerpo(ids, stock=-1))

    assert respuesta.status_code == 422


async def test_alta_libro_rol_invalido_422(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post(
        "/libros/",
        json=_cuerpo(
            ids, autores=[{"autor_id": ids["autor_id"], "rol": "director", "orden": 1}]
        ),
    )

    assert respuesta.status_code == 422


async def test_alta_libro_orden_invalido_422(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post(
        "/libros/",
        json=_cuerpo(
            ids, autores=[{"autor_id": ids["autor_id"], "rol": "autor", "orden": 0}]
        ),
    )

    assert respuesta.status_code == 422


async def test_alta_libro_autor_repetido_422(cliente_bd):
    ids = await _ids_base(cliente_bd)

    respuesta = await cliente_bd.post(
        "/libros/",
        json=_cuerpo(
            ids,
            autores=[
                {"autor_id": ids["autor_id"], "rol": "autor", "orden": 1},
                {"autor_id": ids["autor_id"], "rol": "coautor", "orden": 2},
            ],
        ),
    )

    assert respuesta.status_code == 422
