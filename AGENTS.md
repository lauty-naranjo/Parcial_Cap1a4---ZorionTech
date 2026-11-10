# ZorionTech — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

---

## Stack Tecnológico

API REST asincrónica de catálogo y ventas para una librería de barrio (Parcial Cap. 1 a 4, Programación III).

| Capa | Tecnología | Versión mínima | Uso |
|---|---|---|---|
| Lenguaje | Python | 3.12 | Runtime de la aplicación |
| Framework web | FastAPI | 0.111 | API REST; todos los handlers `async def` |
| Modelos y DTO | SQLModel | 0.0.24 | Modelos de tabla y contratos en una sola librería |
| ORM | SQLAlchemy | 2.0 (asincrónico) | Motor, sesión y carga anticipada |
| Driver | asyncpg | 0.30 | Controlador asincrónico de PostgreSQL |
| Base de datos | PostgreSQL | 16 | Persistencia; en el despliegue, la del servidor |
| Configuración | python-dotenv | 1.0 | Lectura del archivo `.env` |
| Servidor ASGI | uvicorn | la que instala `fastapi[standard]` | Servir la app (`app.main:app`) |
| Contenedor | Docker | 20.10 | Construir la imagen y correr el contenedor en local y en el VPS |

Sin frontend, auth, Redis, colas, migraciones ni Docker Compose. Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Contenido |
|---------|-----------|
| [README.md](knowledge-base/README.md) | Índice de la KB, resumen ejecutivo, quick start y riesgos principales |
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Propósito, 5 actores, alcance de la entrega, fuera de alcance, métricas |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack con versiones, arquitectura general, integraciones, resumen de API |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Actores, ausencia de RBAC, rutas públicas |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | 8 tablas con columnas obligatorias, ERD, relaciones y justificación del lado de cada FK, índices, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | RN-01 a RN-12, reglas de integridad (RI-01…05), reglas globales y matriz regla → caso |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | 5 épicas y 20 historias de usuario con criterios de aceptación |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | 7 flujos extremo a extremo (arranque, alta de libro, alta de venta, lectura sin N+1, perfil, healthchecks, actualización) |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura de directorios obligatoria, capa de datos, seguridad, variables de entorno |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | 10 decisiones (DD) y 8 supuestos (SU) con trade-offs y riesgo |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | 6 ambigüedades + 11 preguntas priorizadas |
| [11_contratos_api.md](knowledge-base/11_contratos_api.md) | Matriz completa de endpoints, DTOs, ejemplos, errores y casos C/D |
| [12_devops_y_despliegue.md](knowledge-base/12_devops_y_despliegue.md) | Dockerfile, `.dockerignore`, `docker run`, healthcheck, `DEPLOY.md`, evidencia, checklist de entrega |

### Inconsistencias a resolver ANTES de codear

`knowledge-base/10_preguntas_abiertas.md` §Inconsistencias / ambigüedades detectadas. Ninguna se resuelve improvisando en el código: se acuerda la decisión y se documenta en el `README.md` o en el artefacto del change que corresponda.

- **IN-01** — ¿`PATCH /libros/{id}` edita la lista de autores? Propuesta: limitarlo a campos escalares y documentarlo.
- **IN-02** — Código para `genero_id` inexistente. Propuesta: 409, por coherencia con la FK.
- **IN-03** — Cuerpo exacto de `/health/ready`. Propuesta: decidir uno (`{"estado": "listo", "base": "ok"}`) y mantenerlo.
- **IN-04** — Cantidad exacta de consultas esperada en C-07. Propuesta: registrar el mismo número con 1 y con 3 autores/renglones en `evidencia/`.
- **IN-05** — Formato de `fecha`. Propuesta: `DateTime(timezone=True)` en UTC, serializado ISO 8601 con `Z`.
- **IN-06** — ¿`SQL_ECHO` es obligatoria? Propuesta: `false` por defecto en `config.py`, presente en `env.example`.

---

## Skills Disponibles

Fuente de verdad: `.atl/skill-registry.md`. Agrupadas por el plan de 3 agentes de `CHANGES.md`.

| Agente | Rol | Changes | Skills que carga |
|--------|-----|---------|------------------|
| **Agente A** | Backend núcleo: API, modelos, servicios, asincronía | C-01, C-02, C-03, C-04, C-06, C-07 | `fastapi`, `sqlmodel`, `fastapi-templates`, `async-python-patterns`, `tdd` |
| **Agente B** | Datos y calidad: esquema, seed, pruebas, evidencia | C-05, C-10 | `postgresql-table-design`, `postgresql-optimization`, `supabase-postgres-best-practices`, `python-testing-patterns`, `test-driven-development` |
| **Agente C** | Infra y entrega: imagen, VPS, entrega | C-08, C-09, C-11 | `security-and-hardening`, `postgresql-optimization` |
| **Orquestación** | SDD / OPSX / workflow de changes | todos | `openspec-explore`, `openspec-propose`, `openspec-update-change`, `openspec-apply-change`, `openspec-verify-change`, `openspec-sync-specs`, `openspec-archive-change` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo).

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 11 changes en 10 gates (GATE 0 a GATE 9).
- **Camino crítico** (10): `C-01 → C-02 → C-03 → C-04 → C-06 → C-07 → C-08 → C-09 → C-10 → C-11`.
- **Primer change**: `C-01` (`proyecto-conexion-lifespan`).

