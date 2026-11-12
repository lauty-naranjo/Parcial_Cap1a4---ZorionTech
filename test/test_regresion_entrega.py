"""Guardas de regresión de los contratos de entrega (C-10, D5–D7).

Cubre los huecos G3 a G6 del design sin duplicar los tests por módulo:

- G3: RN-12 de extremo a extremo (409, 404 y 422 por HTTP).
- G4: C-01 demuestra que el handler no se ejecutó (cero consultas).
- G5: RN-10 en las ocho colecciones y sub-colecciones.
- G6: importes siempre como string decimal de dos decimales.
"""

from __future__ import annotations

import re

import pytest

from app.main import create_app
from app.seed import sembrar
from contador_consultas import contador_consultas

COLECCIONES = (
    "/editoriales/",
    "/generos/",
    "/libros/",
    "/ventas/",
    "/editoriales/1/libros",
    "/generos/1/libros",
    "/autores/1/libros",
    "/clientes/2/ventas",
)

# Las sub-colecciones llevan ids del seed; el OpenAPI las declara con parámetros.
PLANTILLAS_OPENAPI = {
    "/editoriales/1/libros": "/editoriales/{editorial_id}/libros",
    "/generos/1/libros": "/generos/{genero_id}/libros",
    "/autores/1/libros": "/autores/{autor_id}/libros",
    "/clientes/2/ventas": "/clientes/{cliente_id}/ventas",
}

RUTAS_INVALIDAS = (
    ("GET", "/libros/abc"),
    ("GET", "/editoriales/abc"),
    ("GET", "/generos/abc/libros"),
    ("GET", "/autores/abc"),
    ("GET", "/clientes/abc"),
    ("GET", "/clientes/abc/ventas"),
    ("GET", "/ventas/abc"),
    ("PATCH", "/libros/abc"),
)

TEXTO_INTERNO_PROHIBIDO = (
    "duplicate key",
    "violates",
    "constraint",
    "Traceback",
    "asyncpg",
    "psycopg",
    "IntegrityError",
    "SELECT",
    "uq_",
    "fk_",
)

PATRON_IMPORTE = re.compile(r"^\d+\.\d{2}$")


async def _noop(*args, **kwargs) -> None:
    """Evita la espera de 0.5 s del aviso de comprobante en la venta C-06."""


def _verificar_importe(valor: object, etiqueta: str) -> None:
    assert isinstance(valor, str), f"{etiqueta} debe ser string, no {type(valor).__name__}"
    assert PATRON_IMPORTE.fullmatch(valor), f"{etiqueta} no es decimal de dos cifras: {valor!r}"


# --- G4: 422 sin ejecutar el handler (C-01) --------------------------------


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_INVALIDAS)
async def test_parametro_de_ruta_invalido_no_consulta(
    metodo: str,
    ruta: str,
    motor_bd,
    cliente_bd,
    url_bd_test,
) -> None:
    await sembrar(url_bd_test)

    with contador_consultas(motor_bd) as cuenta:
        respuesta = await cliente_bd.request(metodo, ruta)

    assert respuesta.status_code == 422, f"{metodo} {ruta} devolvió {respuesta.status_code}"
    assert cuenta.total == 0, (
        f"{metodo} {ruta} ejecutó {cuenta.total} consultas antes de rechazar la ruta"
    )


# --- G5: paginación de toda colección (RN-10) ------------------------------


@pytest.mark.parametrize("ruta", COLECCIONES)
async def test_toda_coleccion_paginacion_defaults_y_limites(
    ruta: str,
    cliente_bd,
    url_bd_test,
) -> None:
    await sembrar(url_bd_test)

    por_defecto = await cliente_bd.get(ruta)
    explicito = await cliente_bd.get(ruta, params={"limit": 20, "offset": 0})

    assert por_defecto.status_code == 200
    assert explicito.status_code == 200
    assert por_defecto.json() == explicito.json()

    for parametros in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        respuesta = await cliente_bd.get(ruta, params=parametros)
        assert respuesta.status_code == 422, (
            f"{ruta} con {parametros} devolvió {respuesta.status_code}"
        )


def test_toda_coleccion_paginacion_defaults_declarados_en_openapi() -> None:
    esquema = create_app().openapi()

    for ruta in COLECCIONES:
        plantilla = PLANTILLAS_OPENAPI.get(ruta, ruta)
        parametros = {
            parametro["name"]: parametro
            for parametro in esquema["paths"][plantilla]["get"]["parameters"]
        }
        assert parametros["limit"]["schema"]["default"] == 20, f"{ruta}: limit por defecto"
        assert parametros["offset"]["schema"]["default"] == 0, f"{ruta}: offset por defecto"


# --- G3: RN-12 de extremo a extremo ----------------------------------------


def _verificar_error(respuesta, etiqueta: str, mensaje: str | None = None) -> None:
    cuerpo = respuesta.text
    for prohibido in TEXTO_INTERNO_PROHIBIDO:
        assert prohibido not in cuerpo, (
            f"{etiqueta}: el cuerpo expone '{prohibido}': {cuerpo}"
        )
    if mensaje is not None:
        assert respuesta.json()["detail"] == mensaje, f"{etiqueta}: mensaje propio distinto"


