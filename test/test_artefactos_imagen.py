"""Contrato estático de los artefactos de imagen (C-08), sin motor Docker.

Estos tests no construyen ni ejecutan la imagen: verifican el contenido de
``Dockerfile``, ``.dockerignore``, ``.gitignore`` y ``DEPLOY.md``. La
verificación con Docker real vive en ``scripts/verificar_imagen.sh`` y en
``evidencia/D-*.txt``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DOCKERFILE = RAIZ / "Dockerfile"
DOCKERIGNORE = RAIZ / ".dockerignore"
GITIGNORE = RAIZ / ".gitignore"
DEPLOY = RAIZ / "DEPLOY.md"


def _leer(ruta: Path) -> str:
    assert ruta.is_file(), f"falta el artefacto {ruta.name}"
    return ruta.read_text(encoding="utf-8")


def _instrucciones(texto: str) -> list[str]:
    """Instrucciones efectivas: sin vacías ni comentarios y con ``\\`` unidas."""
    unidas = texto.replace("\\\r\n", " ").replace("\\\n", " ")
    return [
        linea.strip()
        for linea in unidas.splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]


def _posicion(instrucciones: list[str], aguja: str) -> int:
    for indice, linea in enumerate(instrucciones):
        if aguja in linea:
            return indice
    pytest.fail(f"no se encontró {aguja!r} en el Dockerfile")


# --- Dockerfile -----------------------------------------------------------


def test_dockerfile_parte_de_python_alpine() -> None:
    instrucciones = _instrucciones(_leer(DOCKERFILE))
    assert instrucciones[0] == "FROM python:3.12-alpine"


def test_dockerfile_copia_e_instala_dependencias_antes_del_codigo() -> None:
    texto = _leer(DOCKERFILE)
    instrucciones = _instrucciones(texto)

    copia_requirements = _posicion(instrucciones, "COPY requirements.txt")
    instala = _posicion(instrucciones, "RUN pip install --no-cache-dir -r requirements.txt")
    copia_app = _posicion(instrucciones, "COPY app ./app")

    assert copia_requirements < instala < copia_app
    assert "COPY app ./app" in texto
    assert "COPY scripts" not in texto


def test_dockerfile_usa_usuario_sin_privilegios() -> None:
    texto = _leer(DOCKERFILE)
    assert "RUN adduser -D -H -u 1000 appuser" in texto
    assert "USER appuser" in texto
    # El usuario se activa después de crearlo.
    assert texto.index("RUN adduser") < texto.index("USER appuser")


def test_dockerfile_expone_8000_y_arranca_uvicorn_en_todas_las_interfaces() -> None:
    texto = _leer(DOCKERFILE)
    assert "EXPOSE 8000" in texto

    cmd = [linea for linea in _instrucciones(texto) if linea.startswith("CMD")]
    assert len(cmd) == 1, "debe haber una sola instrucción CMD"
    assert '"app.main:app"' in cmd[0]
    assert '"--host", "0.0.0.0"' in cmd[0]
    assert '"--port", "8000"' in cmd[0]


def test_dockerfile_tiene_un_solo_healthcheck_contra_ready_en_ipv4() -> None:
    texto = _leer(DOCKERFILE)
    healthchecks = [linea for linea in _instrucciones(texto) if linea.startswith("HEALTHCHECK")]

    assert len(healthchecks) == 1, "debe haber exactamente una instrucción HEALTHCHECK"
    unido = "\n".join(healthchecks)
    assert "http://127.0.0.1:8000/health/ready" in unido
    assert "--interval=30s" in unido
    assert "--timeout=5s" in unido
    assert "--start-period=10s" in unido
    assert "--retries=3" in unido
    assert "localhost" not in texto


def test_dockerfile_no_contiene_secretos_ni_cadenas_de_conexion() -> None:
    texto = _leer(DOCKERFILE)
    assert "DATABASE_URL" not in texto
    assert "postgresql://" not in texto
    assert "postgresql+asyncpg://" not in texto
    assert "SQL_ECHO" not in texto
    assert "ENV " not in texto, "la configuración entra por --env-file, no por ENV"


# --- .dockerignore --------------------------------------------------------

ENTRADAS_OBLIGATORIAS = [
    ".env",
    ".env.docker",
    ".venv",
    ".git",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "knowledge-base",
    "docs",
    "evidencia",
    "openspec",
    "test",
]


@pytest.mark.parametrize("entrada", ENTRADAS_OBLIGATORIAS)
def test_dockerignore_excluye_entradas_obligatorias(entrada: str) -> None:
    lineas = _instrucciones(_leer(DOCKERIGNORE))
    assert entrada in lineas


def test_dockerignore_no_excluye_el_codigo_ni_las_dependencias() -> None:
    lineas = _instrucciones(_leer(DOCKERIGNORE))
    prohibidas = {
        "app",
        "app/",
        "/app",
        "app/**",
        "**/app",
        "requirements.txt",
        "Dockerfile",
    }
    assert not (prohibidas & set(lineas))
    # Ninguna línea puede empezar por "app" (ni siquiera con comodines).
    assert not [linea for linea in lineas if linea.lstrip("/").startswith("app")]


def test_gitignore_excluye_el_archivo_de_entorno_del_contenedor() -> None:
    lineas = _instrucciones(_leer(GITIGNORE))
    assert ".env.docker" in lineas


# --- DEPLOY.md ------------------------------------------------------------

def test_deploy_documenta_build_run_healthcheck_y_seed() -> None:
    texto = _leer(DEPLOY)
    assert "docker build -t libreria ." in texto
    assert "docker run" in texto
    assert "--env-file" in texto
    assert "docker exec libreria python -m app.seed" in texto
    assert "http://127.0.0.1:8000/health/ready" in texto


def test_deploy_no_expone_credenciales_reales() -> None:
    texto = _leer(DEPLOY)
    urls = re.findall(r"postgresql\+asyncpg://[^\s`\"']+", texto)
    assert urls, "DEPLOY.md debe mostrar la forma de la URL de ejemplo"

    for url in urls:
        assert url.startswith("postgresql+asyncpg://usuario:password@"), (
            f"DEPLOY.md contiene una URL con credenciales que no es de ejemplo: {url}"
        )
