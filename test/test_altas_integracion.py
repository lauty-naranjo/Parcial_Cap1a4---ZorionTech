"""Prueba de integración de altas con relaciones (C-04) contra PostgreSQL real.

Se salta si ``DATABASE_URL`` no está definida (patrón de ``test/conftest.py``).
"""

import pytest


@pytest.mark.integration
async def test_flujo_altas_extremo_a_extremo(cliente_bd):
    # Referencias por la API.
    editorial = await cliente_bd.post(
        "/editoriales/", json={"nombre": "Sudamericana", "pais": "Argentina"}
    )
    assert editorial.status_code == 201
    id_editorial = editorial.json()["id"]

    genero = await cliente_bd.post("/generos/", json={"nombre": "Novela"})
    assert genero.status_code == 201
    id_genero = genero.json()["id"]

    autor1 = await cliente_bd.post(
        "/autores/", json={"nombre": "Julio Cortázar", "nacionalidad": "Argentina"}
    )
    autor2 = await cliente_bd.post(
        "/autores/", json={"nombre": "Ricardo Piglia", "nacionalidad": "Argentina"}
    )
    assert autor1.status_code == 201
    assert autor2.status_code == 201
    id_autor1 = autor1.json()["id"]
    id_autor2 = autor2.json()["id"]

    cliente = await cliente_bd.post(
        "/clientes/", json={"nombre": "Tomás Ríos", "email": "tomas@example.com"}
    )
    assert cliente.status_code == 201
    id_cliente = cliente.json()["id"]

    # Alta de libros con autorías.
    libro1 = await cliente_bd.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0006-6",
            "titulo": "Rayuela",
            "precio": "25000.00",
            "stock": 4,
            "editorial_id": id_editorial,
            "genero_id": id_genero,
            "autores": [{"autor_id": id_autor1, "rol": "autor", "orden": 1}],
        },
    )
    assert libro1.status_code == 201
    id_libro1 = libro1.json()["id"]

    libro2 = await cliente_bd.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0007-3",
            "titulo": "Respiración artificial",
            "precio": "27000.00",
            "stock": 3,
            "editorial_id": id_editorial,
            "genero_id": id_genero,
            "autores": [{"autor_id": id_autor2, "rol": "autor", "orden": 1}],
        },
    )
    assert libro2.status_code == 201
    id_libro2 = libro2.json()["id"]

    # Venta con dos renglones: 2×25000 + 1×27000 = 77000.00 (C-06).
    venta = await cliente_bd.post(
        "/ventas/",
        json={
            "cliente_id": id_cliente,
            "renglones": [
                {"libro_id": id_libro1, "cantidad": 2},
                {"libro_id": id_libro2, "cantidad": 1},
            ],
        },
    )
    assert venta.status_code == 201
    cuerpo = venta.json()
    assert cuerpo["total"] == "77000.00"
    assert cuerpo["fecha"].endswith("Z")
    assert len(cuerpo["renglones"]) == 2

    # C-04: editorial/autor inexistente → 409.
    editorial_404 = await cliente_bd.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0008-0",
            "titulo": "X",
            "precio": "1000.00",
            "stock": 1,
            "editorial_id": 99999,
            "genero_id": id_genero,
            "autores": [{"autor_id": id_autor1, "rol": "autor", "orden": 1}],
        },
    )
    assert editorial_404.status_code == 409

    autor_404 = await cliente_bd.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0009-7",
            "titulo": "Y",
            "precio": "1000.00",
            "stock": 1,
            "editorial_id": id_editorial,
            "genero_id": id_genero,
            "autores": [{"autor_id": 99999, "rol": "autor", "orden": 1}],
        },
    )
    assert autor_404.status_code == 409

    # C-05: cliente/libro inexistente → 409.
    cliente_404 = await cliente_bd.post(
        "/ventas/",
        json={"cliente_id": 99999, "renglones": [{"libro_id": id_libro1, "cantidad": 1}]},
    )
    assert cliente_404.status_code == 409

    libro_404 = await cliente_bd.post(
        "/ventas/",
        json={"cliente_id": id_cliente, "renglones": [{"libro_id": 99999, "cantidad": 1}]},
    )
    assert libro_404.status_code == 409
