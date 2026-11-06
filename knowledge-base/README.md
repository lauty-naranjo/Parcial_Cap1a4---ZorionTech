# ZorionTech — Base de Conocimiento

Base de conocimiento generada a partir de `docs/consigna-parcial-cap1a4.md` (texto completo del PDF `Parcial_Cap1a4_Consigna.pdf`, 16 páginas).

**Proyecto**: API REST de librería — Parcial de Programación III, unidades 1 a 4 + despliegue en VPS.
**Stack**: Python 3.12 · FastAPI · SQLModel · SQLAlchemy async · asyncpg · PostgreSQL 16 · Docker (Alpine).

## Índice de Archivos

| Archivo | Contenido |
|---|---|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, 5 actores, alcance de la entrega, fuera de alcance, métricas |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack con versiones, arquitectura general, integraciones, resumen de API |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, ausencia de RBAC, rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | 8 tablas con columnas obligatorias, ERD, relaciones y justificación del lado de cada FK, índices, seed |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | RN-01 a RN-12, reglas de integridad (RI-01…05), reglas globales y matriz regla → caso |
| [06_funcionalidades.md](06_funcionalidades.md) | 5 épicas y 20 historias de usuario con criterios de aceptación |
| [07_flujos_principales.md](07_flujos_principales.md) | 7 flujos extremo a extremo (arranque, alta de libro, alta de venta, lectura sin N+1, perfil, healthchecks, actualización) |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, estructura de directorios obligatoria, capa de datos, seguridad, variables de entorno |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | 10 decisiones (DD) y 8 supuestos (SU) con trade-offs y riesgo |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | 6 ambigüedades + 11 preguntas priorizadas |
| [11_contratos_api.md](11_contratos_api.md) | Matriz completa de endpoints, DTOs, ejemplos, errores y casos C/D |
| [12_devops_y_despliegue.md](12_devops_y_despliegue.md) | Dockerfile, `.dockerignore`, `docker run`, healthcheck, `DEPLOY.md`, evidencia, checklist de entrega |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos (nombres obligatorios) → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md), [11](11_contratos_api.md)
6. Empaquetar y desplegar → [12](12_devops_y_despliegue.md)
7. Antes de codificar → [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

API asincrónica de catálogo y ventas para una librería de barrio, construida con FastAPI + SQLModel sobre PostgreSQL 16. El modelo de datos está diseñado para ejercitar todas las relaciones del capítulo 4: agregación (libro–editorial), agregación opcional (libro–género), muchos a muchos con datos (libro–autor vía `libro_autor`), uno a uno (cliente–perfil), asociación (venta–cliente, renglón–libro) y composición (venta–renglón). La entrega incluye imagen Docker Alpine sin secretos, despliegue documentado en un VPS, `env.example`, pruebas `.http` y evidencia.

**Riesgos principales**: el despliegue (25 puntos) depende de datos de acceso que provee la cátedra; `localhost` dentro del contenedor y el IPv6 del healthcheck son las dos trampas clásicas; el historial de Git se revisa si se incluye `.git`.
