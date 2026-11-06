# Contratos de API

> Tabla de referencia de la consigna. **Nombres de rutas y campos obligatorios.** Códigos: 200 lectura/edición, 201 alta, 404 recurso inexistente en lectura/PATCH, 409 rechazo de la base (unicidad o FK), 422 contrato o parámetros inválidos.

## Matriz de endpoints

| Método | Ruta | Cuerpo | Respuesta | Códigos |
|---|---|---|---|---|
| GET | `/health/live` | — | `{"estado": "vivo"}` | 200 |
| GET | `/health/ready` | — | Estado de la base | 200 |
| POST | `/editoriales/` | `EditorialCreate` | `EditorialRead` | 201, 409, 422 |
| GET | `/editoriales/` | `limit`, `offset` | Lista de `EditorialRead` | 200, 422 |
| GET | `/editoriales/{id}` | — | `EditorialRead` | 200, 404, 422 |
| PATCH | `/editoriales/{id}` | `EditorialUpdate` | `EditorialRead` | 200, 404, 409 |
| GET | `/editoriales/{id}/libros` | — | Libros de la editorial | 200, 404 |
| POST | `/generos/` | `GeneroCreate` | `GeneroRead` | 201, 409 |
| GET | `/generos/` | — | Lista de `GeneroRead` | 200 |
| GET | `/generos/{id}/libros` | — | Libros del género | 200, 404 |
| POST | `/autores/` | `AutorCreate` | `AutorRead` | 201, 422 |
| GET | `/autores/{id}` | — | `AutorRead` | 200, 404, 422 |
| PATCH | `/autores/{id}` | `AutorUpdate` | `AutorRead` | 200, 404, 422 |
| GET | `/autores/{id}/libros` | — | Libros con rol y orden | 200, 404 |
| POST | `/libros/` | `LibroCreate` con `autores` | Detalle del libro | 201, 409, 422 |
| GET | `/libros/` | `limit`, `offset`, `titulo`, `genero_id` | Libros con editorial y género | 200, 422 |
| GET | `/libros/{id}` | — | Libro con editorial, género y autores | 200, 404 |
| PATCH | `/libros/{id}` | `LibroUpdate` | Detalle del libro | 200, 404, 409, 422 |
| POST | `/clientes/` | `ClienteCreate` | `ClienteRead` | 201, 409, 422 |
| GET | `/clientes/{id}` | — | Cliente con su perfil | 200, 404 |
| PATCH | `/clientes/{id}` | `ClienteUpdate` | Cliente con su perfil | 200, 404, 409, 422 |
| POST | `/clientes/{id}/perfil` | `PerfilCreate` | `PerfilRead` | 201, 404, 409 |
| GET | `/clientes/{id}/ventas` | — | Ventas del cliente | 200, 404 |
| POST | `/ventas/` | `VentaCreate` con `renglones` | Venta con cliente y renglones | 201, 409, 422 |
| GET | `/ventas/` | `limit`, `offset` | Lista de ventas | 200, 422 |
| GET | `/ventas/{id}` | — | Venta con cliente y renglones | 200, 404 |

## DTO de entrada (Create / Update)

| DTO | Campos | Notas |
|---|---|---|
| `EditorialCreate` | `nombre`, `pais` | Sin `id` |
| `EditorialUpdate` | `nombre?`, `pais?` | PATCH parcial |
| `GeneroCreate` | `nombre` | — |
| `AutorCreate` | `nombre`, `nacionalidad` | — |
| `AutorUpdate` | `nombre?`, `nacionalidad?` | PATCH parcial |
| `AutorLibroCreate` | `autor_id`, `rol`, `orden` | `rol` ∈ 4 valores; `orden >= 1` |
| `LibroCreate` | `isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id?`, `autores: list[AutorLibroCreate]` | `precio > 0`, `stock >= 0`; sin precio total |
| `LibroUpdate` | `isbn?`, `titulo?`, `precio?`, `stock?`, `editorial_id?`, `genero_id?` | `exclude_unset` |
| `ClienteCreate` | `nombre`, `email` | `email` con formato válido |
| `ClienteUpdate` | `nombre?`, `email?` | `exclude_unset` |
| `PerfilCreate` | `telefono`, `direccion` | `cliente_id` va en la ruta |
| `RenglonCreate` | `libro_id`, `cantidad` (`>0`) | **Sin** `precio_unitario` |
| `VentaCreate` | `cliente_id`, `renglones: list[RenglonCreate]` (≥1) | **Sin** `total` ni `fecha` |

## DTO de salida (Read)