async def test_errores_no_filtran_texto_de_base(
    cliente_bd,
    url_bd_test,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.modules.ventas.router.avisar_comprobante", _noop)
    await sembrar(url_bd_test)

    respuesta = await cliente_bd.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0001-1",
            "titulo": "Duplicado",
            "precio": "10000.00",
            "stock": 1,
            "editorial_id": 1,
            "genero_id": 1,
            "autores": [{"autor_id": 1, "rol": "autor", "orden": 1}],
        },
    )
    assert respuesta.status_code == 409
    _verificar_error(respuesta, "409 ISBN", "El ISBN ya está registrado")

    respuesta = await cliente_bd.post(
        "/clientes/", json={"nombre": "Otro Tomás", "email": "tomas@example.com"}
    )
    assert respuesta.status_code == 409
    _verificar_error(respuesta, "409 email", "El email ya está registrado")

    await cliente_bd.post(
        "/clientes/1/perfil", json={"telefono": "555-0101", "direccion": "Calle 1"}
    )
    respuesta = await cliente_bd.post(
        "/clientes/1/perfil", json={"telefono": "555-0102", "direccion": "Calle 2"}
    )
    assert respuesta.status_code == 409
    _verificar_error(respuesta, "409 perfil", "El cliente ya tiene un perfil")

    respuesta = await cliente_bd.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0200-1",
            "titulo": "Editorial inexistente",
            "precio": "10000.00",
            "stock": 1,
            "editorial_id": 999,
            "genero_id": 1,
            "autores": [{"autor_id": 1, "rol": "autor", "orden": 1}],
        },
    )
    assert respuesta.status_code == 409
    _verificar_error(respuesta, "409 editorial", "La editorial indicada no existe")

    respuesta = await cliente_bd.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0201-8",
            "titulo": "Autor inexistente",
            "precio": "10000.00",
            "stock": 1,
            "editorial_id": 1,
            "genero_id": 1,
            "autores": [{"autor_id": 999, "rol": "autor", "orden": 1}],
        },
    )
    assert respuesta.status_code == 409
    _verificar_error(respuesta, "409 autor", "El autor indicado no existe")

    respuesta = await cliente_bd.post(
        "/ventas/",
        json={"cliente_id": 999, "renglones": [{"libro_id": 1, "cantidad": 1}]},
    )
    assert respuesta.status_code == 409
    _verificar_error(respuesta, "409 cliente", "El cliente indicado no existe")

    respuesta = await cliente_bd.post(
        "/ventas/",
        json={"cliente_id": 2, "renglones": [{"libro_id": 999, "cantidad": 1}]},
    )
    assert respuesta.status_code == 409
    _verificar_error(respuesta, "409 libro", "El libro indicado no existe")

    respuesta = await cliente_bd.get("/libros/999")
    assert respuesta.status_code == 404
    _verificar_error(respuesta, "404 libro", "No encontrado")

    respuesta = await cliente_bd.post("/libros/", json={})
    assert respuesta.status_code == 422
    _verificar_error(respuesta, "422 contrato")


# --- G6: importes como string decimal --------------------------------------


async def test_importes_son_string_decimal(
    cliente_bd,
    url_bd_test,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.modules.ventas.router.avisar_comprobante", _noop)
    await sembrar(url_bd_test)

    listado = await cliente_bd.get("/libros/")
    assert listado.status_code == 200
    for libro in listado.json():
        _verificar_importe(libro["precio"], f"GET /libros/ libro {libro['id']}")

    detalle = await cliente_bd.get("/libros/1")
    assert detalle.status_code == 200
    _verificar_importe(detalle.json()["precio"], "GET /libros/1 precio")

    ventas = await cliente_bd.get("/ventas/")
    assert ventas.status_code == 200
    for venta in ventas.json():
        _verificar_importe(venta["total"], f"GET /ventas/ venta {venta['id']} total")
        for renglon in venta["renglones"]:
            _verificar_importe(
                renglon["precio_unitario"], "GET /ventas/ precio_unitario"
            )
            _verificar_importe(renglon["subtotal"], "GET /ventas/ subtotal")

    detalle_venta = await cliente_bd.get("/ventas/2")
    assert detalle_venta.status_code == 200
    assert detalle_venta.json()["total"] == "77000.00"
    _verificar_importe(detalle_venta.json()["total"], "GET /ventas/2 total")

    ventas_cliente = await cliente_bd.get("/clientes/2/ventas")
    assert ventas_cliente.status_code == 200
    for venta in ventas_cliente.json():
        _verificar_importe(venta["total"], "GET /clientes/2/ventas total")
        for renglon in venta["renglones"]:
            _verificar_importe(
                renglon["precio_unitario"], "GET /clientes/2/ventas precio_unitario"
            )
            _verificar_importe(renglon["subtotal"], "GET /clientes/2/ventas subtotal")

    alta = await cliente_bd.post(
        "/ventas/",
        json={
            "cliente_id": 2,
            "renglones": [
                {"libro_id": 1, "cantidad": 2},
                {"libro_id": 4, "cantidad": 1},
            ],
        },
    )
    assert alta.status_code == 201
    cuerpo = alta.json()
    assert cuerpo["total"] == "77000.00"
    _verificar_importe(cuerpo["total"], "POST /ventas/ total")
    for renglon in cuerpo["renglones"]:
        _verificar_importe(renglon["precio_unitario"], "POST /ventas/ precio_unitario")
        _verificar_importe(renglon["subtotal"], "POST /ventas/ subtotal")
