# Spec Delta

## ADDED Requirements

### Requirement: Aviso de comprobante en segundo plano

Después de registrar una venta, el sistema SHALL agendar el aviso de comprobante como tarea en segundo plano y responder `201` sin esperar a que el aviso termine. El aviso SHALL completarse después de enviada la respuesta y SHALL dejar una línea de log con el id de la venta y el email del cliente.

#### Scenario: Respuesta 201 antes del aviso

- **WHEN** se registra una venta válida en `POST /ventas/`
- **THEN** el `201` se envía antes de que transcurra el tiempo del aviso, aunque la tarea de fondo siga pendiente

#### Scenario: Aviso registrado después de la respuesta

- **WHEN** el aviso de comprobante termina
- **THEN** el log contiene una línea con el id de la venta y el email del cliente, escrita después de enviada la respuesta

#### Scenario: El fallo o demora del aviso no altera la venta

- **WHEN** el aviso de comprobante se demora o falla después de la respuesta
- **THEN** la venta ya registrada y el `201` entregado no cambian, y no se abre una nueva transacción para el aviso

### Requirement: Aviso sin acceso a la base de la petición

El aviso de comprobante SHALL recibir solo datos escalares de la venta (`venta_id`, `email`, `total`) y MUST NOT usar la sesión de la petición ni ejecutar consultas, porque la sesión se cierra al responder.

#### Scenario: Aviso con la sesión ya cerrada

- **WHEN** el aviso se ejecuta después de que la petición terminó y su sesión se liberó
- **THEN** el aviso completa su trabajo sin tocar la base y sin errores por sesión cerrada
