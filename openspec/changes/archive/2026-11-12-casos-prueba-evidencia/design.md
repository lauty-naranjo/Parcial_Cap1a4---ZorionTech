# Design

## Context

Ver `proposal.md` — Why. El estado actual que condiciona el diseño:

- **Suite**: 302 tests recolectados (299 passed + 3 skipped por requerir PostgreSQL). `test/conftest.py` deriva una base `<nombre>_test` de `DATABASE_URL`, dropea y recrea el esquema por prueba (`motor_bd`) e inyecta la sesión real en la app (`cliente_bd`). `app.seed.sembrar(url)` es idempotente y usa ids deterministas.
- **Sin `.http`**: `test/` solo tiene `test/.gitkeep` y los `test_*.py`. No hay parser ni runner de `.http`.
- **Endpoints**: 26 operaciones. La versión de FastAPI instala `_IncludedRouter` en `app.routes`, por lo que el inventario de rutas debe leerse de `app.openapi()["paths"]`, no de `app.routes`.
- **Evidencia**: `evidencia/` tiene los 9 archivos (C-07 ×2 y D-01…D-07) con salidas reales; `scripts/generar_evidencia_c07.py` los regenera.
- **Estilo de tests de artefactos**: `test_artefactos_*.py` son estáticos (`Path` + regex) y fallan sin tocar red ni Docker.

## Goals / Non-Goals

**Goals:**

- Ocho `.http` portables, autocontenidos y con expectativa declarada por bloque.
- Demostrar automáticamente que cada expectativa declarada es la que la app devuelve.
- Cerrar solo los huecos reales de la suite, sin duplicar los 299 tests existentes.
- Proteger los contratos de entrega: RN-12, importes string, paginación total, evidencia presente.

**Non-Goals:**

- No se agregan ni cambian endpoints, DTO, esquema, reglas de negocio ni dependencias.
- No se reescribe ni se regenera la evidencia C-07/D-01…D-07.
- No se corre la suite completa contra el VPS en CI ni se automatiza el despliegue.
- No se genera un cliente OpenAPI ni se documentan endpoints fuera de la matriz.

## Decisions

### D1 — Formato de los `.http`

Contrato de bloque, idéntico en los ocho archivos:

```http
@base = http://localhost:8000
@libro = 1
@cliente = 2

# Librería de barrio — casos C-02 (ISBN repetido)
# Requiere: uvicorn app.main:app y `python -m app.seed`

### Caso C-02 — ISBN repetido: esperado 409 con mensaje propio
POST {{base}}/libros/
Content-Type: application/json

{
  "isbn": "978-950-00-0001-1",
  "titulo": "Duplicado",
  "precio": "10000.00",
  "stock": 1,
  "editorial_id": 1,
  "genero_id": 1,
  "autores": [{"autor_id": 1}]
}

# Caso: C-02
# Esperado: 409 — {"detail": "El ISBN ya está registrado"}
```

Reglas:

- `@base = http://localhost:8000` en la primera línea de contenido de cada archivo; `@libro`/`@cliente` solo donde se usan.
- Separador `###` antes de cada request; el texto tras `###` describe el request.
- Dos líneas obligatorias al final del bloque: `# Caso:` y `# Esperado:`.
- El valor de `# Caso:` es `C-0N`/`D-xx` cuando el request demuestra un caso de la consigna, o `CRUD` cuando solo documenta una operación de soporte. Esta es la interpretación de "cada request con el código de caso": los archivos por módulo no fuerzan un código C inexistente para un CRUD que no lo es; el validador exige que la unión cubra C-01…C-08.
- Sin credenciales, sin `DATABASE_URL`, sin IPs ni hosts del VPS; solo `{{base}}`.
- UTF-8 sin BOM (los títulos del seed llevan acentos: `Respiración artificial`).

### D2 — Distribución de casos por archivo

| Archivo | Bloques | Casos |
|---|---|---|
| `health.http` | `/health/live`, `/health/ready`; nota de `wget 127.0.0.1` del HEALTHCHECK | `CRUD` (soporte D-02/D-03) |
| `editoriales.http` | listar, crear, crear duplicado, detalle, `PATCH` parcial, `PATCH` 404, `/{id}/libros`, `/{id}/libros` 404, `/abc` | C-01, CRUD |
| `generos.http` | listar, crear, duplicado, `/{id}/libros`, `/{id}/libros` 404, `/{id}/libros` con `limit=0` | CRUD |
| `autores.http` | listar, crear, detalle, `PATCH`, 404, `/{id}/libros` con rol/orden, `/abc` | C-01, CRUD |
| `libros.http` | listar con `limit/offset/titulo/genero_id`, detalle, `PATCH` parcial (ignora `autores`), `PATCH` 404, `/abc`, alta completa | C-01, CRUD |
| `clientes.http` | listar, crear, email duplicado, detalle con perfil `null`, `PATCH`, `/{id}/ventas`, `/abc` | C-02, C-01, CRUD |
| `ventas.http` | listar con paginación, detalle con renglones, detalle 404, `/abc`, venta con dos renglones (201, 77000.00) | C-01, C-06, CRUD |
| `casos-C.http` | C-01 ×3 rutas, C-02 ISBN y email, C-03 primer y segundo perfil, C-04 editorial y autor inexistentes, C-05 cliente y libro inexistentes, C-06 venta 201, C-08 inyección | C-01…C-06, C-08 |

