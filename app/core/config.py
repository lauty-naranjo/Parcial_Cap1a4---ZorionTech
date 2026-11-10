"""Configuración por entorno con fallo temprano.

La instancia de :class:`Settings` se construye una sola vez por proceso: el
``lifespan`` de la aplicación llama a :func:`get_settings` al arrancar, de modo
que una configuración inválida impide atender peticiones en lugar de fallar
más tarde, dentro de un handler (D-02, D-05).
"""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()

PREFIJO_URL = "postgresql+asyncpg://"

_VALORES_VERDADEROS = frozenset({"1", "true", "yes", "si", "sí", "on"})
_VALORES_FALSOS = frozenset({"0", "false", "no", "off", ""})


class ConfigurationError(RuntimeError):
    """Error de configuración que impide arrancar la aplicación."""


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable del proceso."""

    database_url: str
    sql_echo: bool


def _leer_database_url() -> str:
    """Devuelve la URL validada sin exponer su valor en los mensajes."""
    valor = os.environ.get("DATABASE_URL", "").strip()
    if not valor:
        raise ConfigurationError(
            "Falta la variable de entorno DATABASE_URL. "
            f"Definila con una URL que empiece con '{PREFIJO_URL}'."
        )
    if not valor.startswith(PREFIJO_URL):
        raise ConfigurationError(
            f"DATABASE_URL debe empezar con '{PREFIJO_URL}' para usar el driver "
            "asincrónico de PostgreSQL."
        )
    return valor


def _leer_sql_echo() -> bool:
    """Interpreta SQL_ECHO de forma estricta; ausente equivale a ``false``."""
    valor = os.environ.get("SQL_ECHO")
    if valor is None:
        return False

    normalizado = valor.strip().lower()
    if normalizado in _VALORES_VERDADEROS:
        return True
    if normalizado in _VALORES_FALSOS:
        return False
    raise ConfigurationError(
        f"SQL_ECHO tiene un valor no reconocido ({valor!r}). "
        "Usá true/false, 1/0, yes/no, on/off o si/sí."
    )


def get_settings() -> Settings:
    """Construye y valida la configuración leyendo el entorno actual."""
    return Settings(database_url=_leer_database_url(), sql_echo=_leer_sql_echo())
