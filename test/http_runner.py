"""Parser mínimo de archivos ``.http`` para el replay automático (C-10, D4).

El formato soportado es el que documenta ``design.md`` y comparten VS Code REST
Client y JetBrains HTTP Client:

.. code-block:: http

    @base = http://localhost:8000

    ### Descripción del request
    GET {{base}}/libros/1
    # Caso: CRUD
    # Esperado: 200 — "Rayuela"

El módulo no se recolecta como test (no empieza con ``test_``) y su única
dependencia es la biblioteca estándar. Un archivo mal formado lanza
:class:`FormatoHttpError` con el nombre del archivo y la línea del bloque.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

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

_PATRON_VARIABLE = re.compile(r"^@(\w+)\s*=\s*(.+?)\s*$")
_PATRON_VARIABLE_USADA = re.compile(r"\{\{(\w+)\}\}")
_PATRON_REQUEST = re.compile(r"^([A-Z]+)\s+(\S+)\s*$")
_PATRON_HEADER = re.compile(r"^([A-Za-z0-9-]+):\s*(.+?)\s*$")
_PATRON_CASO = re.compile(r"^#\s*Caso:\s*(\S+)\s*$")
_PATRON_ESPERADO = re.compile(r"^#\s*Esperado:\s*(\d{3})\s*(?:—|-|:)\s*(\S.*)$")
_PATRON_SEPARADOR_FRAGMENTOS = re.compile(r"\s+\|\s+")
_METODOS = ("GET", "POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS")


class FormatoHttpError(ValueError):
    """El archivo ``.http`` no cumple el contrato de bloques."""


@dataclass(frozen=True)
class Esperado:
    """Resultado declarado en ``# Esperado:``."""

    codigo: int
    fragmentos: tuple[str, ...]
    texto: str


@dataclass(frozen=True)
class BloqueHttp:
    """Un request del archivo con su expectativa declarada."""

    archivo: Path
    linea: int
    descripcion: str
    caso: str
    metodo: str
    ruta: str
    headers: dict[str, str]
    cuerpo: str | None
    esperado: Esperado


def _error(archivo: Path, linea: int, mensaje: str) -> FormatoHttpError:
    return FormatoHttpError(f"{archivo.name}:{linea}: {mensaje}")


def _leer_variables(lineas: list[str], archivo: Path) -> dict[str, str]:
    variables: dict[str, str] = {}
    for numero, linea in enumerate(lineas, start=1):
        coincidencia = _PATRON_VARIABLE.match(linea.strip())
        if coincidencia:
            clave, valor = coincidencia.groups()
            if clave in variables and variables[clave] != valor:
                raise _error(archivo, numero, f"la variable @{clave} se redefine")
            variables[clave] = valor
    return variables


def _sustituir(texto: str, variables: dict[str, str], archivo: Path, linea: int) -> str:
    def _reemplazo(coincidencia: re.Match[str]) -> str:
        clave = coincidencia.group(1)
        if clave not in variables:
            raise _error(archivo, linea, f"variable @{clave} no declarada")
        return variables[clave]

    return _PATRON_VARIABLE_USADA.sub(_reemplazo, texto)


def _separar_bloques(lineas: list[str]) -> list[tuple[int, str, list[tuple[int, str]]]]:
    """Devuelve ``(línea_del_separador, descripción, líneas_del_bloque)``."""
    bloques: list[tuple[int, str, list[tuple[int, str]]]] = []
    actual: tuple[int, str, list[tuple[int, str]]] | None = None
    for numero, linea in enumerate(lineas, start=1):
        if linea.lstrip().startswith("###"):
            if actual is not None:
                bloques.append(actual)
            descripcion = linea.lstrip()[3:].strip()
            actual = (numero, descripcion, [])
        elif actual is not None:
            actual[2].append((numero, linea))
    if actual is not None:
        bloques.append(actual)
    return bloques


