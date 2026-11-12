# Proposal

## Why

La API está implementada, probada (405 passed + 3 skipped) y desplegada en
`http://46.202.151.202:8000`, pero el entregable todavía no está armado: el
`README.md` no identifica a los integrantes ni explica cómo correr los casos
`.http`, no existe el `.zip` con el contenido que enumera la consigna y nadie
verificó todavía que el paquete no arrastre secretos. Sin este cierre, el
corrector no puede reproducir el proyecto desde cero ni saber a quién
corresponde.

## What Changes

- Reemplazar `README.md` por la versión final de entrega: integrantes con
  nombres y apellidos, requisitos, creación del venv, instalación de
  dependencias, copia de `env.example` a `.env`, arranque local en Windows y
  Linux/macOS, seed idempotente, ejecución de los `.http` y de `pytest`, URL
  pública, despliegue y estructura del proyecto.
- Revisar `env.example` para que solo conserve la **forma** de `DATABASE_URL`
  (`usuario:password@host:5432/base`) y `SQL_ECHO=false`, sin usuario, clave,
  host reales ni la IP del VPS.
- Revisar `DEPLOY.md` contra la checklist de entrega de
  `knowledge-base/12_devops_y_despliegue.md`: URL, día y hora, comandos
  completos con el **nombre** del archivo de variables y sin su contenido,
  cambios hechos y procedimiento de actualización. No se agrega anexo de
  EasyPanel.
- Generar `Parcial_Cap1a4_ZorionTech.zip` desde una copia limpia, con una sola
  carpeta raíz `Parcial_Cap1a4_ZorionTech/` y exactamente el contenido pedido.
- Verificar antes y después de comprimir que no haya secretos en el paquete y
  que no estén los directorios excluidos.
- Sin cambios en `app/`, en el contrato HTTP, en los tests ni en `evidencia/`.

## Capabilities

### New Capabilities

- `delivery`: entregable reproducible y sin secretos — README de entrega con
  integrantes, plantilla de entorno sin valores reales, `DEPLOY.md` completo y
  paquete `.zip` con el contenido exacto.

### Modified Capabilities

- Ninguna. `vps-deployment` y `test-evidence` ya describen el despliegue y los
  casos; C-11 solo documenta y empaqueta lo verificado.

## Impact

- **Archivos modificados**: `README.md`; ajustes de redacción en `env.example`
  y `DEPLOY.md` solo si la checklist detecta faltantes.
- **Archivo generado**: `Parcial_Cap1a4_ZorionTech.zip` en la raíz del
  repositorio (ignorado por `.gitignore`).
- **Documentación interna**: `CHANGES.md` marca C-11 como cerrado.
- **Sin impacto en runtime**: no cambia `app/`, `Dockerfile`,
  `requirements*.txt`, `test/` ni la base de datos.
