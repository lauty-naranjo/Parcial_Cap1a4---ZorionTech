# Spec Delta

## Purpose

Define cómo la API se pone en línea en el VPS de la cátedra sobre la imagen ya verificada: configuración fuera del repositorio, conexión a la base del servidor, carga inicial de datos, verificación pública, reinicio sin pérdida de datos y documentación de despliegue y actualización.

## ADDED Requirements

### Requirement: Servicio en línea en la URL declarada

La aplicación SHALL quedar corriendo en el VPS en un contenedor publicado en el puerto asignado y accesible desde fuera del servidor. `GET /health/ready` MUST responder 200 con `{"estado": "listo", "base": "ok"}` sobre esa URL pública. El despliegue SHALL permanecer en línea hasta que se publiquen las notas.

#### Scenario: Healthcheck público

- **WHEN** se solicita `GET /health/ready` contra la URL pública declarada en `DEPLOY.md` desde una máquina fuera del VPS
- **THEN** la respuesta es 200 con `{"estado": "listo", "base": "ok"}`

#### Scenario: Puerto publicado correcto

- **WHEN** se ejecuta `docker ps` en el VPS
- **THEN** el contenedor `libreria-zoriontech` figura en estado `healthy` y publica el puerto asignado hacia el 8000 del contenedor

### Requirement: Imagen construida en el servidor

El camino principal SHALL ser construir la imagen en el VPS con `docker build -t libreria-zoriontech .` y correrla allí, sin depender de transferir imágenes entre máquinas. El proyecto SHALL documentar `docker save` + `docker load` como plan alternativo si el servidor no puede construir.

#### Scenario: Build en un servidor limpio

- **WHEN** se ejecuta `docker build -t libreria-zoriontech .` en el VPS sobre el código transferido
- **THEN** el build termina con código 0 y no requiere imágenes previas ni archivos del entorno de desarrollo

#### Scenario: Plan alternativo documentado

- **WHEN** el VPS no puede construir la imagen por recursos o por falta del código fuente
- **THEN** `DEPLOY.md` describe cómo transferirla con `docker save` local y `docker load` en el servidor, y el camino elegido queda registrado

### Requirement: Configuración por archivo de variables fuera del repositorio

La configuración SHALL entrar al contenedor con `--env-file`. El archivo de variables SHALL vivir en el servidor, fuera del repositorio, de la imagen y del `.zip`, con permisos `600`, y MUST contener `DATABASE_URL` con esquema `postgresql+asyncpg://` y `SQL_ECHO=false`. Ni `DEPLOY.md` ni la evidencia MUST incluir su contenido, usuario, contraseña o host reales.

#### Scenario: Archivo de variables restringido

- **WHEN** se inspecciona el archivo de variables en el VPS con `ls -l`
- **THEN** sus permisos son `600` y no está dentro del directorio del repositorio

#### Scenario: Sin credenciales en la documentación

- **WHEN** se revisan `DEPLOY.md`, `README.md` y `evidencia/` en busca de usuarios, contraseñas, hosts o cadenas de conexión reales
- **THEN** solo aparecen el nombre del archivo de variables y valores de ejemplo

#### Scenario: Arranque sin configuración

- **WHEN** el contenedor se corre sin `--env-file`
- **THEN** no queda sirviendo y termina con código distinto de 0

### Requirement: Conexión a la base del servidor sin localhost

Dentro del contenedor, `DATABASE_URL` MUST NOT usar `localhost` ni `127.0.0.1` para llegar a PostgreSQL. Si la base corre en el host del VPS, el contenedor SHALL arrancar con `--add-host=host.docker.internal:host-gateway` y la URL SHALL usar `host.docker.internal`. Si la cátedra provee otra dirección, SHALL usarse esa.

#### Scenario: Base en el host del VPS

- **WHEN** PostgreSQL corre en el host y el contenedor se inicia con `--add-host=host.docker.internal:host-gateway`
- **THEN** `/health/ready` responde 200 y los endpoints con datos funcionan

#### Scenario: Dirección provista por la cátedra

- **WHEN** la cátedra entrega un host de base distinto del host del contenedor
- **THEN** `DATABASE_URL` usa esa dirección y el arranque verifica la conexión con `/health/ready`

### Requirement: Carga inicial de datos en el servidor

La base del VPS SHALL poblarse ejecutando el seed dentro del contenedor con `docker exec libreria-zoriontech python -m app.seed`. El comando SHALL terminar con código 0 y dejar los datos iniciales esperados; al re-ejecutarse MUST NOT duplicar filas.

#### Scenario: Seed dentro del contenedor

- **WHEN** se ejecuta `docker exec libreria-zoriontech python -m app.seed` en el VPS
- **THEN** el comando termina con código 0 y `GET /libros/` devuelve los libros del seed

#### Scenario: Seed repetido

