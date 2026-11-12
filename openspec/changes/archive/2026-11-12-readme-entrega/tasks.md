# Tasks

## 1. README de entrega

- [x] 1.1 Reescribir `README.md` con título, descripción, grupo ZorionTech e integrantes Lautaro Naranjo y Martin Escudero; verificar que ambos nombres y apellidos aparecen.
- [x] 1.2 Documentar requisitos (Python 3.12, PostgreSQL 16) y puesta en marcha desde cero: `python -m venv .venv`, `pip install -r requirements.txt -r requirements-dev.txt`, copia de `env.example` a `.env` y valores de `DATABASE_URL` y `SQL_ECHO`; verificar los comandos en una shell limpia.
- [x] 1.3 Documentar el arranque en Windows (`.venv\Scripts\python.exe -m uvicorn app.main:app --reload`) y en Linux/macOS (`python -m uvicorn app.main:app --reload`), con la nota de `create_all` del `lifespan` (DD-06).
- [x] 1.4 Documentar el seed (`python -m app.seed`, idempotente) y la ejecución de los casos: los `.http` de `test/` con VS Code REST Client o JetBrains HTTP Client, `@base` local o pública, y `pytest -q` con la variante que usa PostgreSQL.
- [x] 1.5 Documentar despliegue (URL real `http://46.202.151.202:8000`, enlace a `DEPLOY.md`, contenedor `libreria-zoriontech`, seed dentro del contenedor) y estructura breve del proyecto; verificar que no hay credenciales reales.

## 2. Plantilla de entorno

- [x] 2.1 Revisar `env.example`: solo `DATABASE_URL` con marcadores y `SQL_ECHO=false`; verificar con búsqueda de usuario, contraseña, host e IP reales.

## 3. Auditoría de DEPLOY.md

- [x] 3.1 Contrastar `DEPLOY.md` con la checklist de `knowledge-base/12_devops_y_despliegue.md`: URL, día y hora, comandos completos con el nombre de `/root/libreria-zoriontech.env` y sin su contenido, cambios hechos y procedimiento de actualización; corregir solo lo faltante y no agregar anexo de EasyPanel.
- [x] 3.2 Confirmar que `DEPLOY.md` no contiene contraseñas, usuarios de base reales ni el contenido del archivo de variables.

## 4. Paquete de entrega

- [x] 4.1 Crear una copia limpia en un directorio temporal con lista blanca: `app/`, `requirements*.txt`, `pyproject.toml`, `env.example`, `test/`, `Dockerfile`, `.dockerignore`, `README.md`, `DEPLOY.md`, `evidencia/` y `scripts/`; excluir `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`, `.env`, `.env.docker`, `*.zip`, `.git`, `docs/`, `knowledge-base/`, `openspec/`, `.atl/`, `.opencode/`, `design-system/`, `AGENTS.md`, `CLAUDE.md` y `.active-orchestrator-state.json`.
- [x] 4.2 Revisar la copia antes de comprimir: `DATABASE_URL` con credenciales reales, `password=`, claves privadas, tokens, la IP del VPS en `env.example` y archivos `libreria*.env`; revisar también los archivos que git ignora.
- [x] 4.3 Comprimir a `Parcial_Cap1a4_ZorionTech.zip` con una sola carpeta raíz `Parcial_Cap1a4_ZorionTech/`.
- [x] 4.4 Listar las entradas del `.zip`: confirmar una única raíz, todas las rutas incluidas, ninguna excluida y registrar el conteo.

## 5. Verificación

- [x] 5.1 Ejecutar `.venv\Scripts\python.exe -m pytest -q` y confirmar 405 passed + 3 skipped.
- [x] 5.2 Ejecutar `openspec validate --strict readme-entrega` y `openspec validate --all --strict`.
- [x] 5.3 Confirmar que `README.md` tiene los dos integrantes y la URL real, y que el `.zip` no contiene `.env`, `.env.docker`, `.git`, `.venv`, `__pycache__`, `openspec`, `docs`, `knowledge-base`, `AGENTS.md` ni `CLAUDE.md`.
- [x] 5.4 Hacer `GET http://46.202.151.202:8000/health/ready` de solo lectura y confirmar 200 `{"estado": "listo", "base": "ok"}`; no ejecutar ninguna otra acción contra el VPS.

## Workflow follow-up

- Actualizar la fila de C-11 en `CHANGES.md` con el resultado de la verificación y marcarla al archivar.
- `/opsx:verify` antes de `/opsx:archive`.