def _es_comentario(linea: str) -> bool:
    return linea.lstrip().startswith("#")


def _parsear_esperado(texto: str, archivo: Path, linea: int) -> Esperado:
    coincidencia = _PATRON_ESPERADO.match(f"# Esperado: {texto}")
    if coincidencia is None:
        raise _error(
            archivo,
            linea,
            "el '# Esperado:' debe declarar <código> — <fragmento> "
            "(por ejemplo '409 — {\"detail\": \"...\"}')",
        )
    codigo = int(coincidencia.group(1))
    resto = coincidencia.group(2).strip()
    fragmentos = tuple(
        fragmento.strip()
        for fragmento in _PATRON_SEPARADOR_FRAGMENTOS.split(resto)
        if fragmento.strip()
    )
    if not fragmentos:
        raise _error(archivo, linea, "el '# Esperado:' no declara ningún fragmento")
    return Esperado(codigo=codigo, fragmentos=fragmentos, texto=resto)


def _parsear_bloque(
    archivo: Path,
    separador: int,
    descripcion: str,
    lineas: list[tuple[int, str]],
    variables: dict[str, str],
) -> BloqueHttp | None:
    indice_request: int | None = None
    metodo = ""
    ruta = ""
    for indice, (numero, linea) in enumerate(lineas):
        desnuda = linea.strip()
        if not desnuda or _es_comentario(desnuda):
            continue
        partes = desnuda.split(maxsplit=1)
        if partes[0] not in _METODOS or len(partes) != 2:
            raise _error(archivo, numero, f"se esperaba '<MÉTODO> <ruta>', no '{desnuda}'")
        indice_request = indice
        metodo, ruta = partes
        break

    if indice_request is None:
        # Bloque de solo comentarios (C-07 es un comando, no un request).
        return None

    numero_request = lineas[indice_request][0]
    ruta = _sustituir(ruta, variables, archivo, numero_request)
    if ruta.startswith(("http://", "https://")):
        partes = urlsplit(ruta)
        ruta = partes.path + (f"?{partes.query}" if partes.query else "")
    if not ruta.startswith("/"):
        raise _error(archivo, numero_request, f"la ruta '{ruta}' debe empezar con '/'")

    caso: str | None = None
    esperado: Esperado | None = None
    headers: dict[str, str] = {}
    cuerpo_lineas: list[str] = []
    en_cuerpo = False

    for numero, linea in lineas[indice_request + 1 :]:
        desnuda = linea.strip()
        if _es_comentario(desnuda):
            coincidencia_caso = _PATRON_CASO.match(desnuda)
            if coincidencia_caso:
                if caso is not None:
                    raise _error(archivo, numero, "'# Caso:' repetido en el bloque")
                caso = coincidencia_caso.group(1)
                continue
            if desnuda.lower().startswith("# esperado:"):
                if esperado is not None:
                    raise _error(archivo, numero, "'# Esperado:' repetido en el bloque")
                esperado = _parsear_esperado(desnuda.split(":", 1)[1].strip(), archivo, numero)
                continue
            continue

        if en_cuerpo:
            cuerpo_lineas.append(linea)
            continue

        if not desnuda:
            en_cuerpo = True
            continue

        coincidencia_header = _PATRON_HEADER.match(desnuda)
        if coincidencia_header is None:
            raise _error(
                archivo,
                numero,
                f"línea inesperada antes del cuerpo: '{desnuda}'",
            )
        clave, valor = coincidencia_header.groups()
        headers[clave] = _sustituir(valor, variables, archivo, numero)

    if caso is None:
        raise _error(
            archivo,
            numero_request,
            "el bloque no declara '# Caso:' (C-0N, D-xx o CRUD)",
        )
    if esperado is None:
        raise _error(
            archivo,
            numero_request,
            "el bloque no declara '# Esperado: <código> — <fragmento>'",
        )

    cuerpo = "\n".join(cuerpo_lineas).strip() or None

    return BloqueHttp(
        archivo=archivo,
        linea=numero_request,
        descripcion=descripcion,
        caso=caso,
        metodo=metodo,
        ruta=ruta,
        headers=headers,
        cuerpo=cuerpo,
        esperado=esperado,
    )


