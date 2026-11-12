"""Contrato estático de los archivos ``.http`` y de la evidencia (C-10).

Estos tests no tocan la red ni la base: verifican la presencia y el formato de
los ocho ``.http``, que cada request declare caso y resultado esperado, que las
rutas existan en el OpenAPI de la aplicación y que la carpeta ``evidencia/``
siga completa. El replay real vive en ``test_casos_http.py``.
"""

from __future__ import annotations

import codecs
import re
from pathlib import Path

import pytest

from app.main import create_app

RAIZ = Path(__file__).resolve().parent.parent
TEST = RAIZ / "test"
EVIDENCIA = RAIZ / "evidencia"

ARCHIVOS_HTTP = (
    "health.http",
    "editoriales.http",
    "generos.http",
    "autores.http",
    "libros.http",
    "clientes.http",
    "ventas.http",
    "casos-C.http",
)

ARCHIVOS_EVIDENCIA = (
    "C-07-consultas-libro.txt",
    "C-07-consultas-venta.txt",
    "D-01-docker-images.txt",
    "D-02-build-run-ps.txt",
    "D-03-endpoints-publicos.txt",
    "D-04-restart.txt",
    "D-05-sin-database-url.txt",
    "D-06-usuario.txt",
    "D-07-background.txt",
)

CASOS_OBLIGATORIOS = ("C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-08")

PATRON_REQUEST = re.compile(r"^(GET|POST|PATCH|PUT|DELETE)\s+(\S+)\s*$", re.MULTILINE)
PATRON_CASO = re.compile(r"^#\s*Caso:\s*(\S+)\s*$", re.MULTILINE)
PATRON_ESPERADO = re.compile(
    r"^#\s*Esperado:\s*(\d{3})\s*(?:—|-|:)\s*(\S.*)$", re.MULTILINE
)
PATRON_VARIABLE = re.compile(r"^@(\w+)\s*=\s*(.+?)\s*$", re.MULTILINE)
PATRON_URL = re.compile(r"https?://[^\s\"'`]+")

SECRETOS = (
    "DATABASE_URL",
    "postgres",
    "password",
    "Bearer ",
    "46.202.151.202",
)


def _datos(nombre: str) -> bytes:
    ruta = TEST / nombre
    assert ruta.is_file(), f"falta test/{nombre}"
    return ruta.read_bytes()


def _texto(nombre: str) -> str:
    return _datos(nombre).decode("utf-8")


def _bloques(texto: str) -> list[str]:
    """Devuelve el contenido de cada bloque posterior a una línea ``###``."""
    partes = re.split(r"^###.*$", texto, flags=re.MULTILINE)[1:]
    return [parte for parte in partes if parte.strip()]


def _rutas_declaradas(texto: str) -> list[tuple[str, str]]:
    return [(metodo, ruta) for metodo, ruta in PATRON_REQUEST.findall(texto)]


def _coincide_con_openapi(
    metodo: str, ruta: str, operaciones: set[tuple[str, str]]
) -> bool:
    """Compara la ruta declarada con las plantillas del OpenAPI segmento a segmento.

    Un segmento literal solo coincide con el mismo literal; un segmento de la
    plantilla (``{libro_id}``) acepta cualquier valor, incluido ``abc`` de C-01.
    """
    declarada = ruta.replace("{{base}}", "").split("?", 1)[0]
    segmentos = declarada.split("/")
    for metodo_openapi, plantilla in operaciones:
        if metodo_openapi != metodo:
            continue
        segmentos_plantilla = plantilla.split("/")
        if len(segmentos_plantilla) != len(segmentos):
            continue
        if all(
            plantilla_segmento == declarado
            or (
                plantilla_segmento.startswith("{")
                and plantilla_segmento.endswith("}")
            )
            for plantilla_segmento, declarado in zip(segmentos_plantilla, segmentos)
        ):
            return True
    return False


