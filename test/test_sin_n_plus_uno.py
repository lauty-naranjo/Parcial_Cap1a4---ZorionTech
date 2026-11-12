"""Pruebas de N+1: número fijo de consultas por endpoint relacional (C-06, IN-04).

Cada caso compara el conteo de ``SELECT`` de un detalle (libro o venta) con 1
relación frente a 3 relaciones, y de los listados con una página de 1 frente a
3 filas. El criterio operativo es que el número **no crezca**; el número real se
registra en ``evidencia/C-07-consultas-*.txt``.
"""

import re
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta
from contador_consultas import contador_consultas


def _solo_select(consulta: str) -> bool:
    return consulta.lstrip().upper().startswith("SELECT")


async def _sembrar_libro(sesion_bd, *, n_autores: int) -> int:
    """Siembra un libro con ``n_autores`` autores y devuelve su id."""
    editorial = Editorial(nombre=f"Ed {n_autores}", pais="Argentina")
    sesion_bd.add(editorial)
    await sesion_bd.flush()

    libro = Libro(
        isbn=f"978-{n_autores}",
        titulo=f"Libro {n_autores}",
        precio=Decimal("1000.00"),
        stock=5,
        editorial_id=editorial.id,
    )
    sesion_bd.add(libro)
    await sesion_bd.flush()

    for i in range(n_autores):
        autor = Autor(nombre=f"Autor {n_autores}-{i}", nacionalidad="Argentina")
        sesion_bd.add(autor)
        await sesion_bd.flush()
        sesion_bd.add(
            LibroAutor(libro_id=libro.id, autor_id=autor.id, rol="autor", orden=i + 1)
        )
    await sesion_bd.commit()
    return libro.id


async def _sembrar_ventas(
    sesion_bd,
    *,
    n_ventas: int,
    n_renglones: int,
    sufijo: str = "a",
    cliente_id: int | None = None,
) -> list[int]:
    """Siembra ``n_ventas`` ventas con ``n_renglones`` renglones cada una.

    Si ``cliente_id`` se pasa, reutiliza ese cliente (para acumular ventas del
    mismo cliente); si no, crea un cliente nuevo con email único por ``sufijo``.
    """
    editorial = Editorial(nombre=f"Sudamericana {sufijo}", pais="Argentina")
    sesion_bd.add(editorial)
    if cliente_id is None:
        cliente = Cliente(
            nombre=f"Tomás Ríos {sufijo}", email=f"tomas-{sufijo}@example.com"
        )
        sesion_bd.add(cliente)
    else:
        cliente = None
    await sesion_bd.flush()

    if cliente_id is None:
        cliente_id = cliente.id

    total_libros = n_ventas * n_renglones
    libros = []
    for i in range(1, total_libros + 1):
        libro = Libro(
            isbn=f"978-{sufijo}-{i}",
            titulo=f"Libro {sufijo} {i}",
            precio=Decimal("1000.00"),
            stock=5,
            editorial_id=editorial.id,
        )
        sesion_bd.add(libro)
        libros.append(libro)
    await sesion_bd.flush()

    ventas = []
    for v in range(n_ventas):
        venta = Venta(cliente_id=cliente_id, total=Decimal("0.00"))
        sesion_bd.add(venta)
        await sesion_bd.flush()
        total = Decimal("0.00")
        for r in range(n_renglones):
            libro = libros[v * n_renglones + r]
            sesion_bd.add(
                RenglonVenta(
                    venta_id=venta.id,
                    libro_id=libro.id,
                    cantidad=1,
                    precio_unitario=libro.precio,
                )
            )
            total += libro.precio
        venta.total = total
        ventas.append(venta)
    await sesion_bd.commit()
    return [v.id for v in ventas]


