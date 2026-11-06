# Flujos Principales

## Flujo 1: Arranque de la aplicación (lifespan)

**Disparador**: `uvicorn app.main:app` o el `CMD` del contenedor.
**Actor**: operador / Docker.

**Pasos**:
1. `app/core/config.py` lee `DATABASE_URL` del entorno (`.env` en local, `--env-file` en el contenedor). Si falta, **falla el arranque** (D-05).
2. FastAPI ejecuta el `lifespan` de entrada.
3. Se crea el `AsyncEngine` (`create_async_engine(DATABASE_URL, echo=SQL_ECHO)`) y la fábrica `async_sessionmaker(expire_on_commit=False)`.
4. Motor y fábrica se guardan en `app.state`.
5. Se importan todos los modelos y se ejecuta `SQLModel.metadata.create_all` (solo crea tablas faltantes; no altera existentes).
6. Se registran los routers de todos los módulos.
7. La aplicación queda escuchando en `0.0.0.0:8000` (contenedor) o `127.0.0.1:8000` (local).
8. Al apagar (`SIGTERM`/Ctrl+C), el `lifespan` cierra el motor (`engine.dispose()`).

**Casos de error**:
- `DATABASE_URL` ausente → excepción en el arranque, el contenedor termina con error (D-05).
- Base inalcanzable → `create_all` falla, el arranque falla; Docker reinicia si `--restart unless-stopped`.
- Cambio de modelo sobre una base ya creada → `create_all` **no** lo aplica (limitación documentada, RN-G-05).

## Flujo 2: Alta de libro con editorial, género y autorías

**Disparador**: `POST /libros/`.
**Actor**: librero.

```
Cliente → Router → Pydantic/SQLModel valida → Service → DB
```

**Pasos**:
1. El router recibe `LibroCreate` (sin `id`).
2. Se valida el contrato: `precio > 0`, `stock >= 0`, `autores` con `rol` permitido y `orden >= 1` (422 si falla).
3. El servicio construye `Libro` con `editorial_id` y `genero_id` tal como vienen (sin consultar si existen).
4. Por cada autoría crea `LibroAutor(libro=libro, autor_id=..., rol=..., orden=...)` y la agrega a `libro.autorias`.
5. `session.add(libro)` + `commit`.
6. La base valida FK y UNIQUE. Si rechaza → `IntegrityError` → **409** con mensaje propio ("La editorial indicada no existe", "El autor indicado no existe", "El ISBN ya está registrado").
7. Se relee el libro con `selectinload(Libro.autorias).joinedload(LibroAutor.autor)` + `joinedload` de editorial y género.
8. Respuesta **201** con el detalle.

**Casos de error**:
- ISBN repetido → 409 (RN-01, C-02).
- `editorial_id` o `autor_id` inexistente → 409 (C-04).
- `genero_id` inexistente → 409 (RI-05).
- `precio <= 0` / `stock < 0` → 422 (RN-03).
- Autor repetido en el mismo libro → 409 (PK compuesta) o 422 si el DTO lo detecta antes.

## Flujo 3: Registro de venta (composición + copia de precio + total)

**Disparador**: `POST /ventas/`.
**Actor**: librero.

**Cuerpo**:
```json
{
  "cliente_id": 2,
  "renglones": [
    { "libro_id": 1, "cantidad": 2 },
    { "libro_id": 4, "cantidad": 1 }
  ]
}
```

