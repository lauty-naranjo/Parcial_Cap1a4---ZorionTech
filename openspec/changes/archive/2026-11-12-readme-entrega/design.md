# Design

## Context

Ver `proposal.md` — Why. Estado que condiciona el diseño:

- **Suite**: 405 passed + 3 skipped (los skipped requieren PostgreSQL y se
  activan con `DATABASE_URL`). `pytest -q` es el comando de referencia.
- **Runtime**: `app/` con 9 tablas, seed en `app/seed.py`, healthchecks en
  `/health/live` y `/health/ready`, 26 operaciones en `app.openapi()["paths"]`.
- **Casos**: 8 archivos `.http` en `test/` (health, editoriales, generos,
  autores, libros, clientes, ventas, casos-C) con `@base` configurable.
- **Despliegue**: `http://46.202.151.202:8000`, contenedor
  `libreria-zoriontech`, base `libreria-zoriontech-db`, variables en
  `/root/libreria-zoriontech.env` (fuera del repositorio).
- **Evidencia**: `evidencia/` con C-07 ×2 y D-01…D-07, ya verificada por C-10.
- **Higiene**: `.gitignore` cubre `.env`, `.env.docker`, `.venv`,
  `__pycache__`, `.pytest_cache` y `*.zip`; `git status` está limpio y no hay
  archivos sin trackear fuera de lo ignorado.

## Goals / Non-Goals

**Goals:**

- README que permita a un tercero clonar, instalar, sembrar, arrancar y correr
  los casos sin preguntar nada.
- Identificar la entrega: grupo ZorionTech, integrantes Lautaro Naranjo y
  Martin Escudero.
- Plantilla de entorno sin un solo valor real.
- `.zip` con una sola carpeta raíz y exactamente el contenido de la consigna,
  sin secretos ni artefactos internos.

**Non-Goals:**

- No se modifica `app/`, el contrato HTTP, los tests, los `.http` ni
  `evidencia/`.
- No se reescribe `DEPLOY.md` más allá de lo que exija su checklist.
- No se incluye `.git`, `docs/`, `knowledge-base/`, `openspec/`, `.atl/`,
  `.opencode/`, `design-system/`, `AGENTS.md`, `CLAUDE.md` ni
  `.active-orchestrator-state.json` en el paquete.
- No se agrega un anexo de EasyPanel: el usuario lo pidió expresamente.

## Decisions

### D1 — Estructura del `README.md` final

Orden fijo, pensado para el corrector:

1. Título, descripción breve, **grupo e integrantes** (nombres y apellidos).
2. Requisitos: Python 3.12, PostgreSQL 16, Docker solo para el despliegue.
3. Puesta en marcha desde cero: venv, `pip install -r requirements.txt -r
   requirements-dev.txt`, copiar `env.example` a `.env`, completar
   `DATABASE_URL` y `SQL_ECHO`.
4. Arranque: `.venv\Scripts\python.exe -m uvicorn app.main:app --reload` en
   Windows y `python -m uvicorn app.main:app --reload` en Linux/macOS, con la
   nota de que el `lifespan` ejecuta `create_all` (DD-06: sin migraciones).
5. Datos iniciales: `.venv\Scripts\python.exe -m app.seed` (idempotente).
6. Cómo correr los casos: los 8 `.http` con VS Code REST Client o JetBrains
   HTTP Client, cambiando `@base` entre local y la URL pública; `pytest -q` y
   la variante con PostgreSQL.
7. Despliegue: URL pública real, enlace a `DEPLOY.md`, contenedor
   `libreria-zoriontech` y seed dentro del contenedor.
8. Estructura del proyecto (árbol breve) y notas de contrato.
9. Sin credenciales: los ejemplos usan `usuario:password@host:5432/base`.

Se conserva lo que ya era correcto (healthchecks, seed, `PATCH` de libros,
limitación de `create_all`) y se elimina la duplicación con `DEPLOY.md`.

### D2 — `env.example` solo con la forma

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@host:5432/base
SQL_ECHO=false
```

Sin usuario, clave, host ni IP reales. Se mantiene el comentario de
percent-encoding para contraseñas especiales. El archivo ya cumple; la tarea
es verificarlo y dejarlo explícito en el README.

### D3 — Auditoría de `DEPLOY.md` contra la checklist

| Ítem de la checklist | Dónde está | Acción |
|---|---|---|
| URL pública | §URL pública y fecha | Verificar `http://46.202.151.202:8000` |
| Día y hora | `2026-11-12T17:26:00Z` | Verificar |
| Comandos completos | §Construcción, §Ejecución, §Actualización | Verificar que usan el nombre `/root/libreria-zoriontech.env` |
| Archivo de variables sin contenido | §Archivos de variables | Verificar que no hay usuario/clave/host reales |
| Cambios hechos | §Qué hizo falta para que corra en el contenedor | Verificar |
| Actualización | §Actualización | Verificar `docker build` + `docker rm -f` + `docker run` |
| Anexo EasyPanel | — | No agregar (pedido del usuario) |

