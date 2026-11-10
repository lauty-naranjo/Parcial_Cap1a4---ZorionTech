"""Pruebas del mapeo de ``IntegrityError`` a mensajes propios (RN-12)."""

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.errors import CONSTRAINT_MENSAJE, traducir_integrity_error


def _error_asyncpg_con_constraint(nombre: str) -> IntegrityError:
    """Arma un ``IntegrityError`` como lo produce SQLAlchemy con asyncpg.

    La cadena real es ``IntegrityError.orig`` (wrapper de SQLAlchemy) →
    ``.orig.__cause__`` (excepción cruda de asyncpg con ``constraint_name``).
    """
    cruda = type("UniqueViolationError", (Exception,), {"constraint_name": nombre})()
    envuelta = type("AsyncpgUniqueViolationError", (Exception,), {})()
    envuelta.__cause__ = cruda
    return IntegrityError("INSERT", {}, envuelta)


def test_mapa_de_constraints_con_mensajes_propios():
    assert CONSTRAINT_MENSAJE["uq_libro_isbn"] == "El ISBN ya está registrado"
    assert CONSTRAINT_MENSAJE["uq_cliente_email"] == "El email ya está registrado"
    assert CONSTRAINT_MENSAJE["uq_perfil_cliente_cliente_id"] == "El cliente ya tiene un perfil"
    assert CONSTRAINT_MENSAJE["fk_libro_editorial_id"] == "La editorial indicada no existe"


@pytest.mark.parametrize(
    ("constraint", "mensaje"),
    [
        ("uq_libro_isbn", "El ISBN ya está registrado"),
        ("uq_cliente_email", "El email ya está registrado"),
        ("uq_perfil_cliente_cliente_id", "El cliente ya tiene un perfil"),
        ("fk_libro_editorial_id", "La editorial indicada no existe"),
        ("uq_editorial_nombre", "El nombre ya está registrado"),
        ("uq_genero_nombre", "El nombre ya está registrado"),
        ("fk_libro_genero_id", "El género indicado no existe"),
    ],
)
def test_traduce_por_nombre_de_constraint(constraint, mensaje):
    error = _error_asyncpg_con_constraint(constraint)

    resultado = traducir_integrity_error(error)

    assert isinstance(resultado, HTTPException)
    assert resultado.status_code == 409
    assert resultado.detail == mensaje


def test_constraint_desconocido_devuelve_409_generico_sin_texto_interno():
    error = _error_asyncpg_con_constraint("ck_inventada")

    resultado = traducir_integrity_error(error)

    assert resultado.status_code == 409
    assert resultado.detail == "Conflicto con los datos existentes"
    assert "ck_inventada" not in resultado.detail
    assert str(error) not in resultado.detail


def test_error_sin_constraint_devuelve_409_generico():
    error = IntegrityError("INSERT", {}, Exception("detalle interno de la base"))

    resultado = traducir_integrity_error(error)

    assert resultado.status_code == 409
    assert resultado.detail == "Conflicto con los datos existentes"
    assert "detalle interno" not in resultado.detail
