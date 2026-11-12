# Tareas pendientes — Martin Escudero

> **Para el agente de OpenCode de Martin**: este archivo es la tarea a ejecutar.
> El proyecto ya está terminado y funcionando; estas dos mejoras quedaron
> pendientes a propósito para que las implementes vos, con TDD, y las subas con
> tus propios commits.
> Leé también `AGENTS.md` (reglas duras del proyecto) y `knowledge-base/` si
> necesitás contexto del dominio.

---

## Contexto mínimo

- API REST asincrónica de librería: **FastAPI + SQLModel + SQLAlchemy async + asyncpg + PostgreSQL**.
- Python 3.12. Venv: `.venv\Scripts\python.exe` (Windows) o `.venv/bin/python` (Linux/macOS).
- Suite actual en `main`: **405 passed + 3 skipped**. Al terminar tiene que quedar en **422 passed + 3 skipped**.
- El despliegue está en `http://46.202.151.202:8000` y **no lo toques**.

### Puesta en marcha en tu máquina

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
Copy-Item env.example .env    # completá DATABASE_URL y SQL_ECHO=false
.venv\Scripts\python.exe -m pytest -q
```

`.env` no viaja en el repo: lo creás vos. Sin PostgreSQL accesible, los tests de
integración se saltean (los 3 skips conocidos).

---

## Tarea 1 — `PATCH` con `null` explícito debe devolver **422**

### Problema
Hoy, por ejemplo:

```http
PATCH /libros/1
{"titulo": null}
```

devuelve **409**. La causa: el schema `LibroUpdate` declara `titulo: str | None`,
Pydantic acepta `null`, `model_dump(exclude_unset=True)` lo incluye, el `NOT NULL`
de la base dispara `IntegrityError` y se traduce a 409 (conflicto de integridad).

La consigna dice que **422** es para un cuerpo que no cumple el contrato. Un
`null` explícito en un campo que no admite nulos es un error de contrato, no un
conflicto: debe ser **422**.

### Qué hacer
1. Crear un helper reutilizable, por ejemplo en `app/core/schemas.py`:

   ```python
   from pydantic import BaseModel

   def rechazar_nulos_explicitos(modelo: BaseModel, campos: tuple[str, ...]) -> None:
       for campo in campos:
           if campo in modelo.model_fields_set and getattr(modelo, campo) is None:
               raise ValueError(f"El campo '{campo}' no admite null")
   ```

   La clave es distinguir **omitido** de **null explícito**: `model_fields_set`
   contiene solo los campos enviados.

2. Aplicarlo con `@model_validator(mode="after")` en los cuatro `Update`:

   | Schema | Campos que NO admiten `null` |
   |---|---|
   | `EditorialUpdate` | `nombre`, `pais` |
   | `AutorUpdate` | `nombre`, `nacionalidad` |
   | `ClienteUpdate` | `nombre`, `email` |
   | `LibroUpdate` | `isbn`, `titulo`, `precio`, `stock`, `editorial_id` |

3. **`genero_id` de `LibroUpdate` NO se rechaza**: es nullable y
   `{"genero_id": null}` debe seguir devolviendo **200** y dejar el género en
   `null`.

No toques endpoints, códigos de otros casos ni el comportamiento de los campos
opcionales.

### Tests (primero en RED)
Creá `test/test_patch_nulos.py` con, como mínimo:
- Por cada módulo, `PATCH` con `null` explícito en un campo no nulo → **422** y
  el recurso **no cambia** (releer y comparar).
- `PATCH` omitiendo el campo → **200**, y el resto se actualiza.
- `PATCH /libros/{id} {"genero_id": null}` → **200** y `genero: null`.
- Caso combinado `{"titulo": null, "stock": 5}` → **422** y **no** se aplica el
  stock.

Corré los tests antes del fix: tienen que fallar con `409 != 422`. Recién
después implementá.

### Criterio de aceptación
- `pytest -q` pasa con los 17 tests nuevos y sin romper los 405 existentes.
- El error sale por la validación de FastAPI (422 con `detail`), nunca por
  `IntegrityError`.
- `genero_id: null` sigue funcionando.

---

## Tarea 2 — Pinear `requirements.txt`

Hoy usa mínimos (`>=`), lo que hace que dos instalaciones puedan resolver
versiones distintas. Reemplazalo por las versiones exactas ya verificadas en el
entorno del proyecto **y en la imagen Docker del VPS**:

```txt
fastapi[standard]==0.162.2
sqlmodel==0.0.48
sqlalchemy[asyncio]==2.1.8
asyncpg==0.32.0
python-dotenv==1.2.4
```

No agregues `uvicorn`: viene con `fastapi[standard]`.

Después del cambio, verificá que la suite siga verde. Si querés probar la imagen
en tu máquina:

```bash
docker build -t libreria-local .
docker run --rm --entrypoint python libreria-local -c "import fastapi, sqlmodel, sqlalchemy, asyncpg; print('ok')"
```

**No reconstruyas ni toques el contenedor del VPS.**

---

## Reglas del proyecto (obligatorias)

1. **No** usar `float` para dinero: `Decimal` en Python y `Numeric` en la base.
2. **No** cambiar contratos HTTP, endpoints ni códigos de otros casos.
3. **No** devolver `str(exc)`, nombres de constraints ni trazas al cliente.
4. Todos los handlers `async def`; nada bloqueante.
5. **No** commitear `.env`, `.env.docker` ni `libreria.env` (ya están en `.gitignore`).
6. **No** tocar el VPS ni el despliegue en producción.
7. Español en comentarios y documentación; `SHALL`/`MUST` en inglés solo en specs.

---

## Cómo entregar tu trabajo

1. Configurá tu identidad en git (una sola vez):
   ```bash
   git config user.name "Martin Escudero"
   git config user.email "tu-email@..."
   ```
2. Hacé commits chicos y con sentido, por ejemplo:
   - `feat(core): helper para rechazar null explícito`
   - `fix(editoriales|autores|clientes|libros): PATCH con null devuelve 422`
   - `test(patch): cobertura de null explícito`
   - `chore(deps): pinear requirements a las versiones verificadas`
3. Antes de pushear: `git pull --rebase origin main` y volvé a correr `pytest -q`.
4. `git push origin main`.
5. Avisale a Lautaro cuando esté.

> **Nota**: existe una rama `respaldo/patch-null-pin` con una implementación de
> referencia de estas dos tareas. Podés consultarla si te trabás, pero la idea es
> que la implementes vos y la entiendas. Si la usás, no copies sin correr los
> tests.

---

## Checklist final

- [ ] `pytest -q` → **422 passed + 3 skipped**, 0 failed.
- [ ] `PATCH {"titulo": null}` → 422; `{"genero_id": null}` → 200.
- [ ] `requirements.txt` con las cinco versiones exactas.
- [ ] `git status` sin `.env` ni archivos temporales.
- [ ] Commits con tu nombre y `git push origin main`.
