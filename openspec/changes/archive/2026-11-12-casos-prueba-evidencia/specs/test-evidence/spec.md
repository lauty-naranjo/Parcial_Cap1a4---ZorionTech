# Spec Delta

## Purpose

Define la entrega verificable del proyecto: los casos C-01…C-08 demostrados con archivos `.http` ejecutables, la suite de regresión que los respalda y la evidencia C-07/D-01…D-07 conservada y referenciada.

## ADDED Requirements

### Requirement: Casos C en archivos `.http` ejecutables

El proyecto SHALL incluir en `test/` los archivos `health.http`, `editoriales.http`, `generos.http`, `autores.http`, `libros.http`, `clientes.http`, `ventas.http` y `casos-C.http`. `casos-C.http` SHALL demostrar C-01, C-02, C-03, C-04, C-05, C-06 y C-08 con al menos un request cada uno.

#### Scenario: Cobertura completa de los casos C

- **WHEN** se recorre la unión de los bloques de los ocho archivos `.http`
- **THEN** aparecen los códigos C-01, C-02, C-03, C-04, C-05, C-06 y C-08, y C-07 está documentado como comando con su evidencia

#### Scenario: Archivos por módulo para el CRUD

- **WHEN** se abre el archivo de un módulo (por ejemplo `libros.http`)
- **THEN** sus bloques recorren las operaciones reales de ese módulo con el resultado esperado declarado, sin inventar endpoints fuera de la matriz

### Requirement: Cada request declara caso y resultado esperado

Cada bloque **con request** de un archivo `.http` SHALL declarar en comentarios el caso que demuestra (un código C-0N o D-xx cuando aplique, o `CRUD` para el soporte) y el resultado esperado con el código HTTP y el fragmento de respuesta relevante. C-07, que no es un request, SHALL documentarse como comando reproducible con su referencia a la evidencia.

#### Scenario: Request con expectativa declarada

- **WHEN** se lee cualquier bloque separado por `###`
- **THEN** incluye una línea `# Caso:` y una línea `# Esperado:` con el código HTTP y el fragmento que debe aparecer en el cuerpo

#### Scenario: Expectativa que no coincide con la realidad

- **WHEN** un bloque declara un código o un fragmento que la aplicación no devuelve
- **THEN** la suite de regresión falla señalando el archivo y el bloque, y el `.http` se corrige en lugar de relajar la expectativa

### Requirement: Formato portable y sin secretos

Los archivos `.http` SHALL usar una variable `@base` al inicio con el valor por defecto `http://localhost:8000`, separar los requests con `###` y MUST NOT contener credenciales, tokens ni cadenas de conexión reales.

#### Scenario: Ejecución en VS Code y JetBrains

- **WHEN** se abre un archivo `.http` con VS Code REST Client o JetBrains HTTP Client
- **THEN** todos los requests resuelven contra `@base` y se pueden ejecutar sin editar el archivo

#### Scenario: Revisión de secretos

- **WHEN** se buscan contraseñas, usuarios de base o `DATABASE_URL` dentro de `test/*.http`
- **THEN** no aparece ningún valor real

### Requirement: Verificación automática de los `.http`

La suite SHALL reejecutar cada bloque `.http` contra la aplicación ASGI con una base sembrada y SHALL comprobar que el código HTTP y el fragmento esperado coinciden con lo declarado.

#### Scenario: Replay de un bloque válido

- **WHEN** se ejecuta un bloque cuyo request es válido contra el estado sembrado
- **THEN** la respuesta real coincide con el código y el fragmento declarados en el comentario

#### Scenario: Estado inicial reproducible

- **WHEN** se reejecuta la misma suite dos veces
- **THEN** cada corrida parte de una base con el mismo estado inicial y los resultados no dependen de la corrida anterior

### Requirement: Suite de regresión que complementa los `.http`

La suite `pytest` + `httpx` SHALL cubrir al menos health, 404, 409 por unicidad y por clave foránea, `PATCH` parcial, paginación de toda colección, venta con renglones y número fijo de consultas. MUST NOT reemplazar los archivos `.http` ni duplicar pruebas ya existentes.

#### Scenario: Regresión de errores sin texto interno

- **WHEN** se provocan respuestas 409, 404 y 422 por HTTP
- **THEN** el cuerpo no contiene texto de PostgreSQL, nombres de constraints ni trazas, e incluye el mensaje propio esperado

#### Scenario: Regresión de importes

- **WHEN** una respuesta incluye `precio`, `precio_unitario`, `subtotal` o `total`
- **THEN** el valor es un string decimal con dos decimales y nunca un número JSON

### Requirement: Evidencia C-07 y D conservada

La carpeta `evidencia/` SHALL contener `C-07-consultas-libro.txt`, `C-07-consultas-venta.txt` y los archivos `D-01` a `D-07`, con salidas reales y los comandos usados. Este change MUST NOT reescribir ni inventar evidencia; solo verifica su presencia y contenido mínimo.

#### Scenario: Evidencia completa

- **WHEN** se enumeran los archivos de `evidencia/`
- **THEN** están los nueve archivos esperados y ninguno conserva marcadores de plantilla ni salidas inventadas

#### Scenario: C-07 referenciado desde los `.http`

- **WHEN** se busca el caso C-07 en `test/`
- **THEN** el comando con `SQL_ECHO=true` y las rutas `GET /libros/{id}` y `GET /ventas/{id}` están documentados y apuntan a los archivos de evidencia existentes
