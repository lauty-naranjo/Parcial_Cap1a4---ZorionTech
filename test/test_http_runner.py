"""Pruebas unitarias del parser de archivos ``.http`` (C-10, D4).

El parser es deliberadamente acotado al formato documentado en ``design.md``:
variables ``@nombre = valor``, bloques separados por ``###``, una línea de
request, headers, cuerpo JSON opcional y las dos líneas finales ``# Caso:`` y
``# Esperado:``. Estas pruebas cubren cada regla sin tocar la red ni la base.
"""

from __future__ import annotations

import pytest

from http_runner import BloqueHttp, FormatoHttpError, coincide, leer_archivo


def _escribir(tmp_path, contenido: str):
    ruta = tmp_path / "ejemplo.http"
    ruta.write_text(contenido, encoding="utf-8", newline="\n")
    return ruta


def test_bloque_de_solo_comentarios_se_ignora(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### Caso C-07 — comando, no request
# Arrancar con SQL_ECHO=true y pedir:
#   GET /libros/1 → 2 SELECT
# Caso: C-07
# Esperado: el conteo no cambia con la cardinalidad
""",
    )

    assert leer_archivo(ruta) == []


def test_variables_base_y_propias_se_sustituyen(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000
@libro = 1

### Detalle
GET {{base}}/libros/{{libro}}
# Caso: CRUD
# Esperado: 200 — "Rayuela"
""",
    )

    (bloque,) = leer_archivo(ruta)

    assert isinstance(bloque, BloqueHttp)
    assert bloque.metodo == "GET"
    assert bloque.ruta == "/libros/1"
    assert bloque.caso == "CRUD"
    assert bloque.esperado.codigo == 200
    assert bloque.esperado.fragmentos == ('"Rayuela"',)


def test_headers_y_cuerpo_json_se_extraen(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### Alta
POST {{base}}/editoriales/
Content-Type: application/json

{
  "nombre": "Emecé",
  "pais": "Argentina"
}
# Caso: CRUD
# Esperado: 201 — {"nombre": "Emecé"}
""",
    )

    (bloque,) = leer_archivo(ruta)

    assert bloque.metodo == "POST"
    assert bloque.ruta == "/editoriales/"
    assert bloque.headers == {"Content-Type": "application/json"}
    assert bloque.cuerpo is not None
    assert '"nombre": "Emecé"' in bloque.cuerpo


def test_esperado_sin_fragmento_json(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### PATCH inválido
PATCH {{base}}/libros/999
Content-Type: application/json

{"stock": 1}
# Caso: CRUD
# Esperado: 404 — {"detail": "No encontrado"}
""",
    )

    (bloque,) = leer_archivo(ruta)

    assert bloque.esperado.codigo == 404
    assert bloque.esperado.fragmentos == ('{"detail": "No encontrado"}',)


def test_esperado_con_varios_fragmentos_separados_por_pipe(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### Venta C-06
POST {{base}}/ventas/
Content-Type: application/json

{"cliente_id": 2, "renglones": [{"libro_id": 1, "cantidad": 2}]}
# Caso: C-06
# Esperado: 201 — "precio_unitario": "25000.00" | "total": "50000.00"
""",
    )

    (bloque,) = leer_archivo(ruta)

    assert bloque.esperado.codigo == 201
    assert bloque.esperado.fragmentos == (
        '"precio_unitario": "25000.00"',
        '"total": "50000.00"',
    )


def test_numero_de_linea_apunta_al_request(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### Primero
GET {{base}}/health/live
# Caso: CRUD
# Esperado: 200 — "vivo"

### Segundo
GET {{base}}/health/ready
# Caso: CRUD
# Esperado: 200 — "listo"
""",
    )

    primero, segundo = leer_archivo(ruta)

    assert primero.linea == 4
    assert segundo.linea == 9


def test_normalizacion_ignora_espaciado_del_json() -> None:
    cuerpo = '{"id": 1, "titulo": "Rayuela", "precio": "25000.00"}'

    assert coincide(cuerpo, '{"id": 1, "titulo": "Rayuela"}')
    assert coincide(cuerpo, '"precio": "25000.00"')
    assert not coincide(cuerpo, '"precio": "27000.00"')


def test_normalizacion_de_fragmento_de_texto() -> None:
    cuerpo = '{"estado": "listo", "base": "ok"}'

    assert coincide(cuerpo, "estado")
    assert not coincide(cuerpo, "no_listo")


def test_fragmento_objeto_coincide_con_cualquier_elemento_de_la_lista() -> None:
    cuerpo = '[{"id": 2, "total": "77000.00", "fecha": "2026-11-01T12:00:00Z"}]'

    assert coincide(cuerpo, '{"id": 2, "total": "77000.00"}')
    assert not coincide(cuerpo, '{"id": 3}')


def test_fragmento_clave_valor_anidado_coincide_estructuralmente() -> None:
    cuerpo = '{"cliente": {"id": 2, "nombre": "Tomás Ríos", "email": "tomas@example.com"}}'

    assert coincide(cuerpo, '"cliente": {"id": 2, "nombre": "Tomás Ríos"}')
    assert not coincide(cuerpo, '"cliente": {"id": 3}')


def test_fragmento_lista_vacia_solo_coincide_con_lista_vacia() -> None:
    assert coincide("[]", "[]")
    assert not coincide('[{"id": 1}]', "[]")


def test_bloque_sin_caso_declara_error_con_archivo_y_linea(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### Sin caso
GET {{base}}/health/live
# Esperado: 200 — "vivo"
""",
    )

    with pytest.raises(FormatoHttpError) as excinfo:
        leer_archivo(ruta)

    assert "ejemplo.http" in str(excinfo.value)
    assert "Caso" in str(excinfo.value)


def test_bloque_sin_esperado_declara_error(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### Sin esperado
GET {{base}}/health/live
# Caso: CRUD
""",
    )

    with pytest.raises(FormatoHttpError) as excinfo:
        leer_archivo(ruta)

    assert "Esperado" in str(excinfo.value)


def test_variable_desconocida_declara_error(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### Ruta con variable desconocida
GET {{base}}/libros/{{inexistente}}
# Caso: CRUD
# Esperado: 200 — "Rayuela"
""",
    )

    with pytest.raises(FormatoHttpError) as excinfo:
        leer_archivo(ruta)

    assert "inexistente" in str(excinfo.value)


def test_bloque_sin_metodo_http_se_ignora_aunque_tenga_caso(tmp_path) -> None:
    ruta = _escribir(
        tmp_path,
        """@base = http://localhost:8000

### Nota
# texto suelto
# Caso: C-07
# Esperado: 2 SELECT
""",
    )

    assert leer_archivo(ruta) == []
