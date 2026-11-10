"""Punto de entrada de la aplicación: fábrica, lifespan y routers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.modules.autores.router import router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router

# C-02 completará estos módulos con las nueve tablas del dominio. Los imports
# deben ejecutarse antes de `SQLModel.metadata.create_all` para que el esquema
# se cree completo; hoy solo aportan el docstring de cada archivo (D-05).
from app.modules.autores import models as _autores_models  # noqa: F401
from app.modules.clientes import models as _clientes_models  # noqa: F401
from app.modules.editoriales import models as _editoriales_models  # noqa: F401
from app.modules.generos import models as _generos_models  # noqa: F401
from app.modules.libros import models as _libros_models  # noqa: F401
from app.modules.ventas import models as _ventas_models  # noqa: F401


@asynccontextmanager
async def lifespan(aplicacion: FastAPI) -> AsyncIterator[None]:
    """Crea el motor y la fábrica al arrancar y libera el motor al apagar."""
    settings = get_settings()
    engine = build_engine(settings)
    aplicacion.state.engine = engine
    aplicacion.state.session_factory = build_session_factory(engine)
    try:
        async with engine.begin() as conexion:
            await conexion.run_sync(SQLModel.metadata.create_all)
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """Arma la aplicación; no abre conexiones hasta que corre el lifespan."""
    aplicacion = FastAPI(
        title="Librería de barrio",
        description="API de catálogo y ventas (Parcial Cap. 1 a 4).",
        version="0.1.0",
        lifespan=lifespan,
    )
    aplicacion.include_router(health_router)
    aplicacion.include_router(editoriales_router)
    aplicacion.include_router(generos_router)
    aplicacion.include_router(autores_router)
    aplicacion.include_router(clientes_router)
    aplicacion.include_router(libros_router)
    return aplicacion


app = create_app()
