"""Validaciones reutilizables para los DTO de entrada."""

from pydantic import BaseModel


def rechazar_nulos_explicitos(modelo: BaseModel, campos: tuple[str, ...]) -> None:
    """Rechaza ``null`` explícito en campos que el contrato declara no nulos.

    ``model_fields_set`` distingue un campo omitido (válido en un PATCH) de uno
    enviado como ``null``: el segundo viola el contrato y debe salir como 422,
    no como un ``IntegrityError`` de ``NOT NULL`` traducido a 409.
    """
    for campo in campos:
        if campo in modelo.model_fields_set and getattr(modelo, campo) is None:
            raise ValueError(f"El campo '{campo}' no admite null")