Si todo está presente, no se reescribe el documento. Cualquier mención a
EasyPanel queda solo como contexto del servidor compartido, no como
procedimiento.

### D4 — Armado del `.zip` desde una copia limpia

Se copia a un directorio temporal (`%TEMP%\entrega-zoriontech\`) usando una
lista blanca explícita; nunca se comprime la raíz del repositorio. La copia
contiene una sola carpeta raíz `Parcial_Cap1a4_ZorionTech/`:

| Entrada | Contenido |
|---|---|
| `app/` | Todo el paquete, incluido `app/seed.py` |
| `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` | Dependencias y configuración de pytest |
| `env.example` | Plantilla sin valores reales |
| `test/` | Los 8 `.http`, los `test_*.py`, `conftest.py`, helpers; sin `__pycache__` |
| `Dockerfile`, `.dockerignore` | Imagen |
| `README.md`, `DEPLOY.md` | Documentación de entrega |
| `evidencia/` | C-07 ×2 y D-01…D-07 |
| `scripts/` | `desplegar_vps.sh`, `verificar_despliegue.sh`, `verificar_imagen.sh`, `verificar_publico.sh`, `generar_evidencia_c07.py` |

Excluidos explícitos: `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`,
`.env`, `.env.docker`, `*.zip`, `.git/`, `docs/`, `knowledge-base/`,
`openspec/`, `.atl/`, `.opencode/`, `design-system/`, `AGENTS.md`,
`CLAUDE.md`, `.active-orchestrator-state.json`, `Parcial_Cap1a4_Consigna.pdf`.

**Alternativa descartada**: `git archive` desde el índice. No incluye
archivos ignorados legítimos (ninguno hace falta) y no permite verificar lo
que realmente contiene el disco; la lista blanca es más explícita y auditable.

### D5 — Revisión de secretos antes de comprimir

Sobre la **copia limpia** (no solo sobre el índice de git) se buscan:

- `DATABASE_URL` con credenciales reales (`postgresql+asyncpg://` seguido de
  algo distinto de `usuario:password@host`);
- `password=`, `PGPASSWORD`, `POSTGRES_PASSWORD=`;
- claves privadas (`BEGIN OPENSSH PRIVATE KEY`, `BEGIN RSA PRIVATE KEY`);
- tokens (`ghp_`, `github_pat_`, `sk-`, `Bearer `);
- la IP del VPS en `env.example`;
- archivos `libreria*.env` o `.env*` reales.

Se revisa el disco completo del paquete, no `git status`: un archivo ignorado
no aparece en git y sí podría colarse en una copia manual.

### D6 — Verificación posterior al comprimir

Se listan las entradas del `.zip` con `python -m zipfile -l` (o `tar -tf` si
está disponible) y se comprueba:

1. una sola raíz `Parcial_Cap1a4_ZorionTech/`;
2. están todas las entradas de la lista blanca;
3. no aparece ninguna de las excluidas (`.env`, `.env.docker`, `.git`,
   `.venv`, `__pycache__`, `openspec/`, `docs/`, `knowledge-base/`,
   `AGENTS.md`, `CLAUDE.md`);
4. el conteo de entradas queda registrado.

### D7 — Verificación final

- `pytest -q` → 405 passed + 3 skipped.
- `openspec validate --strict readme-entrega` y
  `openspec validate --all --strict`.
- `GET http://46.202.151.202:8000/health/ready` de solo lectura → 200
  `{"estado": "listo", "base": "ok"}`.
- `README.md` contiene ambos integrantes y la URL real.

No se ejecuta ninguna otra acción contra el VPS: la entrega no reinicia ni
muta el despliegue.

## Risks / Trade-offs

- **Zip con archivos internos** → lista blanca + verificación de entradas
  excluidas después de comprimir.
- **Secreto olvidado en un archivo ignorado** → revisión sobre la copia en
  disco, no solo sobre `git status`.
- **README que se desincroniza del código** → los comandos se ejecutan en la
  verificación y la suite cubre los contratos; el README no promete
  endpoints fuera de la matriz.
- **URL pública caída al momento de corregir** → es una dependencia externa;
  se verifica viva al cerrar y se documenta la fecha.

## Migration Plan

Sin migración de datos ni de runtime. Orden: README → `env.example` →
auditoría de `DEPLOY.md` → copia limpia → revisión de secretos → `.zip` →
verificación de contenido → suite y validaciones → cerrar C-11 en
`CHANGES.md`. Revertir es restaurar `README.md` y borrar el `.zip`.

## UI Mockups

Decision: no (no UI). C-11 no modifica pantallas, componentes ni estilos.
