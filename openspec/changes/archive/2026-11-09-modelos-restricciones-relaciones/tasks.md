# Tasks

> TDD estricto en el apply: cada grupo empieza por el test que falla (RED), sigue con la implementaciÃ³n mÃ­nima (GREEN), triangula y refactoriza. Los tests de metadata se escriben contra `SQLModel.metadata`; los de integraciÃ³n (marcados `@pytest.mark.integration`) corren contra la base real si `DATABASE_URL` estÃ¡ definida y se saltean si no.

## 1. CatÃ¡logo base: editorial, gÃ©nero y autor

- [x] 1.1 Escribir `test/test_modelos_catalogo.py` con tests de metadata en RED: existen las tablas `editorial` (id, nombre, pais), `genero` (id, nombre) y `autor` (id, nombre, nacionalidad); `nombre` es NOT NULL en las tres; `editorial.nombre` y `genero.nombre` tienen UNIQUE con nombre `uq_editorial_nombre` y `uq_genero_nombre`. VerificaciÃ³n: `pytest test/test_modelos_catalogo.py` falla (tablas aÃºn no existen).
- [x] 1.2 Implementar `app/modules/editoriales/models.py` (clase `Editorial`), `app/modules/generos/models.py` (`Genero`) y `app/modules/autores/models.py` (`Autor`) con `__tablename__`, columnas exactas, `sa.Column` para NOT NULL y `sa.UniqueConstraint` con nombre, y relaciones `Editorial.libros`/`Genero.libros`/`Autor.autorias` con `Relationship(back_populates=...)` por string. VerificaciÃ³n: los tests de 1.1 pasan (GREEN) y el resto de la suite sigue verde.
- [x] 1.3 Verificar que `import app.main` no abre conexiones ni rompe con las relaciones por string. VerificaciÃ³n: `python -c "import app.main"` termina sin excepciones y sin tocar la base.

## 2. Libro y autorÃ­a

- [x] 2.1 Escribir en `test/test_modelos_libro.py` tests de metadata en RED para `libro` y `libro_autor`: `uq_libro_isbn`; CHECKs `ck_libro_precio_positivo` (`precio > 0`), `ck_libro_stock_no_negativo` (`stock >= 0`); FKs `fk_libro_editorial_id` (NOT NULL) y `fk_libro_genero_id` (nullable); `libro_autor` con PK compuesta `(libro_id, autor_id)`, `ck_libro_autor_rol` con los cuatro valores, `ck_libro_autor_orden` (`orden >= 1`) y FKs `fk_libro_autor_libro_id`/`fk_libro_autor_autor_id`; Ã­ndices en `editorial_id`, `genero_id`, `autor_id` y `titulo`. VerificaciÃ³n: `pytest test/test_modelos_libro.py` falla.
- [x] 2.2 Implementar `app/modules/libros/models.py` con `Libro` y `LibroAutor` (precio `sa.Numeric(10,2)`, FKs nombradas, PK compuesta, checks, `sa.Index("ix_libro_titulo", "titulo")`, relaciones `editorial`/`genero`/`autorias`/`renglones` y `libro`/`autor` con `back_populates`). VerificaciÃ³n: tests de 2.1 en verde.
- [x] 2.3 Agregar test de navegaciÃ³n `libro.autorias[i].autor` con `selectinload(Libro.autorias).joinedload(LibroAutor.autor)` sobre un objeto persistido en sesiÃ³n (sin tocar base real: usar la fÃ¡brica con URL dummy no ejecutada, o el test de integraciÃ³n del grupo 5). VerificaciÃ³n: el test confirma el autor de cada autorÃ­a sin consulta perezosa.

## 3. Cliente y perfil uno a uno

- [x] 3.1 Escribir en `test/test_modelos_cliente.py` tests de metadata en RED para `cliente` y `perfil_cliente`: `uq_cliente_email`; `fk_perfil_cliente_cliente_id`; `uq_perfil_cliente_cliente_id` (UNIQUE sobre la FK, 1:1); y que `Cliente.perfil` es escalar (`uselist=False`, no lista). VerificaciÃ³n: `pytest test/test_modelos_cliente.py` falla.
- [x] 3.2 Implementar `app/modules/clientes/models.py` con `Cliente` y `PerfilCliente` (email UNIQUE nombrado, `cliente_id` FK UNIQUE nombrada e indexada, `Cliente.perfil` con `uselist=False` y `back_populates="cliente"`, `Cliente.ventas` con `back_populates="cliente"`). VerificaciÃ³n: tests de 3.1 en verde.

## 4. Venta y renglones por composiciÃ³n

- [x] 4.1 Escribir en `test/test_modelos_venta.py` tests de metadata en RED para `venta` y `renglon_venta`: `ck_venta_total_no_negativo` (`total >= 0`); `fk_venta_cliente_id`; `ck_renglon_venta_cantidad_positiva` (`cantidad > 0`); `ck_renglon_venta_precio_positivo` (`precio_unitario > 0`); `fk_renglon_venta_venta_id` con `ON DELETE CASCADE`; `fk_renglon_venta_libro_id`; `total` es `Numeric(12,2)` con default `Decimal("0.00")`; `fecha` es `DateTime(timezone=True)`. VerificaciÃ³n: `pytest test/test_modelos_venta.py` falla.
- [x] 4.2 Implementar `app/modules/ventas/models.py` con `Venta` y `RenglonVenta` (`fecha` con `default=utc_now` tz-aware, `total Numeric(12,2)`, `renglones` con `cascade="all, delete-orphan"` y `passive_deletes=True`, `ondelete="CASCADE"`, relaciones `cliente`/`renglones`/`venta`/`libro`). VerificaciÃ³n: tests de 4.1 en verde.
- [x] 4.3 Test de integraciÃ³n (`@pytest.mark.integration`) en `test/test_modelos_venta.py`: persistir una `Venta` con dos `RenglonVenta` por composiciÃ³n, re-leerla con `selectinload(Venta.renglones)` y verificar que al borrar la venta se eliminan los renglones en cascada; usar transacciÃ³n con rollback o datos Ãºnicos + teardown para no dejar basura. VerificaciÃ³n: pasa con `DATABASE_URL` definida y se saltea (skip) sin ella.

## 5. VerificaciÃ³n transversal

- [x] 5.1 Test en `test/test_modelos_transversal.py`: los campos monetarios (`precio`, `total`, `precio_unitario`) entregan `Decimal` (no `float`) al asignar y al leer desde el metadata (`Numeric`). VerificaciÃ³n: pasa.
- [x] 5.2 Test de integraciÃ³n: `SQLModel.metadata.create_all` crea exactamente las nueve tablas en una base vacÃ­a (contar en `SQLModel.metadata.tables` y/o `CREATE TABLE` idempotente). VerificaciÃ³n: pasa con `DATABASE_URL` definida; skip sin ella.
- [x] 5.3 Test: `Venta.fecha` por defecto es tz-aware en UTC (comparar `datetime.now(timezone.utc)` con la instancia reciÃ©n creada). VerificaciÃ³n: pasa.
- [x] 5.4 Correr la suite completa (`pytest -q`) y `openspec validate --strict --change "modelos-restricciones-relaciones"`. VerificaciÃ³n: todos los tests en verde y el change valida sin errores; `import app.main` no abre conexiones.

## Workflow follow-up

- Verificar formalmente el change con `openspec-verify-change` contra proposal, design y specs.
- Archivar el change (`openspec-archive-change`) y sincronizar la delta a `openspec/specs/data-model/spec.md`.
- Marcar C-02 en `[x]` en `CHANGES.md` con su lÃ­nea de cierre.

