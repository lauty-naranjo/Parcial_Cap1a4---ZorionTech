"""Pruebas del comando de datos iniciales ``app.seed`` (C-05).

Todas las pruebas de base usan ``url_bd_test`` (se saltan sin ``DATABASE_URL``)
y las fixtures de ``test/conftest.py``; nunca tocan la base real ni dependen de
``.env`` para su configuración.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro
from app.seed import main, sembrar

RAIZ = Path(__file__).resolve().parents[1]
LINEA_CONTEOS = (
    "Seed aplicado: editorial=1 genero=1 autor=4 libro=4 libro_autor=5 "
    "cliente=2 perfil_cliente=0 venta=1 renglon_venta=2"
)

CONTEOS_ESPERADOS = {
    "editorial": 1,
    "genero": 1,
    "autor": 4,
    "libro": 4,
    "libro_autor": 5,
    "cliente": 2,
    "perfil_cliente": 0,
    "venta": 1,
    "renglon_venta": 2,
}


async def _conteos_reales(motor_bd) -> dict[str, int]:
    """Cuenta filas por tabla directamente en la base sembrada."""
    async with motor_bd.connect() as conexion:
        conteos = {}
        for tabla in CONTEOS_ESPERADOS:
            resultado = await conexion.execute(text(f"SELECT count(*) FROM {tabla}"))
            conteos[tabla] = resultado.scalar_one()
        return conteos


@pytest.mark.integration
async def test_seed_dos_veces_deja_los_mismos_conteos(motor_bd, url_bd_test):
    primera = await sembrar(url_bd_test)
    segunda = await sembrar(url_bd_test)

    assert primera == CONTEOS_ESPERADOS
    assert segunda == CONTEOS_ESPERADOS
    assert await _conteos_reales(motor_bd) == CONTEOS_ESPERADOS


@pytest.mark.integration
async def test_seed_sobre_base_vacia_inserta_el_conjunto_completo(
    motor_bd, url_bd_test
):
    # Triangulación de la doble ejecución: una sola corrida ya deja el conjunto.
    primera = await sembrar(url_bd_test)

    assert primera == CONTEOS_ESPERADOS
    assert await _conteos_reales(motor_bd) == CONTEOS_ESPERADOS


@pytest.mark.integration
async def test_seed_aborta_ante_conflicto_ajeno_a_la_clave_primaria(
    url_bd_test, sesion_bd
):
    # Una editorial con otro id ya usa el nombre del seed: el conflicto de
    # unicidad ajeno a la PK debe abortar la transacción, no silenciarse.
    sesion_bd.add(Editorial(id=7, nombre="Sudamericana", pais="Chile"))
    await sesion_bd.commit()

    with pytest.raises(IntegrityError) as excinfo:
        await sembrar(url_bd_test)
    # El error proviene de la unicidad ajena (`uq_editorial_nombre`), no de una
    # FK rota por haber silenciado la fila de editorial.
    assert "uq_editorial_nombre" in str(excinfo.value)

    # La transacción abortada no deja el resto del conjunto a medias.
    resultado = await sesion_bd.execute(text("SELECT count(*) FROM genero"))
    assert resultado.scalar_one() == 0


@pytest.mark.integration
async def test_seed_no_sobrescribe_datos_modificados(url_bd_test, sesion_bd):
    await sembrar(url_bd_test)

    libro = await sesion_bd.get(Libro, 1)
    libro.stock = 99
    extra = Editorial(nombre="Editorial Extra", pais="Chile")
    sesion_bd.add(extra)
    await sesion_bd.commit()
    id_extra = extra.id

    await sembrar(url_bd_test)

    libro_tras_rerun = await sesion_bd.get(Libro, 1)
    existe_extra = await sesion_bd.get(Editorial, id_extra)
    await sesion_bd.refresh(libro_tras_rerun)
    assert libro_tras_rerun.stock == 99
    assert existe_extra is not None
    assert existe_extra.nombre == "Editorial Extra"


@pytest.mark.integration
async def test_seed_reposiciona_secuencias_para_altas_por_api(
    cliente_bd, url_bd_test
):
    await sembrar(url_bd_test)

    editorial = await cliente_bd.post(
        "/editoriales/", json={"nombre": "Anagrama", "pais": "España"}
    )
    libro = await cliente_bd.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0005-9",
            "titulo": "Nuevo libro",
            "precio": "19000.00",
            "stock": 3,
            "editorial_id": 1,
            "genero_id": 1,
            "autores": [{"autor_id": 1, "rol": "autor", "orden": 1}],
        },
    )
    venta = await cliente_bd.post(
        "/ventas/",
        json={"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 1}]},
    )

    assert editorial.status_code == 201, editorial.text
    assert editorial.json()["id"] == 2
    assert libro.status_code == 201, libro.text
    assert libro.json()["id"] == 5
    assert venta.status_code == 201, venta.text
    assert venta.json()["id"] == 3


@pytest.mark.integration
async def test_catalogo_sembrado_se_lee_por_api(cliente_bd, url_bd_test):
    await sembrar(url_bd_test)

    respuesta = await cliente_bd.get("/libros/")

    assert respuesta.status_code == 200
    libros = respuesta.json()
    assert [libro["id"] for libro in libros] == [1, 2, 3, 4]
    por_id = {libro["id"]: libro for libro in libros}
    assert por_id[1]["titulo"] == "Rayuela"
    assert por_id[1]["precio"] == "25000.00"
    assert por_id[4]["titulo"] == "Respiración artificial"
    assert por_id[4]["precio"] == "27000.00"


@pytest.mark.integration
async def test_venta_sembrada_se_lee_con_total_y_renglones(cliente_bd, url_bd_test):
    await sembrar(url_bd_test)

    respuesta = await cliente_bd.get("/ventas/2")

    assert respuesta.status_code == 200
    venta = respuesta.json()
    assert venta["total"] == "77000.00"
    assert venta["cliente"]["nombre"] == "Tomás Ríos"
    renglones = {r["titulo"]: r for r in venta["renglones"]}
    assert len(renglones) == 2
    assert renglones["Rayuela"]["cantidad"] == 2
    assert renglones["Rayuela"]["subtotal"] == "50000.00"
    assert renglones["Respiración artificial"]["cantidad"] == 1
    assert renglones["Respiración artificial"]["subtotal"] == "27000.00"


def test_main_sin_database_url_devuelve_2_sin_credenciales(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    codigo = main()

    salida = capsys.readouterr()
    assert codigo == 2
    assert "DATABASE_URL" in salida.err
    assert "secreto" not in salida.err
    assert "password" not in salida.err.lower()
    assert "localhost:5432" not in salida.err


@pytest.mark.integration
async def test_sembrar_no_imprime_la_url_ni_la_contrasena(url_bd_test, capsys):
    conteos = await sembrar(url_bd_test)

    salida = capsys.readouterr()
    combinada = salida.out + salida.err
    assert conteos == CONTEOS_ESPERADOS
    assert url_bd_test not in combinada
    contrasena = make_url(url_bd_test).password
    if contrasena:
        assert contrasena not in combinada


def _ejecutar_seed(url: str, sql_echo: str) -> subprocess.CompletedProcess[str]:
    """Corre el comando real ``python -m app.seed`` con ``SQL_ECHO`` explícito."""
    entorno = {
        **os.environ,
        "DATABASE_URL": url,
        "SQL_ECHO": sql_echo,
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, "-m", "app.seed"],
        cwd=RAIZ,
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.mark.integration
async def test_seed_con_sql_echo_activo_no_vuelca_sql(motor_bd, url_bd_test):
    resultado = _ejecutar_seed(url_bd_test, "true")

    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode == 0, resultado.stderr
    assert LINEA_CONTEOS in resultado.stdout
    assert "INSERT INTO" not in salida
    assert "sqlalchemy.engine" not in salida
    assert "Rayuela" not in salida
    assert "tomas@example.com" not in salida


@pytest.mark.integration
async def test_seed_con_sql_echo_inactivo_solo_informa_conteos(motor_bd, url_bd_test):
    resultado = _ejecutar_seed(url_bd_test, "false")

    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == LINEA_CONTEOS
    assert resultado.stderr == ""


def test_importar_app_seed_no_imprime_ni_ejecuta_el_seed(capsys):
    import importlib

    import app.seed as modulo

    importlib.reload(modulo)

    salida = capsys.readouterr()
    assert salida.out == ""
    assert salida.err == ""
