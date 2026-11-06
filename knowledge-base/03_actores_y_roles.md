# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|---|---|---|
| Librero / administrador | Opera el catálogo y las ventas de la librería | Consume la API con archivos `.http`, `curl` o Swagger UI (`/docs`) |
| Cliente de la librería | Persona que compra; es una entidad del dominio, no un usuario autenticado | Sus datos se registran vía API; recibe el aviso de comprobante simulado en el log |
| Corrector / cátedra | Verifica el parcial | Ejecuta los casos C y D, revisa `DEPLOY.md`, `evidencia/` y el historial de Git |
| Equipo ZorionTech | Construye la aplicación y la despliega | Repositorio, `Dockerfile`, VPS |

## RBAC — Matriz de permisos

**No aplica.** La consigna excluye explícitamente autenticación y autorización (capítulo 5). No hay usuarios, tokens, sesiones ni roles de acceso. Todos los endpoints son anónimos desde el punto de vista de la API.

| Rol | Recurso | Permisos |
|---|---|---|
| (sin autenticación) | Todo el catálogo y las ventas | CRUD según la tabla de endpoints de referencia |

> El término "rol" en este proyecto designa otra cosa: la **función del autor respecto del libro** en `libro_autor.rol` (`autor`, `coautor`, `traductor`, `ilustrador`). No es un rol de seguridad.

## Rutas públicas

Todas las rutas son públicas:

- `/health/live`, `/health/ready`
- `/editoriales/*`, `/generos/*`, `/autores/*`, `/libros/*`, `/clientes/*`, `/ventas/*`
- `/docs`, `/redoc`, `/openapi.json` (generadas por FastAPI)

## Distinción importante

| Concepto | Naturaleza |
|---|---|
| Rol de seguridad (RBAC) | Fuera de alcance |
| Rol de autoría (`rol` en `libro_autor`) | Dato de la relación muchos a muchos; restringido por CHECK a los cuatro valores permitidos |
| Actor del dominio (`cliente`) | Entidad persistida, con perfil uno a uno y ventas asociadas |