**Árbol de dependencias** (con peso de corrección):

```
C-01  proyecto-conexion-lifespan        Ej.1 · 8%
 └─ C-02 modelos-restricciones-relaciones  Ej.2 · 22%
     └─ C-03 contratos-crud                Ej.3 · 12%
         └─ C-04 altas-con-relaciones       Ej.4 · 17%
             ├─ C-05 datos-iniciales-seed   higiene ──► C-09
             └─ C-06 lecturas-sin-n-plus-uno Ej.5 · 8%
                 └─ C-07 asincronia-sin-bloqueos Ej.6 · 8%
                     └─ C-08 imagen-docker   Ej.7 · 15%
                         └─ C-09 despliegue-vps Ej.8 · 10%
                             └─ C-10 casos-prueba-evidencia higiene
                                 └─ C-11 readme-entrega          higiene
```

**Gates de paralelismo** (un gate es un punto de sincronización; dentro de un gate se puede paralelizar):

- **GATE 0** → C-01 [A]. **GATE 1**: C-01 ✓ → C-02 [A]. **GATE 2**: C-02 ✓ → C-03 [A]. **GATE 3**: C-03 ✓ → C-04 [A].
- **GATE 4**: C-04 ✓ (primer fork) → C-05 [B], C-06 [A], C-08 borrador [C — no cierra hasta C-07 ✓].
- **GATE 5**: C-05 + C-06 ✓ → C-07 [A], C-10 borrador (.http C-01…C-08) [B].
- **GATE 6**: C-07 ✓ → C-08 build y verificación [C]. **GATE 7**: C-08 + C-05 ✓ → C-09 [C].
- **GATE 8**: C-09 ✓ → C-10 cierre [B]. **GATE 9**: C-10 ✓ → C-11 [C].

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

Para arrancar: `/opsx:propose proyecto-conexion-lifespan`

---

## Reglas Duras (específicas del proyecto)

Reglas específicas de este proyecto. No existe `~/.claude/CLAUDE.md` global, así que las reglas universales (orquestador, governance, TDD, engram) que apliquen quedan escritas acá.

Son contrato: romperlas es un defecto.

### A. Datos y dinero

1. NUNCA `float` para dinero → `Numeric(10,2)` en DB, `Decimal` en Python, string decimal (`"25000.00"`) al serializar.
2. NUNCA renombrar ni quitar tablas/columnas → nombres obligatorios, solo se agregan columnas.
3. NUNCA carga perezosa → toda relación leída se precarga (`joinedload`/`selectinload`) en la misma consulta.
4. NUNCA Alembic ni migraciones → esquema con `SQLModel.metadata.create_all` en el `lifespan`.

### B. API y errores

5. `IntegrityError` por UNIQUE/FK repetido → **409** con mensaje propio mapeado por nombre de constraint; nunca 500.
6. **404** solo lecturas/`PATCH` de recurso inexistente; **422** solo contrato/query inválida.
7. NUNCA devolver `str(exc)`, nombres de constraints ni trazas (RN-12).
8. NUNCA endpoints fuera de la matriz de `11_contratos_api.md` (sin `DELETE` no listados; ventas sin `PATCH`/`PUT`).

### C. Asincronía

9. Todos los handlers `async def`; NUNCA `time.sleep`, `requests`, `httpx` sync ni acceso sync a la DB.
10. Aviso de comprobante con `BackgroundTasks` + `asyncio.sleep`, sin la sesión del request, con logger a stdout.

### D. Higiene

11. `snake_case`, type hints en funciones públicas, cero credenciales en código/repo/imagen/`.zip`.
12. Tests con `pytest` + `httpx`; los `.http` de `test/` complementan, no reemplazan.
13. Respetar el governance de cada change en `CHANGES.md` (C-02 CRÍTICO, C-04/C-08/C-09 ALTO → proponer y esperar OK).

---

## Flujo de Trabajo

```
knowledge-base/ (contrato)  → entender el dominio
CHANGES.md (orden y gates)  → verificar dependencias archivadas y "Leer antes"
/opsx:propose <change>      → proposal + design + specs + tasks (en español; SHALL/MUST en inglés)
/opsx:apply                 → implementar tasks respetando las reglas duras
/opsx:verify                → contrastar implementación contra artefactos
/opsx:archive               → cerrar el change y marcar [x] en CHANGES.md
```

Reglas del flujo:

- **Un change por sesión**; no mezclar dos changes en la misma sesión.
- Antes de arrancar, verificar que las dependencias del change estén archivadas en `openspec/changes/archive/`. Si falta una, no arrancar.
- Los artefactos se escriben en español, con encabezados estructurales y `SHALL`/`MUST` en inglés.
- Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
