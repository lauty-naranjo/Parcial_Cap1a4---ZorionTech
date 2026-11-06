# Reglas de Negocio

La consigna fija códigos **RN-01 … RN-12**. Se conservan exactamente para trazabilidad con la corrección. Cada regla indica su garante y dónde se hace cumplir.

## Dominio: Catálogo

### RN-01 — ISBN único
El ISBN de un libro es único.
**Garante**: `UNIQUE` en `libro.isbn`. Al violarse, el servicio traduce `IntegrityError` → **409** con mensaje propio (nunca el texto de PostgreSQL).
**Prohibido**: consultar antes si el ISBN existe.

### RN-02 — Email único
El email de un cliente es único.
**Garante**: `UNIQUE` en `cliente.email`; `IntegrityError` → **409**.

### RN-03 — Precio y stock válidos
El precio de un libro es mayor que cero y el stock nunca es negativo.
**Garante doble**: `CHECK (precio > 0)` y `CHECK (stock >= 0)` en la base **y** validación del DTO (`Field(gt=0)`, `Field(ge=0)`). El DTO devuelve **422**; la base es la última línea de defensa.

## Dominio: Ventas

### RN-04 — La venta se crea con sus renglones
Los datos de cada renglón viajan **dentro del cuerpo del alta de la venta**. No existe un alta de renglones por separado.
**Garante**: DTO anidado `VentaCreate.renglones: list[RenglonCreate]`; los renglones se agregan a `venta.renglones` antes del `commit`.

### RN-05 — Al menos un renglón y libros no repetidos
Una venta tiene al menos un renglón, y un mismo libro no aparece en dos renglones.
**Garante**: validación del DTO → **422**. `min_length=1` en la lista y validación de unicidad de `libro_id`.

### RN-06 — El precio del renglón se copia del libro
El precio de cada renglón se copia del libro al registrar la venta y **no cambia** aunque después cambie el precio del libro.
**Garante**: el servidor lee `libro.precio` de la base y lo persiste en `renglon_venta.precio_unitario`. El precio **nunca** viaja en el DTO de entrada.

### RN-07 — El total lo calcula el servidor
El total de la venta es la suma de `cantidad × precio_unitario` de sus renglones.
**Garante**: cálculo en el servicio; `total` **no viaja en el DTO**. `CHECK (total >= 0)` en la base.

### RN-08 — Las ventas no se modifican
Las ventas registran un hecho: no hay `PATCH` ni `PUT` de ventas.
**Garante**: ausencia de la ruta. Tampoco se expone borrado.

## Dominio: Clientes

### RN-09 — Un cliente tiene como máximo un perfil
**Garante**: `UNIQUE` en `perfil_cliente.cliente_id`; el segundo alta → **409**.

## Dominio: Contratos y listados

### RN-10 — Paginación obligatoria
Todo listado se pagina con `limit` (1 a 100, por defecto 20) y `offset` (desde 0).
**Garante**: `Query(20, ge=1, le=100)` y `Query(0, ge=0)`; fuera de rango → **422**.

### RN-11 — Búsqueda por título parcial e insensible a mayúsculas
El listado de libros se puede filtrar por parte del título, sin distinguir mayúsculas.
**Garante**: parámetro ligado (`ilike(f"%{titulo}%")`), **nunca SQL armado por concatenación**. Un texto como `' OR '1'='1` es un valor literal y devuelve lista vacía (C-08).

## Dominio: Errores

### RN-12 — Sin texto interno de la base
Ningún error devuelve al cliente nombres de tablas, restricciones ni trazas.
**Garante**: traducción explícita de `IntegrityError` a mensajes propios (409) y de errores de validación a 422; los errores no controlados no exponen trazas.

## Reglas de integridad referencial (derivadas de la consigna)

| Código | Regla | Garante | Código HTTP |
|---|---|---|---|
| RI-01 | Un libro no puede referenciar una editorial inexistente | FK `libro.editorial_id` + traducción de `IntegrityError` | 409 |
| RI-02 | Un libro no puede referenciar un autor inexistente | FK `libro_autor.autor_id` + traducción | 409 |
| RI-03 | Una venta no puede referenciar un cliente inexistente | FK `venta.cliente_id` + traducción | 409 |
| RI-04 | Un renglón no puede referenciar un libro inexistente | FK `renglon_venta.libro_id` + traducción | 409 |
| RI-05 | Un género inexistente en el alta de libro | FK `libro.genero_id` + traducción | 409 |

> **Nuance crítica (C-04, C-05)**: un id inexistente en un alta responde **409**, no 404. El 404 está reservado para lecturas y PATCH de un recurso que no existe. Y **no se consulta antes** si el id existe: se escribe y se traduce el rechazo de la base.

## Excepciones globales

- **RN-G-01** — Dinero siempre `Decimal`/`Numeric`, nunca `float`.
- **RN-G-02** — Ningún handler ejecuta una llamada bloqueante: ni `time.sleep`, ni `requests`, ni acceso síncrono a la base.
- **RN-G-03** — Toda relación que se lee se precarga en la misma consulta; la carga perezosa está prohibida.
- **RN-G-04** — Ninguna credencial en el código, el repositorio, la imagen ni el `.zip`.
- **RN-G-05** — `create_all` al arrancar solo crea tablas faltantes; no altera tablas existentes.
- **RN-G-06** — La fecha de la venta la pone el servidor con zona horaria; no viaja en el DTO.

## Matriz regla → caso de prueba

| Regla | Caso |
|---|---|
| RN-01 | C-02 |
| RN-02 | C-02 |
| RN-03 | Validación de DTO (422) y CHECK (base) |
| RN-04, RN-05, RN-06, RN-07 | C-06 |
| RN-08 | Ausencia de PATCH en `/ventas/` |
| RN-09 | C-03 |
| RN-10 | C-01 (422 por parámetro inválido) |
| RN-11 | C-08 |
| RN-12 | C-02, C-04, C-05 |
| RI-01…RI-05 | C-04, C-05 |
| RN-G-03 | C-07 |
| RN-G-02 | D-07 |
| RN-G-05 | D-04 |
| RN-G-04 | D-01, revisión del historial de Git |
