"""Pruebas de las lecturas de venta: GET /ventas/ y GET /ventas/{id} (C-06)."""

from decimal import Decimal

from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta


async def _sembrar_ventas(sesion_bd, *, cantidad=2, renglones_por_venta=1):
    """Siembra un cliente, libros y ``cantidad`` ventas; devuelve sus ids."""
    editorial = Editorial(nombre="Sudamericana", pais="Argentina")
    cliente = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
    sesion_bd.add_all([editorial, cliente])
    await sesion_bd.flush()

    libros = []
    for i in range(1, cantidad * renglones_por_venta + 1):
        libro = Libro(
            isbn=f"978-{i}",
            titulo=f"Libro {i}",
            precio=Decimal("1000.00"),
            stock=5,
            editorial_id=editorial.id,
        )
        sesion_bd.add(libro)
        libros.append(libro)
    await sesion_bd.flush()

    ventas = []
    for v in range(cantidad):
        venta = Venta(
            cliente_id=cliente.id,
            total=Decimal("0.00"),
        )
        sesion_bd.add(venta)
        await sesion_bd.flush()
        total = Decimal("0.00")
        for r in range(renglones_por_venta):
            libro = libros[v * renglones_por_venta + r]
            sesion_bd.add(
                RenglonVenta(
                    venta_id=venta.id,
                    libro_id=libro.id,
                    cantidad=2,
                    precio_unitario=libro.precio,
                )
            )
            total += Decimal("2") * libro.precio
        venta.total = total
        ventas.append(venta)
    await sesion_bd.commit()
    return {"cliente_id": cliente.id, "ventas": [v.id for v in ventas]}


async def test_listado_ventas_200_con_cliente_y_renglones(cliente_bd, sesion_bd):
    datos = await _sembrar_ventas(sesion_bd)

    respuesta = await cliente_bd.get("/ventas/")

    assert respuesta.status_code == 200
    cuerpos = respuesta.json()
    assert len(cuerpos) == 2
    assert [c["id"] for c in cuerpos] == datos["ventas"]
    assert cuerpos[0]["cliente"]["nombre"] == "Tomás Ríos"
    assert cuerpos[0]["total"] == "2000.00"
    assert cuerpos[0]["renglones"][0]["titulo"] == "Libro 1"
    assert cuerpos[0]["renglones"][0]["subtotal"] == "2000.00"


async def test_listado_ventas_limit_y_offset(cliente_bd, sesion_bd):
    datos = await _sembrar_ventas(sesion_bd, cantidad=3)

    respuesta = await cliente_bd.get("/ventas/", params={"limit": 2, "offset": 1})

    assert respuesta.status_code == 200
    assert [c["id"] for c in respuesta.json()] == datos["ventas"][1:3]


async def test_listado_ventas_sin_parametros_usa_limit_20(cliente_bd, sesion_bd):
    """El default de RN-10 es ``limit=20`` y no un tope duro del endpoint.

    Se siembran 25 ventas: sin parámetros la respuesta se corta en 20 (las 20
    primeras por ``order_by(Venta.id)``); con ``?limit=25`` se devuelven las 25.
    Si el default no aplicara (por ejemplo, sin límite), el primer caso
    devolvería 25 y el test fallaría.
    """
    datos = await _sembrar_ventas(sesion_bd, cantidad=25)
    ids_sembrados = datos["ventas"]

    por_defecto = await cliente_bd.get("/ventas/")

    assert por_defecto.status_code == 200
    ids_por_defecto = [c["id"] for c in por_defecto.json()]
    assert len(ids_por_defecto) == 20
    assert ids_por_defecto == ids_sembrados[:20]

    con_limite_explicito = await cliente_bd.get("/ventas/", params={"limit": 25})

    assert con_limite_explicito.status_code == 200
    ids_con_limite = [c["id"] for c in con_limite_explicito.json()]
    assert len(ids_con_limite) == 25
    assert ids_con_limite == ids_sembrados


async def test_listado_ventas_limit_fuera_de_rango_422(cliente_bd):
    assert (await cliente_bd.get("/ventas/", params={"limit": 0})).status_code == 422
    assert (await cliente_bd.get("/ventas/", params={"limit": 101})).status_code == 422


async def test_listado_ventas_offset_negativo_422(cliente_bd):
    respuesta = await cliente_bd.get("/ventas/", params={"offset": -1})

    assert respuesta.status_code == 422


async def test_detalle_venta_200(cliente_bd, sesion_bd):
    datos = await _sembrar_ventas(sesion_bd, cantidad=1)

    respuesta = await cliente_bd.get(f"/ventas/{datos['ventas'][0]}")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == datos["ventas"][0]
    assert cuerpo["total"] == "2000.00"
    assert cuerpo["fecha"].endswith("Z")
    assert cuerpo["cliente"]["nombre"] == "Tomás Ríos"
    assert cuerpo["renglones"][0]["titulo"] == "Libro 1"


async def test_detalle_venta_404(cliente_bd):
    respuesta = await cliente_bd.get("/ventas/9999")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No encontrado"


async def test_detalle_venta_id_no_entero_422(cliente_bd):
    respuesta = await cliente_bd.get("/ventas/abc")

    assert respuesta.status_code == 422
