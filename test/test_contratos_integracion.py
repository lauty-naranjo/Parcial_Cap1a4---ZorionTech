"""Prueba de integración extremo a extremo del contrato (C-03) contra PostgreSQL.

Corre contra la base real (``DATABASE_URL``) y se salta si no está definida.
"""

from decimal import Decimal

import pytest

from app.modules.libros.models import Libro


@pytest.mark.integration
async def test_flujo_contrato_extremo_a_extremo(cliente_bd, sesion_bd):
    # Altas de referencia por la API.
    editorial = await cliente_bd.post(
        "/editoriales/", json={"nombre": "Sudamericana", "pais": "Argentina"}
    )
    assert editorial.status_code == 201
    id_editorial = editorial.json()["id"]

    genero = await cliente_bd.post("/generos/", json={"nombre": "Novela"})
    assert genero.status_code == 201
    id_genero = genero.json()["id"]

    autor = await cliente_bd.post(
        "/autores/", json={"nombre": "Julio Cortázar", "nacionalidad": "Argentina"}
    )
    assert autor.status_code == 201

    cliente = await cliente_bd.post(
        "/clientes/", json={"nombre": "Tomás Ríos", "email": "tomas@example.com"}
    )
    assert cliente.status_code == 201
    id_cliente = cliente.json()["id"]

    perfil = await cliente_bd.post(
        f"/clientes/{id_cliente}/perfil",
        json={"telefono": "555", "direccion": "Av. Siempreviva"},
    )
    assert perfil.status_code == 201

    # El alta de libro es C-04; se siembra directo para ejercitar la lectura.
    sesion_bd.add(
        Libro(
            isbn="978-950-00-0006-6",
            titulo="Rayuela",
            precio=Decimal("25000.00"),
            stock=4,
            editorial_id=id_editorial,
            genero_id=id_genero,
        )
    )
    await sesion_bd.commit()

    # Lectura de listados con limit/offset y precio serializado como string.
    libros = await cliente_bd.get("/libros/", params={"limit": 1, "offset": 0})
    assert libros.status_code == 200
    cuerpo = libros.json()[0]
    assert cuerpo["precio"] == "25000.00"
    assert isinstance(cuerpo["precio"], str)

    editoriales = await cliente_bd.get("/editoriales/", params={"limit": 5, "offset": 0})
    assert editoriales.status_code == 200
    assert editoriales.json()[0]["nombre"] == "Sudamericana"

    generos = await cliente_bd.get("/generos/", params={"limit": 5, "offset": 0})
    assert generos.status_code == 200
    assert generos.json()[0]["nombre"] == "Novela"
