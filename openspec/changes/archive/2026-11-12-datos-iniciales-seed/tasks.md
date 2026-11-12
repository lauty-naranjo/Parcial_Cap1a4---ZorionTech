# Tasks

> TDD estricto en el apply: el grupo 1 escribe los tests que fallan (RED); el grupo 2 implementa hasta ponerlos en verde (GREEN). Todos los tests de base usan `url_bd_test` (se saltan sin `DATABASE_URL`) y las fixtures existentes de `test/conftest.py`; nunca tocan la base real ni dependen de `.env`.

## 1. Tests del seed (RED)

- [x] 1.1 Crear `test/test_seed.py` con `@pytest.mark.integration` y la prueba de doble ejecución: con `motor_bd` para partir de un esquema limpio, `await sembrar(url_bd_test)` dos veces y comparar los conteos de las nueve tablas con `editorial=1`, `genero=1`, `autor=4`, `libro=4`, `libro_autor=5`, `cliente=2`, `perfil_cliente=0`, `venta=1`, `renglon_venta=2`. Verificación: `pytest test/test_seed.py -q` falla porque `app.seed` todavía no existe.
- [x] 1.2 Agregar la prueba de no sobrescritura: sembrar, cambiar `libro 1.stock` a 99 y crear una editorial extra desde una sesión, volver a sembrar y comprobar que el stock sigue en 99 y que la editorial extra permanece. Verificación: el test falla en RED y protege la idempotencia sin pisar datos.
- [x] 1.3 Agregar la prueba de secuencias: sembrar y luego `POST /editoriales/`, `POST /libros/` y `POST /ventas/` con datos válidos; esperar 201 e ids 2, 5 y 3 respectivamente, sin `duplicate key`. Verificación: el test falla en RED y será la prueba explícita del `setval`.
- [x] 1.4 Agregar las pruebas de catálogo y venta de ejemplo: `GET /libros/` devuelve los cuatro libros con «Rayuela» a `"25000.00"` y «Respiración artificial» a `"27000.00"`; `GET /ventas/2` devuelve `total == "77000.00"` y dos renglones con cantidades 2 y 1 y subtotales `50000.00` y `27000.00`. Verificación: ambos tests fallan en RED.
- [x] 1.5 Agregar la prueba de configuración y salida: con `monkeypatch.delenv("DATABASE_URL")`, `main()` devuelve 2, el mensaje menciona `DATABASE_URL` y no contiene credenciales; sembrar correctamente no imprime la URL ni la contraseña. Verificación: el test falla en RED y cubre la regla D.11.

## 2. Implementación de `app/seed.py`

- [x] 2.1 Crear `app/seed.py` con los imports explícitos de los seis módulos de `models`, la función `async def sembrar(url: str | None = None) -> dict[str, int]`, el uso de `get_settings()` cuando `url` es `None`, `build_engine`/`build_session_factory`, `create_all` antes de la sesión y `await engine.dispose()` en `finally`. Verificación: `python -c "import app.seed"` no ejecuta el seed ni imprime nada, y el test 1.1 deja de fallar por importación.
- [x] 2.2 Definir las constantes del conjunto inicial con los ids y valores de `design.md` §2: editorial 1, género 1, autores 1–4, libros 1–4, cinco autorías, clientes 1–2, venta 2 y renglones 1–2; usar `Decimal` para `precio`, `total` y `precio_unitario`, y `datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)` para la fecha. Verificación: los tests 1.1 y 1.4 quedan en verde y los valores coinciden con la tabla del diseño.
- [x] 2.3 Implementar las inserciones multfila con `sqlalchemy.dialects.postgresql.insert(...).values([...]).on_conflict_do_nothing(...)`, apuntando a la PK simple de cada tabla y a `["libro_id", "autor_id"]` en `libro_autor`, en orden de dependencias (editorial → género → autor → libro → libro_autor → cliente → venta → renglon_venta). Verificación: los tests 1.1 y 1.2 quedan en verde; un rerun no duplica ni pisa.
- [x] 2.4 Implementar el reposicionamiento de secuencias con `setval(pg_get_serial_sequence('<tabla>', 'id'), COALESCE((SELECT MAX(id) FROM <tabla>), 1), (SELECT MAX(id) FROM <tabla>) IS NOT NULL)` para `autor`, `editorial`, `genero`, `libro`, `cliente`, `perfil_cliente`, `venta` y `renglon_venta`, usando una tupla constante de nombres y omitiendo `libro_autor`. Verificación: el test 1.3 queda en verde; `POST /libros/` y `POST /ventas/` posteriores no fallan por PK duplicada.
- [x] 2.5 Implementar el conteo posterior al `commit` y `main()`: `asyncio.run(sembrar())` solo en `main`, salida de una línea con los conteos, errores a `stderr` con código 2 para `ConfigurationError` y código 1 para `IntegrityError`/`SQLAlchemyError`, sin trazas ni `str(exc)` de la base. Verificación: los tests 1.1 a 1.5 quedan en verde y `python -m app.seed` con `DATABASE_URL` válida termina con código 0.
- [x] 2.6 Confirmar que el seed no contiene credenciales ni imprime la cadena de conexión: revisar que la URL solo se lea de `get_settings()`/parámetro y que la salida solo tenga conteos. Verificación: `rg -n "postgresql|password|DATABASE_URL" app/seed.py` no muestra cadenas de conexión literales ni credenciales; el test 1.5 pasa.

## 3. Documentación del comando

- [x] 3.1 Agregar la sección «Datos iniciales (seed)» en `README.md` con `.venv\Scripts\python.exe -m app.seed`, `python -m app.seed` y `docker exec libreria python -m app.seed`; indicar que requiere `DATABASE_URL`, que es idempotente y que no imprime la URL ni credenciales. Verificación: las tres instrucciones y las advertencias están presentes y coinciden con la ruta `app/seed.py` del diseño.
- [x] 3.2 Verificar que la sección no duplica ni contradice las secciones existentes de configuración y arranque, y que no incluye valores reales de conexión. Verificación: lectura del `README.md` completo; ninguna credencial ni host real aparece.

## 4. Verificación de integración

- [x] 4.1 Ejecutar la suite completa con PostgreSQL disponible: `.venv\Scripts\python.exe -m pytest -q`. Verificación: los 215 tests previos siguen en verde y los nuevos de `test/test_seed.py` pasan (o se saltan sin `DATABASE_URL`).
- [x] 4.2 Ejecutar el seed dos veces contra la base local, arrancar la app y comprobar `GET /libros/` con cuatro libros y `GET /ventas/2` con total `77000.00`. Verificación: los conteos no cambian entre ejecuciones y las respuestas coinciden con los ejemplos de la consigna.
- [x] 4.3 Ejecutar `openspec validate --strict datos-iniciales-seed`. Verificación: el change valida sin errores ni advertencias.

## Workflow follow-up

- Verificar formalmente el change con `openspec-verify-change` contra proposal, design y specs.
- Archivar el change (`openspec-archive-change`) y sincronizar la delta a `openspec/specs/seed-data/spec.md`.
- Marcar C-05 en `[x]` en `CHANGES.md` con su línea de cierre (doble ejecución, alta posterior por API, total `77000.00`).