@pytest.mark.parametrize(
    "entidad,url_una,url_tres",
    [
        pytest.param(
            "libro",
            lambda ids: f"/libros/{ids['uno']}",
            lambda ids: f"/libros/{ids['tres']}",
            id="detalle-libro",
        ),
        pytest.param(
            "venta",
            lambda ids: f"/ventas/{ids['uno'][0]}",
            lambda ids: f"/ventas/{ids['tres'][0]}",
            id="detalle-venta",
        ),
    ],
)
async def test_detalle_mismo_conteo_1_vs_3(
    cliente_bd, sesion_bd, motor_bd, entidad, url_una, url_tres
):
    """El detalle emite el mismo número de SELECT con 1 y con 3 relaciones."""
    if entidad == "libro":
        uno = await _sembrar_libro(sesion_bd, n_autores=1)
        tres = await _sembrar_libro(sesion_bd, n_autores=3)
        ids = {"uno": uno, "tres": tres}
    else:
        ids = {
            "uno": await _sembrar_ventas(sesion_bd, n_ventas=1, n_renglones=1, sufijo="u"),
            "tres": await _sembrar_ventas(sesion_bd, n_ventas=1, n_renglones=3, sufijo="t"),
        }

    with contador_consultas(motor_bd) as cuenta_una:
        respuesta_una = await cliente_bd.get(url_una(ids))
    with contador_consultas(motor_bd) as cuenta_tres:
        respuesta_tres = await cliente_bd.get(url_tres(ids))

    assert respuesta_una.status_code == 200
    assert respuesta_tres.status_code == 200

    select_una = [s for s in cuenta_una.consultas if _solo_select(s)]
    select_tres = [s for s in cuenta_tres.consultas if _solo_select(s)]
    assert len(select_una) == len(select_tres)
    assert len(select_una) > 0


@pytest.mark.parametrize(
    "url_una,url_tres",
    [
        pytest.param(
            lambda _: "/ventas/",
            lambda _: "/ventas/",
            id="listado-ventas",
        ),
    ],
)
async def test_listado_ventas_mismo_conteo_1_vs_3(
    cliente_bd, sesion_bd, motor_bd, url_una, url_tres
):
    """Una página de varias ventas no dispara una consulta por fila."""
    await _sembrar_ventas(sesion_bd, n_ventas=1, n_renglones=1, sufijo="u")
    with contador_consultas(motor_bd) as cuenta_una:
        respuesta_una = await cliente_bd.get(url_una(None))

    await _sembrar_ventas(sesion_bd, n_ventas=3, n_renglones=2, sufijo="t")
    with contador_consultas(motor_bd) as cuenta_tres:
        respuesta_tres = await cliente_bd.get(url_tres(None))

    assert respuesta_una.status_code == 200
    assert respuesta_tres.status_code == 200

    select_una = [s for s in cuenta_una.consultas if _solo_select(s)]
    select_tres = [s for s in cuenta_tres.consultas if _solo_select(s)]
    assert len(select_una) == len(select_tres)
    assert len(select_una) > 0


async def test_ventas_de_cliente_mismo_conteo_1_vs_3(
    cliente_bd, sesion_bd, motor_bd
):
    """El listado de ventas de un cliente no crece con la cantidad de ventas."""
    await _sembrar_ventas(sesion_bd, n_ventas=1, n_renglones=1, sufijo="u")

    venta = (await sesion_bd.execute(select(Venta).limit(1))).scalar_one()
    cliente_id = venta.cliente_id

    with contador_consultas(motor_bd) as cuenta_una:
        respuesta_una = await cliente_bd.get(f"/clientes/{cliente_id}/ventas")

    await _sembrar_ventas(
        sesion_bd, n_ventas=3, n_renglones=2, sufijo="t", cliente_id=cliente_id
    )
    with contador_consultas(motor_bd) as cuenta_tres:
        respuesta_tres = await cliente_bd.get(f"/clientes/{cliente_id}/ventas")

    assert respuesta_una.status_code == 200
    assert respuesta_tres.status_code == 200

    select_una = [s for s in cuenta_una.consultas if _solo_select(s)]
    select_tres = [s for s in cuenta_tres.consultas if _solo_select(s)]
    assert len(select_una) == len(select_tres)
    assert len(select_una) > 0
    assert len(respuesta_una.json()) == 1
    assert len(respuesta_tres.json()) == 4


