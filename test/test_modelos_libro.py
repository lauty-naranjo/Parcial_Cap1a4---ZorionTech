"""Pruebas de metadata de libro y autoría (C-02)."""

import sqlalchemy as sa
from sqlmodel import SQLModel


def _tabla(nombre: str) -> sa.Table:
    return SQLModel.metadata.tables[nombre]


def _nombres(tabla: sa.Table, tipo: type) -> set[str]:
    return {c.name for c in tabla.constraints if isinstance(c, tipo)}


def test_libro_tiene_columnas_exactas():
    tabla = _tabla("libro")

    assert set(tabla.columns.keys()) == {
        "id",
        "isbn",
        "titulo",
        "precio",
        "stock",
        "editorial_id",
        "genero_id",
    }


def test_libro_isbn_unico_y_not_null():
    tabla = _tabla("libro")

    assert tabla.columns["isbn"].nullable is False
    assert "uq_libro_isbn" in _nombres(tabla, sa.UniqueConstraint)


def test_libro_checks_de_precio_y_stock():
    tabla = _tabla("libro")
    checks = _nombres(tabla, sa.CheckConstraint)

    assert "ck_libro_precio_positivo" in checks
    assert "ck_libro_stock_no_negativo" in checks


def test_libro_precio_es_numeric_10_2():
    tabla = _tabla("libro")
    columna = tabla.columns["precio"].type

    assert isinstance(columna, sa.Numeric)
    assert columna.precision == 10
    assert columna.scale == 2


def test_libro_fks_editorial_y_genero():
    tabla = _tabla("libro")
    fks = _nombres(tabla, sa.ForeignKeyConstraint)

    assert "fk_libro_editorial_id" in fks
    assert "fk_libro_genero_id" in fks
    assert tabla.columns["editorial_id"].nullable is False
    assert tabla.columns["genero_id"].nullable is True


def test_libro_tiene_indices_en_fks_y_titulo():
    tabla = _tabla("libro")
    indexadas = {col.name for idx in tabla.indexes for col in idx.columns}

    assert "editorial_id" in indexadas
    assert "genero_id" in indexadas
    assert "titulo" in indexadas


def test_libro_autor_pk_compuesta():
    tabla = _tabla("libro_autor")

    pk = tabla.primary_key.columns
    assert {col.name for col in pk} == {"libro_id", "autor_id"}


def test_libro_autor_checks_de_rol_y_orden():
    tabla = _tabla("libro_autor")
    checks = _nombres(tabla, sa.CheckConstraint)

    assert "ck_libro_autor_rol" in checks
    assert "ck_libro_autor_orden" in checks


def test_libro_autor_fks_libro_y_autor():
    tabla = _tabla("libro_autor")
    fks = _nombres(tabla, sa.ForeignKeyConstraint)

    assert "fk_libro_autor_libro_id" in fks
    assert "fk_libro_autor_autor_id" in fks


def test_navegacion_libro_autorias_autor():
    from app.modules.autores.models import Autor
    from app.modules.libros.models import Libro, LibroAutor

    autorias = Libro.__mapper__.relationships["autorias"]
    assert autorias.back_populates == "libro"
    assert autorias.mapper.class_.__name__ == "LibroAutor"

    autor = LibroAutor.__mapper__.relationships["autor"]
    assert autor.back_populates == "autorias"
    assert autor.mapper.class_ is Autor
