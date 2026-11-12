"""Validaciones reutilizables de los DTO de entrada.

Un PATCH parcial distingue dos situaciones que Pydantic no separa solo con el
tipo: el campo **omitido** (válido: no se toca) y el campo enviado como
``null`` explícito. Si la columna es ``NOT NULL``, ese ``null`` llega hasta la
base y su ``IntegrityError`` se traduce a 409, cuando en realidad es un cuerpo
que no cumple el contrato y debe responder 422.
"""

from pydantic import BaseModel


def rechazar_nulos_explicitos(modelo: BaseModel, campos: tuple[str, ...]) -> None:
    """Rechaza ``null`` explícito en los campos que no admiten nulos.

    ``model_fields_set`` contiene únicamente los campos enviados en el cuerpo,
    por lo que un campo omitido nunca se rechaza. Se invoca desde un
    ``@model_validator(mode="after")`` para que el error salga por la validación
    de FastAPI (422) antes de tocar la base de datos.
    """
    for campo in campos:
        if campo in modelo.model_fields_set and getattr(modelo, campo) is None:
            raise ValueError(f"El campo '{campo}' no admite null")