**Pasos**:
1. El router recibe `VentaCreate` con renglones anidados (RN-04).
2. Validación del DTO: al menos un renglón y `libro_id` no repetido → 422 (RN-05).
3. El servicio carga los libros involucrados en **una** consulta (`WHERE id IN (...)`) para leer `precio` y `titulo`.
4. Si algún libro no existe → el intento de FK falla y se traduce a **409** (C-05). *(Alternativa equivalente: detectar el faltante al construir los renglones y responder 409 con mensaje propio; nunca 500.)*
5. Por cada renglón: `precio_unitario = libro.precio` (copia, RN-06) y `RenglonVenta(venta=venta, libro_id=..., cantidad=..., precio_unitario=...)`.
6. `total = sum(cantidad × precio_unitario)` (RN-07). `fecha = now(UTC)` con zona horaria.
7. `session.add(venta)` + `commit`; los renglones se persisten por composición (`cascade`).
8. Se agenda `BackgroundTasks.add_task(avisar_comprobante, ...)`; la tarea hace `await asyncio.sleep(0.5)` y escribe en el log.
9. Se relee la venta con `joinedload(Venta.cliente)` + `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`.
10. Respuesta **201** con cliente y renglones; el `subtotal` de cada renglón se calcula en el DTO de salida.
11. **Después** de enviada la respuesta, corre el aviso (D-07).

**Respuesta esperada**:
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

**Casos de error**:
- Cliente inexistente → 409 (C-05).
- Libro inexistente → 409 (C-05).
- Sin renglones o libro repetido → 422 (RN-05).
- Venta con precio o total en el cuerpo → esos campos no existen en el DTO de entrada; se ignoran o se rechazan según configuración (no se aceptan).

## Flujo 4: Lectura de detalle sin N+1

**Disparador**: `GET /libros/{id}` o `GET /ventas/{id}`.
**Actor**: librero / corrector.

**Pasos**:
1. El router delega en el servicio con `session` y `id`.
2. El servicio arma **una** consulta con carga anticipada:
   - Libro: `select(Libro).options(joinedload(Libro.editorial), joinedload(Libro.genero), selectinload(Libro.autorias).joinedload(LibroAutor.autor))`.
   - Venta: `select(Venta).options(joinedload(Venta.cliente), selectinload(Venta.renglones).joinedload(RenglonVenta.libro))`.
3. Si no hay resultado → **404**.
4. Se serializa el DTO de salida.
5. Con `SQL_ECHO=true`, la consola muestra un número **fijo** de consultas (3 para el libro: principal + selectin de autorías + joined de autores; independiente de cuántos autores haya).

**Casos de error**:
- Id no entero → 422 antes de ejecutar el handler (C-01).
- Id inexistente → 404.

## Flujo 5: Alta de perfil (uno a uno)

**Disparador**: `POST /clientes/{id}/perfil`.
**Actor**: librero.

**Pasos**:
1. Se busca el cliente; si no existe → **404**.
2. Se crea `PerfilCliente(cliente_id=id, telefono, direccion)`.
3. `commit`. El `UNIQUE(cliente_id)` decide.
4. Si ya tenía perfil → `IntegrityError` → **409** (C-03).
5. Respuesta **201** `PerfilRead`.

## Flujo 6: Healthchecks y contenedor

**Disparador**: `GET /health/live`, `GET /health/ready`, `HEALTHCHECK` de Docker.
**Actor**: Docker / corrector.

**Pasos**:
1. `/health/live` responde `{"estado": "vivo"}` sin abrir conexión a la base.
2. `/health/ready` ejecuta `SELECT 1` con la sesión; 200 si responde.
3. `HEALTHCHECK CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1`.
4. `docker ps` muestra `healthy`.

**Casos de error**:
- `wget http://localhost:8000/...` dentro de Alpine resuelve a `::1` (IPv6) y uvicorn escucha IPv4 → falso `unhealthy`. Usar **`127.0.0.1`**.
- Base caída → `/health/ready` falla y el contenedor queda `unhealthy`.

## Flujo 7: Actualización del despliegue

**Disparador**: nueva versión del código.
**Actor**: equipo.

**Pasos**:
1. `docker build -t libreria .` en el servidor (o build local + transferencia).
2. `docker rm -f libreria`.
3. `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo> libreria`.
4. Verificar `docker ps` → `healthy` y `/health/ready` → 200.

**Nota**: los datos no se pierden: viven en PostgreSQL del servidor, no en el contenedor (D-04).