_PATRON_DECIMAL = re.compile(r"\d+\.\d{2}")
_PATRON_FECHA_UTC = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z"
)


@pytest.mark.integration
async def test_ventas_lectura_contrato_y_conteo_fijo(cliente_bd, sesion_bd, motor_bd):
    """Con base real, ``GET /ventas/`` y ``GET /ventas/{id}`` cumplen el contrato.

    Verifica el ``VentaRead`` completo (``total`` string decimal, ``fecha`` UTC
    con microsegundos y sufijo ``Z``, renglones con ``titulo``/``subtotal``) y
    que el número de ``SELECT`` no cambia con la cantidad de renglones ni con la
    cantidad de ventas de la página (IN-04).
    """
    venta_uno = (
        await _sembrar_ventas(sesion_bd, n_ventas=1, n_renglones=1, sufijo="int-u")
    )[0]
    venta_tres = (
        await _sembrar_ventas(sesion_bd, n_ventas=1, n_renglones=3, sufijo="int-t")
    )[0]

    with contador_consultas(motor_bd) as cuenta_uno:
        detalle_uno = await cliente_bd.get(f"/ventas/{venta_uno}")
    with contador_consultas(motor_bd) as cuenta_tres:
        detalle_tres = await cliente_bd.get(f"/ventas/{venta_tres}")

    assert detalle_uno.status_code == 200
    assert detalle_tres.status_code == 200

    cuerpo_uno = detalle_uno.json()
    cuerpo_tres = detalle_tres.json()

    assert set(cuerpo_uno) == {"id", "fecha", "total", "cliente", "renglones"}
    assert _PATRON_DECIMAL.fullmatch(cuerpo_uno["total"])
    assert _PATRON_FECHA_UTC.fullmatch(cuerpo_uno["fecha"])
    assert cuerpo_uno["cliente"]["email"] == "tomas-int-u@example.com"
    assert len(cuerpo_uno["renglones"]) == 1
    assert len(cuerpo_tres["renglones"]) == 3
    for renglon in cuerpo_tres["renglones"]:
        assert renglon["titulo"].startswith("Libro int-t")
        assert _PATRON_DECIMAL.fullmatch(renglon["subtotal"])

    selects_uno = [s for s in cuenta_uno.consultas if _solo_select(s)]
    selects_tres = [s for s in cuenta_tres.consultas if _solo_select(s)]
    assert len(selects_uno) == len(selects_tres)
    assert len(selects_uno) > 0

    # Listado: mismo contrato y conteo estable al crecer la página.
    with contador_consultas(motor_bd) as cuenta_listado_dos:
        listado_dos = await cliente_bd.get("/ventas/?limit=100")
    await _sembrar_ventas(sesion_bd, n_ventas=3, n_renglones=2, sufijo="int-l")
    with contador_consultas(motor_bd) as cuenta_listado_cinco:
        listado_cinco = await cliente_bd.get("/ventas/?limit=100")

    assert listado_dos.status_code == 200
    assert listado_cinco.status_code == 200
    assert len(listado_dos.json()) == 2
    assert len(listado_cinco.json()) == 5
    for venta in listado_cinco.json():
        assert _PATRON_DECIMAL.fullmatch(venta["total"])
        assert _PATRON_FECHA_UTC.fullmatch(venta["fecha"])
        assert venta["renglones"]

    selects_listado_dos = [s for s in cuenta_listado_dos.consultas if _solo_select(s)]
    selects_listado_cinco = [
        s for s in cuenta_listado_cinco.consultas if _solo_select(s)
    ]
    assert len(selects_listado_dos) == len(selects_listado_cinco)
    assert len(selects_listado_dos) > 0
