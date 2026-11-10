"""Pruebas del registro de venta con renglones (POST /ventas/, C-04)."""

from decimal import Decimal

from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro


async def _sembrar(sesion_bd):
    editorial = Editorial(nombre="Sudamericana", pais="Argentina")
    cliente = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
    sesion_bd.add_all([editorial, cliente])
    await sesion_bd.flush()

    l1 = Libro(
        isbn="978-1", titulo="Rayuela", precio=Decimal("25000.00"), stock=5,
        editorial_id=editorial.id,
    )
    l2 = Libro(
        isbn="978-2", titulo="Respiración artificial", precio=Decimal("27000.00"),
        stock=5, editorial_id=editorial.id,
    )
    sesion_bd.add_all([l1, l2])
    await sesion_bd.commit()
    return {"cliente_id": cliente.id, "l1": l1.id, "l2": l2.id}


async def test_venta_201_con_renglones_y_subtotal(cliente_bd, sesion_bd):
    datos = await _sembrar(sesion_bd)

    respuesta = await cliente_bd.post(
        "/ventas/",
        json={
            "cliente_id": datos["cliente_id"],
            "renglones": [
                {"libro_id": datos["l1"], "cantidad": 2},
                {"libro_id": datos["l2"], "cantidad": 1},
            ],
        },
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["total"] == "77000.00"
    assert cuerpo["fecha"].endswith("Z")
    assert "+00:00" not in cuerpo["fecha"]
    assert cuerpo["cliente"]["nombre"] == "Tomás Ríos"

    por_titulo = {r["titulo"]: r for r in cuerpo["renglones"]}
    assert por_titulo["Rayuela"]["precio_unitario"] == "25000.00"
    assert por_titulo["Rayuela"]["subtotal"] == "50000.00"
    assert por_titulo["Rayuela"]["cantidad"] == 2
    assert por_titulo["Respiración artificial"]["precio_unitario"] == "27000.00"
    assert por_titulo["Respiración artificial"]["subtotal"] == "27000.00"


async def test_venta_cliente_inexistente_409(cliente_bd, sesion_bd):
    datos = await _sembrar(sesion_bd)

    respuesta = await cliente_bd.post(
        "/ventas/",
        json={
            "cliente_id": 9999,
            "renglones": [{"libro_id": datos["l1"], "cantidad": 1}],
        },
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El cliente indicado no existe"


async def test_venta_libro_inexistente_409(cliente_bd, sesion_bd):
    datos = await _sembrar(sesion_bd)

    respuesta = await cliente_bd.post(
        "/ventas/",
        json={
            "cliente_id": datos["cliente_id"],
            "renglones": [{"libro_id": 9999, "cantidad": 1}],
        },
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El libro indicado no existe"


async def test_venta_renglones_vacio_422(cliente_bd):
    respuesta = await cliente_bd.post("/ventas/", json={"cliente_id": 1, "renglones": []})

    assert respuesta.status_code == 422


async def test_venta_cantidad_no_positiva_422(cliente_bd):
    respuesta = await cliente_bd.post(
        "/ventas/",
        json={"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 0}]},
    )

    assert respuesta.status_code == 422


async def test_venta_libro_repetido_422(cliente_bd):
    respuesta = await cliente_bd.post(
        "/ventas/",
        json={
            "cliente_id": 1,
            "renglones": [
                {"libro_id": 1, "cantidad": 1},
                {"libro_id": 1, "cantidad": 2},
            ],
        },
    )

    assert respuesta.status_code == 422


async def test_precio_copiado_no_cambia_si_el_libro_cambia(cliente_bd, sesion_bd):
    datos = await _sembrar(sesion_bd)

    creada = await cliente_bd.post(
        "/ventas/",
        json={
            "cliente_id": datos["cliente_id"],
            "renglones": [{"libro_id": datos["l1"], "cantidad": 1}],
        },
    )
    assert creada.status_code == 201
    assert creada.json()["renglones"][0]["precio_unitario"] == "25000.00"

    libro = await sesion_bd.get(Libro, datos["l1"])
    libro.precio = Decimal("99999.00")
    await sesion_bd.commit()

    ventas = await cliente_bd.get(f"/clientes/{datos['cliente_id']}/ventas")
    assert ventas.status_code == 200
    renglon = ventas.json()[0]["renglones"][0]
    assert renglon["precio_unitario"] == "25000.00"