| DTO | Campos |
|---|---|
| `EditorialRead` | `id`, `nombre`, `pais` |
| `GeneroRead` | `id`, `nombre` |
| `AutorRead` | `id`, `nombre`, `nacionalidad` |
| `LibroRead` (listado) | `id`, `isbn`, `titulo`, `precio`, `stock`, `editorial`, `genero` |
| `LibroDetalleRead` | lo anterior + `autores: [{autor_id, nombre, rol, orden}]` |
| `ClienteRead` | `id`, `nombre`, `email`, `perfil` (objeto o `null`) |
| `PerfilRead` | `id`, `cliente_id`, `telefono`, `direccion` |
| `VentaRead` | `id`, `fecha`, `total`, `cliente`, `renglones` |
| `RenglonRead` | `libro_id`, `titulo`, `cantidad`, `precio_unitario`, `subtotal` |

Los importes se serializan como **string decimal** (`"25000.00"`).

## Ejemplos canónicos

### `POST /libros/`

```json
{
  "isbn": "978-950-00-0006-6",
  "titulo": "Los que aman, odian",
  "precio": "21000.00",
  "stock": 4,
  "editorial_id": 1,
  "genero_id": 1,
  "autores": [
    { "autor_id": 3, "rol": "coautor", "orden": 1 },
    { "autor_id": 4, "rol": "coautor", "orden": 2 }
  ]
}
```

### `POST /ventas/`

```json
{
  "cliente_id": 2,
  "renglones": [
    { "libro_id": 1, "cantidad": 2 },
    { "libro_id": 4, "cantidad": 1 }
  ]
}
```

Respuesta esperada (201):

```json
{
  "id": 2,
  "fecha": "2026-10-08T21:14:11.751581Z",
  "total": "77000.00",
  "cliente": { "id": 2, "nombre": "Tomás Ríos", "email": "tomas@example.com" },
  "renglones": [
    { "libro_id": 1, "titulo": "Rayuela", "cantidad": 2, "precio_unitario": "25000.00", "subtotal": "50000.00" },
    { "libro_id": 4, "titulo": "Respiración artificial", "cantidad": 1, "precio_unitario": "27000.00", "subtotal": "27000.00" }
  ]
}
```

## Paginación y filtros

| Parámetro | Tipo | Restricción | Default |
|---|---|---|---|
| `limit` | int | 1 ≤ limit ≤ 100 | 20 |
| `offset` | int | ≥ 0 | 0 |
| `titulo` (solo `/libros/`) | str | búsqueda parcial, `ilike`, parámetro ligado | — |
| `genero_id` (solo `/libros/`) | int | FK existente; filtro exacto | — |

## Errores y mensajes

| Situación | Código | Mensaje (propio, sin texto de la base) |
|---|---|---|
| ISBN repetido | 409 | "El ISBN ya está registrado" |
| Email repetido | 409 | "El email ya está registrado" |
| Segundo perfil | 409 | "El cliente ya tiene un perfil" |
| Editorial inexistente en alta de libro | 409 | "La editorial indicada no existe" |
| Autor inexistente en alta de libro | 409 | "El autor indicado no existe" |
| Género inexistente | 409 | "El género indicado no existe" |
| Cliente inexistente en venta | 409 | "El cliente indicado no existe" |
| Libro inexistente en venta | 409 | "El libro indicado no existe" |
| Recurso inexistente en lectura/PATCH | 404 | "No encontrado" |
| Contrato inválido | 422 | Detalle de validación de Pydantic (sin trazas) |
| Parámetro de ruta no entero | 422 | Respuesta automática de FastAPI, handler no ejecutado |

> **Regla**: el `IntegrityError` se mapea por nombre de constraint a un mensaje propio. Nunca se devuelve `str(exc)` ni la traza.

## Casos de prueba mínimos (`.http` en `test/`)

| Caso | Qué se demuestra | Resultado esperado |
|---|---|---|
| C-01 | Parámetro de ruta no entero | 422, handler no ejecutado |
| C-02 | ISBN o email repetido | 409 con mensaje propio |
| C-03 | Segundo perfil del mismo cliente | 409 |
| C-04 | Libro con editorial o autor inexistente | 409 con mensaje propio |
| C-05 | Venta con libro o cliente inexistente | 409 |
| C-06 | Venta válida con dos renglones | 201, precios copiados y total calculado |
| C-07 | Detalle de libro y de venta | Cantidad fija de consultas en consola |
| C-08 | Búsqueda con `' OR '1'='1` | 200 con lista vacía |
| D-01 | `docker images` | `python:3.12-alpine` < 100 MB y usada en el Dockerfile |
| D-02 | `docker build` + `docker run` + `docker ps` | Contenedor `healthy`; logs con tablas creadas |
| D-03 | Desde fuera: `/health/ready`, `/libros/`, `POST /ventas/` | 200, 200 con libros, 201 con total correcto |
| D-04 | `docker rm -f` + mismo `run` | Vuelve `healthy`; los datos siguen |
| D-05 | Correr sin `DATABASE_URL` | El contenedor termina con error |
| D-06 | `docker exec libreria id` | Usuario no root |
| D-07 | Venta registrada | Aviso de comprobante en logs después de la respuesta |

Cada caso lleva su resultado esperado **como comentario** en el archivo `.http`.
