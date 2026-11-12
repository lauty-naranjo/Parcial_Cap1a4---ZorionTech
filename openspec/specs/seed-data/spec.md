# seed-data Specification

## Purpose

Deja una base de datos recién creada en un estado inicial conocido y reproducible, con los datos mínimos que los ejemplos y casos de la consigna referencian por id, de forma segura de re-ejecutar en local y dentro del contenedor.

## Requirements

### Requirement: Comando ejecutable de datos iniciales

El sistema SHALL exponer el comando `python -m app.seed`, que crea las tablas faltantes del esquema, abre una sesión sobre la base configurada, carga el conjunto inicial y libera el motor al terminar. El comando SHALL funcionar tanto en local como dentro del contenedor con `docker exec libreria python -m app.seed`.

#### Scenario: Ejecución sobre una base vacía

- **WHEN** se ejecuta `python -m app.seed` contra una base accesible sin tablas
- **THEN** el comando termina con código 0, crea el esquema, inserta los datos iniciales e informa los conteos por tabla

#### Scenario: Importación sin ejecución

- **WHEN** otro módulo importa `app.seed`
- **THEN** el seed no se ejecuta ni se imprime salida hasta invocar explícitamente el comando o su función

### Requirement: Contenido inicial compatible con los ejemplos

El seed SHALL dejar editorial id 1, género id 1, cuatro autores con ids 1 a 4, cuatro libros con ids 1 a 4, dos clientes con ids 1 y 2 y la venta id 2 con dos renglones. El libro id 1 SHALL ser «Rayuela» a `25000.00` y el id 4 «Respiración artificial» a `27000.00`; el cliente id 2 SHALL ser «Tomás Ríos» con `tomas@example.com`. Los importes SHALL ser `Decimal` y la fecha de la venta SHALL estar en UTC.

#### Scenario: Catálogo inicial

- **WHEN** se consulta `GET /libros/` después del seed
- **THEN** responde 200 con los cuatro libros, incluidos «Rayuela» (`25000.00`) y «Respiración artificial» (`27000.00`)

#### Scenario: Venta de ejemplo

- **WHEN** se consulta `GET /ventas/2` después del seed
- **THEN** responde 200 con total `77000.00` y dos renglones: Rayuela ×2 y Respiración artificial ×1

### Requirement: Idempotencia sin sobrescritura

Ejecutar el seed dos veces SHALL dejar los mismos conteos por tabla y MUST NOT modificar filas existentes ni duplicarlas. El seed MUST NOT borrar ni truncar datos: si una fila sembrada ya existe, conserva sus valores actuales.

#### Scenario: Segunda ejecución

- **WHEN** se ejecuta el seed por segunda vez sobre la misma base
- **THEN** los conteos de todas las tablas no cambian respecto de la primera ejecución

#### Scenario: Datos modificados preservados

- **WHEN** se modifica una fila sembrada y se vuelve a ejecutar el seed
- **THEN** la modificación se conserva y no se sobrescribe con el valor inicial

### Requirement: Secuencias alineadas tras ids explícitos

Después de insertar filas con ids explícitos, el seed SHALL reposicionar las secuencias de las tablas con clave primaria entera para que el siguiente id autogenerado sea mayor que el máximo sembrado. Una alta posterior por la API MUST NOT fallar por clave duplicada.

#### Scenario: Alta de libro después del seed

- **WHEN** se crea un libro por `POST /libros/` después del seed
- **THEN** responde 201 y el libro recibe un id nuevo, sin error de clave duplicada

#### Scenario: Alta de venta después del seed

- **WHEN** se registra una venta por `POST /ventas/` después del seed
- **THEN** responde 201 con ids nuevos de venta y renglones, sin error de clave duplicada

### Requirement: Configuración y salida sin credenciales

El seed SHALL obtener la cadena de conexión del entorno o del archivo `.env` del proyecto (`DATABASE_URL`), sin valor por defecto. Si falta, SHALL fallar con un mensaje claro que nombre la variable. El comando y sus mensajes MUST NOT imprimir la URL de conexión ni credenciales; solo pueden informar conteos y errores genéricos.

#### Scenario: Ejecución sin DATABASE_URL

- **WHEN** se ejecuta el seed sin `DATABASE_URL` en el entorno
- **THEN** termina con código distinto de 0 y un mensaje que menciona `DATABASE_URL`, sin mostrar la cadena de conexión

#### Scenario: Salida sin secretos

- **WHEN** el seed termina correctamente
- **THEN** su salida contiene los conteos por tabla y ninguna URL, usuario, contraseña ni host de la base

### Requirement: Documentación del comando

El `README.md` SHALL documentar el comando de seed para ejecución local y dentro del contenedor, e indicar que es idempotente y que requiere `DATABASE_URL`. El archivo del seed SHALL ubicarse dentro de `app/` para viajar en la imagen sin copias adicionales.

#### Scenario: Instrucciones presentes

- **WHEN** se revisa la sección de datos iniciales del `README.md`
- **THEN** incluye `python -m app.seed` y `docker exec libreria python -m app.seed`, la exigencia de `DATABASE_URL` y la advertencia de idempotencia
