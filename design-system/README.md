# Sistema de Diseño — ZorionTech

**Mode: off**
**Approval: skipped**
**Decisión:** 2026-11-06, por el usuario
**Fuente de la decisión:** elección explícita en la fase `design-system` del flujo `/active-orchestrator:init`.

## Motivo

El entregable del parcial es una **API REST** (FastAPI) con documentación automática en `/docs`
y un despliegue documentado en `DEPLOY.md`. La consigna no pide frontend, pantallas propias ni
identidad visual. Por lo tanto el proyecto **no define sistema visual ni mockups por change**.

## Qué implica

- No se crean `brand.md`, `brand.js`, `tokens.css`, `components.html`, `assets/` ni `previews/`.
- Ningún change futuro pide mockups: los agentes respetan esta política registrada en
  `.active-orchestrator-state.json` (`visual_design.mode = "off"`, `status = "skipped"`).
- Si en el futuro el proyecto incorpora una interfaz propia, el usuario debe pedir explícitamente
  el cambio de política (`/active-orchestrator:design`) y este archivo se reemplaza por el
  sistema visual correspondiente.