- **WHEN** el seed se ejecuta por segunda vez sobre la misma base
- **THEN** los conteos no cambian y no se producen errores de unicidad

### Requirement: Verificación pública de lectura y alta de venta

Desde fuera del VPS SHALL verificarse `GET /libros/` con los datos iniciales y `POST /ventas/` con el cuerpo del caso C-06. La venta SHALL responder 201 con los precios copiados de cada libro y `total` igual a `"77000.00"` (D-03). Los comandos y sus salidas SHALL guardarse en `evidencia/`.

#### Scenario: Listado público con datos del seed

- **WHEN** se solicita `GET /libros/` contra la URL pública después del seed
- **THEN** la respuesta es 200 e incluye los libros cargados, entre ellos `Rayuela` y `Respiración artificial`

#### Scenario: Venta pública con dos renglones

- **WHEN** se envía `POST /ventas/` con `cliente_id` 2 y los renglones de los libros 1 y 4 del seed
- **THEN** la respuesta es 201 con `precio_unitario` copiado en cada renglón y `total` `"77000.00"`

### Requirement: Reinicio sin pérdida de datos

Eliminar y volver a crear el contenedor con el mismo `docker run` SHALL devolverlo a `healthy` y MUST conservar los datos, porque la base vive en el servidor y `create_all` solo crea tablas faltantes (D-04).

#### Scenario: Recreación del contenedor

- **WHEN** se ejecuta `docker rm -f libreria-zoriontech` y el mismo `docker run` con el mismo `--env-file`
- **THEN** `docker ps` vuelve a mostrar `healthy` y `GET /libros/` conserva los libros cargados

### Requirement: Aviso del comprobante en los logs del servidor

Después de registrar una venta, `docker logs libreria-zoriontech` SHALL mostrar el aviso del comprobante en segundo plano con el id de venta, el email y el total, en una línea posterior a la de la respuesta (D-07).

#### Scenario: Aviso tras la venta pública

- **WHEN** se ejecuta `docker logs libreria-zoriontech` después del `POST /ventas/` de D-03
- **THEN** aparece el aviso del comprobante con el id de la venta y el total, sin bloquear la respuesta

### Requirement: DEPLOY.md completo y sin secretos

`DEPLOY.md` SHALL incluir la URL pública, el día y la hora del despliegue, los comandos `docker build` y `docker run` completos con el nombre del archivo de variables y sin su contenido, los cambios hechos para que el proyecto corra en el contenedor, el procedimiento de actualización (build → `docker rm -f` → `docker run`) y la limitación de `create_all` sobre tablas existentes.

#### Scenario: Documento utilizable por un tercero

- **WHEN** otra persona lee `DEPLOY.md` con los datos de acceso y el archivo de variables
- **THEN** puede construir, correr, cargar datos, verificar y actualizar el despliegue siguiendo solo ese documento

#### Scenario: Actualización documentada

- **WHEN** se publica una nueva versión del código
- **THEN** el procedimiento indicado reconstruye la imagen, elimina el contenedor y lo vuelve a correr, y los datos siguen en la base del servidor

### Requirement: Evidencia verificable de los casos D en el VPS

La evidencia de D-03 y D-04 SHALL contener la salida real de los comandos ejecutados en el servidor. Mientras falten los datos de acceso, los archivos SHALL declarar `ESTADO: PENDIENTE (C-09)` con el comando y el criterio, y MUST NOT contener salidas inventadas. D-01, D-02, D-05, D-06 y D-07 SHALL regenerarse en el VPS o conservarse los locales indicando la diferencia de entorno.

#### Scenario: Sin datos del VPS

- **WHEN** todavía no se recibieron host, usuario, puerto ni `DATABASE_URL`
- **THEN** la evidencia de D-03 y D-04 queda como plantilla `PENDIENTE`, con el script que la produce y su criterio de aceptación

#### Scenario: Con datos del VPS

- **WHEN** el servidor está disponible y se ejecuta la verificación
- **THEN** `D-03-endpoints-publicos.txt` y `D-04-restart.txt` contienen la salida real, con fecha y comandos

### Requirement: Parámetros del servidor sin valores inventados

Host/IP, puerto SSH, usuario, método de acceso, puerto público y datos de PostgreSQL SHALL tratarse como parámetros provistos por la cátedra. El proyecto MUST NOT fijar valores por defecto inventados para ellos en scripts, documentación o evidencia.

#### Scenario: Parámetro faltante

- **WHEN** un script de despliegue se ejecuta sin uno de los datos requeridos
- **THEN** falla con un mensaje que nombra el parámetro faltante y no intenta conectarse a un valor supuesto

#### Scenario: Valores de ejemplo distinguibles

- **WHEN** `DEPLOY.md` muestra un comando con puerto o archivo de variables
- **THEN** el valor es un marcador (`<puerto>`, `<archivo-de-variables>`) o un ejemplo explícitamente marcado como tal
