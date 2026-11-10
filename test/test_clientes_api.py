"""Pruebas del contrato de clientes (alta, detalle con perfil, PATCH, perfil y ventas)."""

from app.modules.clientes.models import Cliente, PerfilCliente


async def _crear(cliente_bd, nombre="Tomás Ríos", email="tomas@example.com"):
    return await cliente_bd.post("/clientes/", json={"nombre": nombre, "email": email})


async def test_alta_cliente_201(cliente_bd):
    respuesta = await _crear(cliente_bd)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["id"] is not None
    assert cuerpo["nombre"] == "Tomás Ríos"
    assert cuerpo["email"] == "tomas@example.com"
    assert cuerpo["perfil"] is None


async def test_alta_cliente_email_repetido_409(cliente_bd):
    await _crear(cliente_bd, nombre="Uno", email="repetido@example.com")

    repetido = await _crear(cliente_bd, nombre="Dos", email="repetido@example.com")

    assert repetido.status_code == 409
    assert repetido.json()["detail"] == "El email ya está registrado"


async def test_alta_cliente_contrato_invalido_422(cliente_bd):
    sin_email = await cliente_bd.post("/clientes/", json={"nombre": "Sin email"})

    assert sin_email.status_code == 422


async def test_alta_cliente_email_invalido_422(cliente_bd):
    respuesta = await cliente_bd.post(
        "/clientes/", json={"nombre": "Mail malo", "email": "no-es-email"}
    )

    assert respuesta.status_code == 422


async def test_detalle_cliente_perfil_null_200(cliente_bd):
    creado = await _crear(cliente_bd)
    id_cliente = creado.json()["id"]

    respuesta = await cliente_bd.get(f"/clientes/{id_cliente}")

    assert respuesta.status_code == 200
    assert respuesta.json()["perfil"] is None


async def test_detalle_cliente_perfil_objeto_200(cliente_bd):
    creado = await _crear(cliente_bd)
    id_cliente = creado.json()["id"]
    await cliente_bd.post(
        f"/clientes/{id_cliente}/perfil",
        json={"telefono": "123", "direccion": "Calle 1"},
    )

    respuesta = await cliente_bd.get(f"/clientes/{id_cliente}")

    assert respuesta.status_code == 200
    perfil = respuesta.json()["perfil"]
    assert perfil is not None
    assert perfil["telefono"] == "123"
    assert perfil["direccion"] == "Calle 1"


async def test_detalle_cliente_404(cliente_bd):
    respuesta = await cliente_bd.get("/clientes/9999")

    assert respuesta.status_code == 404


async def test_patch_cliente_parcial_200(cliente_bd):
    creado = await _crear(cliente_bd, nombre="Original")
    id_cliente = creado.json()["id"]

    respuesta = await cliente_bd.patch(f"/clientes/{id_cliente}", json={"nombre": "Nuevo"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Nuevo"
    assert cuerpo["email"] == "tomas@example.com"


async def test_patch_cliente_404(cliente_bd):
    respuesta = await cliente_bd.patch("/clientes/9999", json={"nombre": "X"})

    assert respuesta.status_code == 404


async def test_patch_cliente_email_repetido_409(cliente_bd):
    await _crear(cliente_bd, nombre="A", email="a@example.com")
    otro = await _crear(cliente_bd, nombre="B", email="b@example.com")
    id_otro = otro.json()["id"]

    respuesta = await cliente_bd.patch(f"/clientes/{id_otro}", json={"email": "a@example.com"})

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El email ya está registrado"


async def test_patch_cliente_email_invalido_422(cliente_bd):
    creado = await _crear(cliente_bd)
    id_cliente = creado.json()["id"]

    respuesta = await cliente_bd.patch(f"/clientes/{id_cliente}", json={"email": "invalido"})

    assert respuesta.status_code == 422


async def test_alta_perfil_201(cliente_bd):
    creado = await _crear(cliente_bd)
    id_cliente = creado.json()["id"]

    respuesta = await cliente_bd.post(
        f"/clientes/{id_cliente}/perfil",
        json={"telefono": "555", "direccion": "Av. Siempreviva"},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["cliente_id"] == id_cliente
    assert cuerpo["telefono"] == "555"


async def test_alta_perfil_cliente_inexistente_404(cliente_bd):
    respuesta = await cliente_bd.post(
        "/clientes/9999/perfil", json={"telefono": "1", "direccion": "D"}
    )

    assert respuesta.status_code == 404


async def test_segundo_perfil_409(cliente_bd):
    creado = await _crear(cliente_bd)
    id_cliente = creado.json()["id"]
    cuerpo = {"telefono": "1", "direccion": "D"}
    await cliente_bd.post(f"/clientes/{id_cliente}/perfil", json=cuerpo)

    segundo = await cliente_bd.post(f"/clientes/{id_cliente}/perfil", json=cuerpo)

    assert segundo.status_code == 409
    assert segundo.json()["detail"] == "El cliente ya tiene un perfil"


async def test_ventas_de_cliente_200(cliente_bd):
    creado = await _crear(cliente_bd)
    id_cliente = creado.json()["id"]

    respuesta = await cliente_bd.get(f"/clientes/{id_cliente}/ventas")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


async def test_ventas_de_cliente_404(cliente_bd):
    respuesta = await cliente_bd.get("/clientes/9999/ventas")

    assert respuesta.status_code == 404


async def test_perfil_uno_a_uno_en_base(sesion_bd):
    cliente = Cliente(nombre="C", email="c@example.com")
    sesion_bd.add(cliente)
    await sesion_bd.flush()
    sesion_bd.add(PerfilCliente(cliente_id=cliente.id, telefono="1", direccion="D"))
    await sesion_bd.commit()

    assert cliente.id is not None
