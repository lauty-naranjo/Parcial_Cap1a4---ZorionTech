# Spec Delta

## Purpose

Define el contrato de los endpoints de salud que permiten a Docker y al corrector saber si el proceso está vivo y si puede atender tráfico real, sin exponer información interna del sistema.

## ADDED Requirements

### Requirement: Liveness independiente de la base de datos

`GET /health/live` SHALL responder 200 con el cuerpo exacto `{"estado": "vivo"}` sin abrir conexión ni consultar la base de datos. SHALL seguir respondiendo 200 aunque la base esté caída.

#### Scenario: Proceso vivo con base caída

- **WHEN** se invoca `GET /health/live` con la base de datos inalcanzable
- **THEN** responde 200 con `{"estado": "vivo"}`

### Requirement: Readiness con verificación de la base

`GET /health/ready` SHALL ejecutar `SELECT 1` contra la base de datos. Si la consulta responde, SHALL devolver 200 con el cuerpo exacto `{"estado": "listo", "base": "ok"}`.

#### Scenario: Base disponible

- **WHEN** se invoca `GET /health/ready` y la base de datos responde
- **THEN** responde 200 con `{"estado": "listo", "base": "ok"}`

### Requirement: Readiness degradado sin filtrar detalles internos

Si la verificación de la base falla, `GET /health/ready` SHALL devolver 503 con el cuerpo exacto `{"estado": "no_listo", "base": "error"}` y MUST NOT devolver 500, ni el mensaje de la excepción, ni nombres de tablas o restricciones, ni trazas. El detalle de la causa SHALL registrarse solo del lado del servidor.

#### Scenario: Base inalcanzable

- **WHEN** se invoca `GET /health/ready` y la base de datos no responde
- **THEN** responde 503 con `{"estado": "no_listo", "base": "error"}` y el cuerpo no contiene texto de la excepción ni identificadores internos

### Requirement: Cuerpos estables para consumidores automáticos

Ambos endpoints SHALL mantener el mismo cuerpo y el mismo código HTTP frente a consumidores automáticos como el `HEALTHCHECK` del contenedor, que decide exclusivamente por el código de respuesta. La ausencia de base de datos MUST NOT impedir que `/health/live` y la documentación de la API sigan disponibles.

#### Scenario: Healthcheck por código HTTP

- **WHEN** un consumidor evalúa `/health/ready` únicamente por su código de respuesta
- **THEN** obtiene 200 cuando la base responde y 503 cuando no, sin necesidad de interpretar el cuerpo