`casos-C.http` es la hoja de ruta del corrector: recorre los siete casos HTTP en orden, referenciando el módulo dueño cuando aplica. C-07 va como bloque de comentario con el comando y la evidencia (D3).

### D3 — C-07 no es un request

En `casos-C.http`, bloque final sin línea de request:

```http
### Caso C-07 — cantidad fija de consultas (comando, no request)
# Arrancar con SQL_ECHO=true y pedir:
#   GET /libros/1  (1 autor)   → 2 SELECT
#   GET /libros/2  (3 autores) → 2 SELECT
#   GET /ventas/2  (2 renglones) → 2 SELECT
# Evidencia: evidencia/C-07-consultas-libro.txt y evidencia/C-07-consultas-venta.txt
# Caso: C-07
# Esperado: el conteo no cambia con la cardinalidad (RN-G-03, IN-04)
```

El test estático exige que el bloque C-07 mencione ambos archivos de evidencia y el comando con `SQL_ECHO`. El conteo fijo ya está automatizado en `test_sin_n_plus_uno.py`; no se duplica.

### D4 — Runner de replay: por archivo, secuencial, base sembrada

`test/http_runner.py` expone `leer_archivo(path) -> list[BloqueHttp]` y `BLOQUES`. El parser:

- Ignora líneas de comentario y bloques sin método HTTP (C-07).
- Extrae método, ruta (sustituyendo `{{base}}`/`{{var}}`), cuerpo JSON crudo, `# Caso:` y `# Esperado:`.
- Convierte `# Esperado: 409 — {"detail": "..."}` en `(409, fragmentos)`. Los fragmentos se comparan como texto normalizado (JSON re-serializado cuando el fragmento es JSON) para no depender del espaciado.

`test_casos_http.py` recorre **un archivo por prueba**, en el orden del archivo, con:

1. `motor_bd` (esquema limpio) + `sembrar(url_bd_test)` → estado inicial idéntico al del corrector, IDs 1…4.
2. `cliente_bd` (sesión real inyectada) y `monkeypatch` de `app.modules.ventas.router.avisar_comprobante` por un no-op, para no esperar 0.5 s por venta; el aviso real ya está cubierto por `test_asincronia.py`.
3. Se ejecutan todos los bloques y se acumulan los desvíos; al final, un `assert not desvios` con archivo, número de línea, esperado y obtenido de cada uno. Así un desvío no oculta los siguientes.
4. Sin `DATABASE_URL` la prueba se salta, igual que el resto de `cliente_bd`; los tests estáticos de D1–D3 corren siempre.

Re-ejecutar la suite reproduce el mismo resultado porque cada archivo parte de un esquema dropeado y sembrado; ningún bloque depende de una corrida anterior. Los `POST` de los `.http` usan ids del seed y no inventan estado previo, salvo las secuencias crear → duplicado, que el orden del archivo garantiza.

**Alternativa descartada**: un test por bloque con base nueva. Rompe los pares crear/duplicar y multiplica el costo de seed sin mejorar el aislamiento.

### D5 — 422 sin ejecutar el handler: prueba por conteo

Se instrumenta `contador_consultas(motor_bd)` y se piden rutas con id no entero en los seis recursos y en las sub-colecciones (`/libros/abc`, `/editoriales/abc`, `/generos/abc/libros`, `/autores/abc`, `/clientes/abc`, `/clientes/abc/ventas`, `/ventas/abc`, `PATCH /libros/abc`). Se exige `422` y `cuenta.total == 0`: es la prueba observable de "handler no ejecutado". Hoy solo hay tres 422 de este tipo y ninguno verifica el conteo.

### D6 — Huecos de regresión detectados y archivo que los cubre

| # | Hueco | Cobertura actual | Test nuevo |
|---|---|---|---|
| G1 | No existe ningún `.http` ni contrato de formato | — | `test_artefactos_http.py` |
| G2 | Nada verifica que el `# Esperado:` declarado sea real | — | `test_casos_http.py` |
| G3 | RN-12 solo está probado sobre el mapeador, no por HTTP | `test_errores.py` (unitario) | `test_regresion_entrega.py::test_errores_no_filtran_texto_de_base` |
| G4 | C-01 sin prueba de "handler no ejecutado"; faltan rutas | 3 tests de 422 | `test_regresion_entrega.py::test_parametro_de_ruta_invalido_no_consulta` |
| G5 | RN-10 no probado en `/{id}/libros` ni `/{id}/ventas` | alias aislado + 4 listados | `test_regresion_entrega.py::test_toda_coleccion_pagina` |
| G6 | Importes string solo por assertions puntuales | tests por módulo | `test_regresion_entrega.py::test_importes_son_string_decimal` |
| G7 | Evidencia C-07/D-01/D-02/D-05/D-06 sin guarda | D-03/D-04/D-07 parcial | `test_artefactos_http.py::test_evidencia_*` |
| G8 | `.http` con endpoint inexistente no se detecta | — | `test_artefactos_http.py::test_rutas_declaradas_existen` |

