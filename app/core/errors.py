"""Traducción de ``IntegrityError`` a respuestas 409 con mensajes propios.

La base rechaza una unicidad o una clave foránea; este módulo mapea el nombre
de constraint (fijado en C-02) a un mensaje propio sin exponer jamás el texto
de PostgreSQL ni el nombre de la tabla (RN-12).
"""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

MENSAJE_CONFLICTO_GENERICO = "Conflicto con los datos existentes"

# Mapa completo de constraints a mensajes propios. Se reutiliza en C-04 para
# los altas con relaciones (RI-01…RI-05, RN-01/RN-02/RN-09).
CONSTRAINT_MENSAJE: dict[str, str] = {
    "uq_editorial_nombre": "El nombre ya está registrado",
    "uq_genero_nombre": "El nombre ya está registrado",
    "uq_libro_isbn": "El ISBN ya está registrado",
    "uq_cliente_email": "El email ya está registrado",
    "uq_perfil_cliente_cliente_id": "El cliente ya tiene un perfil",
    "fk_libro_editorial_id": "La editorial indicada no existe",
    "fk_libro_genero_id": "El género indicado no existe",
    "fk_libro_autor_autor_id": "El autor indicado no existe",
    "fk_venta_cliente_id": "El cliente indicado no existe",
    "fk_renglon_venta_libro_id": "El libro indicado no existe",
}


def _nombre_constraint(exc: BaseException) -> str | None:
    """Recorre la cadena de excepciones en busca del nombre de constraint.

    Con asyncpg el nombre vive en ``exc.orig.__cause__.constraint_name`` (la
    excepción cruda). Se recorre ``orig``, ``__cause__`` y ``__context__`` para
    cubrir también drivers que exponen ``diag.constraint_name``.
    """
    visitados: set[int] = set()
    pila: list[BaseException] = [exc]

    while pila:
        actual = pila.pop()
        if id(actual) in visitados:
            continue
        visitados.add(id(actual))

        nombre = getattr(actual, "constraint_name", None)
        if nombre:
            return nombre

        diag = getattr(actual, "diag", None)
        nombre = getattr(diag, "constraint_name", None)
        if nombre:
            return nombre

        for atributo in ("orig", "__cause__", "__context__"):
            siguiente = getattr(actual, atributo, None)
            if isinstance(siguiente, BaseException):
                pila.append(siguiente)

    return None


def traducir_integrity_error(exc: IntegrityError) -> HTTPException:
    """Devuelve un ``HTTPException`` 409 con mensaje propio según el constraint.

    Nunca incluye ``str(exc)`` ni el nombre del constraint: si el nombre no está
    en el mapa, se usa el mensaje genérico.
    """
    nombre = _nombre_constraint(exc)
    mensaje = CONSTRAINT_MENSAJE.get(nombre, MENSAJE_CONFLICTO_GENERICO)
    return HTTPException(status_code=409, detail=mensaje)