def _rutas_openapi() -> set[tuple[str, str]]:
    esquema = create_app().openapi()
    operaciones: set[tuple[str, str]] = set()
    for ruta, metodos in esquema["paths"].items():
        ruta_normalizada = re.sub(r"\{[^}]+\}", "{param}", ruta)
        for metodo in metodos:
            operaciones.add((metodo.upper(), ruta_normalizada))
    return operaciones


# --- Presencia y formato ---------------------------------------------------


def test_los_ocho_archivos_existen() -> None:
    for nombre in ARCHIVOS_HTTP:
        ruta = TEST / nombre
        assert ruta.is_file(), f"falta test/{nombre}"
        assert ruta.stat().st_size > 0, f"test/{nombre} está vacío"


@pytest.mark.parametrize("nombre", ARCHIVOS_HTTP)
def test_base_es_la_primera_linea_de_contenido(nombre: str) -> None:
    lineas = [linea for linea in _texto(nombre).splitlines() if linea.strip()]

    assert lineas[0] == "@base = http://localhost:8000"


@pytest.mark.parametrize("nombre", ARCHIVOS_HTTP)
def test_usa_separador_de_bloques(nombre: str) -> None:
    texto = _texto(nombre)

    assert re.search(r"^###", texto, re.MULTILINE), "falta el separador ###"
    assert _bloques(texto), f"test/{nombre} no declara bloques"


@pytest.mark.parametrize("nombre", ARCHIVOS_HTTP)
def test_cada_bloque_declara_caso_y_esperado(nombre: str) -> None:
    for indice, bloque in enumerate(_bloques(_texto(nombre)), start=1):
        assert PATRON_CASO.search(bloque), (
            f"test/{nombre}: el bloque {indice} no declara '# Caso:'"
        )
        if PATRON_REQUEST.search(bloque):
            assert PATRON_ESPERADO.search(bloque), (
                f"test/{nombre}: el bloque {indice} no declara "
                "'# Esperado: <código> — <fragmento>'"
            )
        else:
            # Bloque de comando (C-07): no hay código HTTP que esperar.
            assert re.search(r"^#\s*Esperado:", bloque, re.MULTILINE), (
                f"test/{nombre}: el bloque {indice} no declara '# Esperado:'"
            )


@pytest.mark.parametrize("nombre", ARCHIVOS_HTTP)
def test_esperado_declara_codigo_http_y_fragmento(nombre: str) -> None:
    for indice, bloque in enumerate(_bloques(_texto(nombre)), start=1):
        if not PATRON_REQUEST.search(bloque):
            continue
        coincidencia = PATRON_ESPERADO.search(bloque)
        assert coincidencia, f"test/{nombre}: bloque {indice} sin '# Esperado:'"
        codigo = int(coincidencia.group(1))
        assert 100 <= codigo <= 599
        assert coincidencia.group(2).strip()


@pytest.mark.parametrize("nombre", ARCHIVOS_HTTP)
def test_archivo_es_utf8_sin_bom_y_con_saltos_lf(nombre: str) -> None:
    datos = _datos(nombre)

    assert not datos.startswith(codecs.BOM_UTF8), f"test/{nombre} empieza con BOM"
    assert b"\r\n" not in datos, f"test/{nombre} usa CRLF; debe quedar en LF"
    datos.decode("utf-8")  # falla con mensaje claro si no es UTF-8 válido


@pytest.mark.parametrize("nombre", ARCHIVOS_HTTP)
def test_sin_secretos_ni_hosts_del_vps(nombre: str) -> None:
    texto = _texto(nombre)

    for secreto in SECRETOS:
        assert secreto not in texto, f"test/{nombre} contiene '{secreto}'"
    urls = set(PATRON_URL.findall(texto))
    assert urls == {"http://localhost:8000"}, f"test/{nombre} usa URLs no permitidas: {urls}"