No se agregan tests para health, 404, 409 por UNIQUE/FK por módulo, `PATCH` parcial, venta con renglones (77000.00) ni conteo fijo: ya están cubiertos con base real.

### D7 — Guardas transversales (RN-12 e importes)

`test_regresion_entrega.py` parametriza sobre respuestas reales:

- **RN-12**: 409 por ISBN, email, perfil, editorial, autor, cliente y libro; 404 de detalle; 422 de contrato. El cuerpo serializado no debe contener `duplicate key`, `violates`, `constraint`, `Traceback`, `asyncpg`, `psycopg`, `IntegrityError`, `SELECT`, ni los nombres `uq_`/`fk_`; además el `detail` debe ser uno de los mensajes propios del contrato.
- **Importes**: `GET /libros/`, `GET /libros/1`, `GET /ventas/`, `GET /ventas/2`, `GET /clientes/2/ventas` y el `POST /ventas/` del caso C-06 deben devolver `precio`, `total`, `precio_unitario` y `subtotal` como `str` que cumple `^\d+\.\d{2}$`.

### D8 — Validación contra el VPS

- Obligatoria y automatizada: replay local contra ASGI con base sembrada (D4).
- Manual y de solo lectura sobre `http://46.202.151.202:8000`: `/health/live`, `/health/ready`, un listado y C-08; se registra en el informe del change, no en `evidencia/` (esa carpeta no se toca).
- Mutantes contra el VPS (altas, perfil, ventas) **no** se reejecutan: contaminarían la base entregada y D-03 ya demuestra la venta C-06. El runbook deja el paso opcional y advierte que muta datos.

### D9 — Organización de los tests nuevos

| Archivo | Tipo | Depende de |
|---|---|---|
| `test/http_runner.py` | helper (no se recolecta: no empieza con `test_`) | stdlib |
| `test/test_http_runner.py` | unitario del parser | stdlib |
| `test/test_artefactos_http.py` | estático: presencia, formato, cobertura C-01…C-08, rutas contra OpenAPI, evidencia, secretos | disco |
| `test/test_casos_http.py` | replay por archivo | PostgreSQL de test |
| `test/test_regresion_entrega.py` | guardas RN-12, importes, C-01, RN-10 | PostgreSQL de test |

### D10 — Datos del seed usados en los `.http`

| Dato | Valor |
|---|---|
| Editorial | `1` = Sudamericana |
| Género | `1` = Novela |
| Autores | `1` Cortázar, `2` Piglia, `3` García Márquez, `4` Vargas Llosa |
| Libros | `1` Rayuela `25000.00` (1 autor), `2` Antología (3 autores), `4` Respiración artificial `27000.00` |
| Clientes | `1` Ana Gómez `ana@example.com`, `2` Tomás Ríos `tomas@example.com` |
| Venta | `2` = cliente 2, dos renglones, `77000.00` |
| Perfiles | ninguno (habilita C-03: primer `POST` 201, segundo 409) |

Los `.http` no dependen de ids creados por otros bloques, salvo los pares crear → duplicado dentro del mismo archivo.

## Risks / Trade-offs

- **Expectativa desactualizada** (el `.http` promete 409 y la app devuelve 422) → el replay falla con archivo y línea; la regla es corregir el `.http`, nunca relajar el test. Si el comportamiento fuera el incorrecto, se abre un change aparte: C-10 no modifica la API.
- **Costo de seed por archivo** (8 seeds + 8 reseteos de esquema) → aceptable frente a los 302 tests actuales; el replay es secuencial y determinista.
- **Tarea de fondo de 0.5 s por venta** → se neutraliza solo en el replay; el comportamiento real sigue cubierto en `test_asincronia.py`.
- **Parser frágil** → formato acotado (`# Caso:`, `# Esperado:`, `###`, `@var`) y tests unitarios del parser; un `.http` mal formado falla con mensaje explícito.
- **Datos del VPS contaminados** → política D8: solo lecturas contra la URL pública.
- **Tests de replay saltados sin `DATABASE_URL`** → el informe del apply debe declarar cuántos tests corrieron con base real; los estáticos nunca se saltan.

## Migration Plan

Sin migración de datos ni de runtime. Orden de trabajo (detalle en `tasks.md`): parser → tests estáticos → `.http` → replay → huecos de regresión → evidencia → suite completa → smoke de solo lectura en el VPS → marcar C-10 en `CHANGES.md`. Revertir es borrar los archivos nuevos; no toca `app/` ni la base.

## UI Mockups

Decision: no (no UI). C-10 no modifica pantallas, componentes ni estilos.