def leer_archivo(ruta: str | Path) -> list[BloqueHttp]:
    """Lee un archivo ``.http`` y devuelve sus bloques ejecutables.

    Los bloques sin línea de request (por ejemplo el comando C-07) se omiten.
    Las variables ``@nombre = valor`` se sustituyen en rutas y headers.
    """
    archivo = Path(ruta)
    if not archivo.is_file():
        raise FormatoHttpError(f"{archivo.name}: no existe")
    texto = archivo.read_text(encoding="utf-8")
    lineas = texto.splitlines()
    variables = _leer_variables(lineas, archivo)

    bloques: list[BloqueHttp] = []
    for separador, descripcion, lineas_bloque in _separar_bloques(lineas):
        bloque = _parsear_bloque(
            archivo, separador, descripcion, lineas_bloque, variables
        )
        if bloque is not None:
            bloques.append(bloque)
    return bloques


def _compactar(texto: str) -> str:
    """Quita espacios fuera de cadenas para comparar JSON sin depender del formato."""
    resultado: list[str] = []
    en_cadena = False
    escape = False
    for caracter in texto:
        if en_cadena:
            resultado.append(caracter)
            if escape:
                escape = False
            elif caracter == "\\":
                escape = True
            elif caracter == '"':
                en_cadena = False
        elif caracter == '"':
            en_cadena = True
            resultado.append(caracter)
        elif caracter.isspace():
            continue
        else:
            resultado.append(caracter)
    return "".join(resultado)


def _json(texto: str) -> object | None:
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, ValueError):
        return None


def _subconjunto(real: object, esperado: object) -> bool:
    if isinstance(esperado, dict):
        if not isinstance(real, dict):
            return False
        return all(
            clave in real and _subconjunto(real[clave], valor)
            for clave, valor in esperado.items()
        )
    if isinstance(esperado, list):
        if not isinstance(real, list) or len(real) != len(esperado):
            return False
        return all(_subconjunto(a, b) for a, b in zip(real, esperado))
    return real == esperado


def _normalizar(texto: str) -> str:
    desnudo = texto.strip()
    if desnudo.startswith(("{", "[", '"')):
        return _compactar(desnudo)
    return " ".join(desnudo.split())


def coincide(cuerpo: str, fragmento: str) -> bool:
    """Indica si ``fragmento`` aparece en ``cuerpo`` sin depender del espaciado.

    Si el fragmento es un objeto JSON, se compara como subconjunto estructural
    contra el cuerpo (o contra cualquier elemento, si el cuerpo es una lista).
    También se acepta la forma ``"clave": <valor JSON>`` como fragmento parcial.
    En cualquier otro caso se compara el texto normalizado.
    """
    cuerpo_json = _json(cuerpo)
    fragmento_json = _json(fragmento)

    if isinstance(fragmento_json, dict):
        if isinstance(cuerpo_json, dict):
            return _subconjunto(cuerpo_json, fragmento_json)
        if isinstance(cuerpo_json, list):
            return any(_subconjunto(item, fragmento_json) for item in cuerpo_json)

    if isinstance(fragmento_json, list) and isinstance(cuerpo_json, list):
        return cuerpo_json == fragmento_json

    envuelto = _json("{" + fragmento + "}")
    if isinstance(envuelto, dict):
        if isinstance(cuerpo_json, dict) and _subconjunto(cuerpo_json, envuelto):
            return True
        if isinstance(cuerpo_json, list) and any(
            _subconjunto(item, envuelto) for item in cuerpo_json
        ):
            return True

    return _normalizar(fragmento) in _normalizar(cuerpo)