@pytest.mark.parametrize("nombre", ARCHIVOS_HTTP)
def test_rutas_declaradas_existen_en_el_openapi(nombre: str) -> None:
    operaciones = _rutas_openapi()
    declaradas = _rutas_declaradas(_texto(nombre))

    assert declaradas, f"test/{nombre} no declara requests"
    for metodo, ruta in declaradas:
        assert _coincide_con_openapi(metodo, ruta, operaciones), (
            f"test/{nombre}: {metodo} {ruta} no existe en app.openapi()['paths']"
        )


# --- Cobertura de los casos C ---------------------------------------------


def test_cobertura_de_casos() -> None:
    casos: set[str] = set()
    for nombre in ARCHIVOS_HTTP:
        casos.update(PATRON_CASO.findall(_texto(nombre)))

    faltantes = set(CASOS_OBLIGATORIOS) - casos
    assert not faltantes, f"faltan casos en los .http: {sorted(faltantes)}"

    casos_c = _texto("casos-C.http")
    assert "C-07" in casos_c
    assert "SQL_ECHO=true" in casos_c
    assert "evidencia/C-07-consultas-libro.txt" in casos_c
    assert "evidencia/C-07-consultas-venta.txt" in casos_c
    assert "GET /libros/{id}" in casos_c
    assert "GET /ventas/{id}" in casos_c


def test_variables_declaradas_se_usan_y_estan_definidas() -> None:
    for nombre in ARCHIVOS_HTTP:
        texto = _texto(nombre)
        declaradas = set(PATRON_VARIABLE.findall(texto))
        assert ("base", "http://localhost:8000") in declaradas
        usadas = set(re.findall(r"\{\{(\w+)\}\}", texto))
        assert usadas <= {clave for clave, _ in declaradas}, (
            f"test/{nombre} usa variables no declaradas: {sorted(usadas)}"
        )


# --- Integridad de la evidencia -------------------------------------------


def test_evidencia_tiene_los_nueve_archivos() -> None:
    for nombre in ARCHIVOS_EVIDENCIA:
        ruta = EVIDENCIA / nombre
        assert ruta.is_file(), f"falta evidencia/{nombre}"
        assert ruta.stat().st_size > 0, f"evidencia/{nombre} está vacío"


def test_evidencia_c07_documenta_select_y_conteo() -> None:
    for nombre in ("C-07-consultas-libro.txt", "C-07-consultas-venta.txt"):
        texto = (EVIDENCIA / nombre).read_text(encoding="utf-8")
        assert "SELECT" in texto
        assert re.search(r"CONTEO:\s*\d+\s+SELECT", texto), (
            f"evidencia/{nombre} no declara el conteo de SELECT"
        )
        assert "SQL_ECHO: true" in texto


def test_evidencia_d_declara_comando_y_criterio() -> None:
    for nombre in ARCHIVOS_EVIDENCIA:
        if not nombre.startswith("D-"):
            continue
        texto = (EVIDENCIA / nombre).read_text(encoding="utf-8")
        assert re.search(r"D-0[1-7]", texto), f"evidencia/{nombre} no identifica su caso"
        en_mayusculas = texto.upper()
        assert "COMANDO" in en_mayusculas, f"evidencia/{nombre} no declara comandos"
        assert (
            "CRITERIO" in en_mayusculas
            or "VERIFICACIÓN" in en_mayusculas
            or "[OK]" in texto
            or "ESTADO: VERIFICADO" in en_mayusculas
        ), f"evidencia/{nombre} no declara criterio o verificación"


def test_evidencia_sin_marcadores_de_plantilla() -> None:
    marcadores = ("<TBD>", "<completar>", "REEMPLAZAR", "{{", "PENDIENTE")
    for nombre in ARCHIVOS_EVIDENCIA:
        texto = (EVIDENCIA / nombre).read_text(encoding="utf-8")
        for marcador in marcadores:
            assert marcador not in texto, (
                f"evidencia/{nombre} conserva el marcador de plantilla '{marcador}'"
            )
        assert not re.search(r"\bTODO\b", texto), (
            f"evidencia/{nombre} conserva el marcador TODO"
        )
