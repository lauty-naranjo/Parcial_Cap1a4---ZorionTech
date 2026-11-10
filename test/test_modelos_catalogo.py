"""Pruebas de metadata del catálogo: editorial, género y autor (C-02)."""

import sqlalchemy as sa
from sqlmodel import SQLModel


def _tabla(nombre: str) -> sa.Table:
    return SQLModel.metadata.tables[nombre]


def _nombres(tabla: sa.Table, tipo: type) -> set[str]:
    return {c.name for c in tabla.constraints if isinstance(c, tipo)}


def test_editorial_tiene_columnas_exactas():
    tabla = _tabla("editorial")

    assert set(tabla.columns.keys()) == {"id", "nombre", "pais"}


def test_editorial_nombre_es_unico_y_not_null():
    tabla = _tabla("editorial")

    assert tabla.columns["nombre"].nullable is False
    assert tabla.columns["pais"].nullable is False
    assert "uq_editorial_nombre" in _nombres(tabla, sa.UniqueConstraint)


def test_genero_tiene_nombre_unico_y_not_null():
    tabla = _tabla("genero")

    assert set(tabla.columns.keys()) == {"id", "nombre"}
    assert tabla.columns["nombre"].nullable is False
    assert "uq_genero_nombre" in _nombres(tabla, sa.UniqueConstraint)


def test_autor_sin_restricciones_extra():
    tabla = _tabla("autor")

    assert set(tabla.columns.keys()) == {"id", "nombre", "nacionalidad"}
    assert tabla.columns["nombre"].nullable is False
    assert tabla.columns["nacionalidad"].nullable is False
    # La consigna declara "sin restricciones extra": no hay UNIQUE ni CHECK.
    assert _nombres(tabla, sa.UniqueConstraint) == set()
    assert _nombres(tabla, sa.CheckConstraint) == set()


def test_editorial_relacion_bidireccional_con_libros():
    from app.modules.editoriales.models import Editorial

    rel = Editorial.__mapper__.relationships["libros"]

    assert rel.back_populates == "editorial"
    assert rel.mapper.class_.__name__ == "Libro"
    assert rel.lazy == "raise"


def test_genero_relacion_bidireccional_con_libros():
    from app.modules.generos.models import Genero

    rel = Genero.__mapper__.relationships["libros"]

    assert rel.back_populates == "genero"
    assert rel.mapper.class_.__name__ == "Libro"
    assert rel.lazy == "raise"


def test_autor_relacion_bidireccional_con_autorias():
    from app.modules.autores.models import Autor

    rel = Autor.__mapper__.relationships["autorias"]

    assert rel.back_populates == "autor"
    assert rel.mapper.class_.__name__ == "LibroAutor"
    assert rel.lazy == "raise"
