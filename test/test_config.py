"""Pruebas de la configuración por entorno (D-02, D-03, D-04, D-05)."""

from pathlib import Path

import pytest

from app.core.config import ConfigurationError, get_settings

URL_VALIDA = "postgresql+asyncpg://usuario:secreto@localhost:5432/libreria"
URL_ALTERNATIVA = "postgresql+asyncpg://otro:clave@127.0.0.1:6543/otra_base"


@pytest.fixture(autouse=True)
def entorno_aislado(tmp_path, monkeypatch):
    """Aísla cada prueba de un `.env` real y de variables heredadas."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQL_ECHO", raising=False)


def test_get_settings_sin_database_url_falla_nombrando_la_variable():
    with pytest.raises(ConfigurationError) as excinfo:
        get_settings()

    assert "DATABASE_URL" in str(excinfo.value)


def test_get_settings_con_database_url_vacia_falla_nombrando_la_variable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")

    with pytest.raises(ConfigurationError) as excinfo:
        get_settings()

    assert "DATABASE_URL" in str(excinfo.value)


def test_get_settings_sin_sql_echo_deja_el_log_apagado(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL_VALIDA)

    settings = get_settings()

    assert settings.sql_echo is False
    assert settings.database_url == URL_VALIDA


@pytest.mark.parametrize("valor", ["true", "TRUE", "1", "yes", "si", "sí", "on"])
def test_get_settings_activa_el_log_con_valores_verdaderos(monkeypatch, valor):
    monkeypatch.setenv("DATABASE_URL", URL_VALIDA)
    monkeypatch.setenv("SQL_ECHO", valor)

    assert get_settings().sql_echo is True


@pytest.mark.parametrize("valor", ["false", "FALSE", "0", "no", "off", "", "  "])
def test_get_settings_apaga_el_log_con_valores_falsos(monkeypatch, valor):
    monkeypatch.setenv("DATABASE_URL", URL_VALIDA)
    monkeypatch.setenv("SQL_ECHO", valor)

    assert get_settings().sql_echo is False


@pytest.mark.parametrize("valor", ["quizas", "2", "activo"])
def test_get_settings_con_sql_echo_desconocido_falla(monkeypatch, valor):
    monkeypatch.setenv("DATABASE_URL", URL_VALIDA)
    monkeypatch.setenv("SQL_ECHO", valor)

    with pytest.raises(ConfigurationError) as excinfo:
        get_settings()

    assert "SQL_ECHO" in str(excinfo.value)


def test_get_settings_con_url_sin_driver_asincronico_falla_sin_filtrar_la_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://usuario:secreto@localhost:5432/libreria")

    with pytest.raises(ConfigurationError) as excinfo:
        get_settings()

    mensaje = str(excinfo.value)
    assert "postgresql+asyncpg://" in mensaje
    assert "secreto" not in mensaje


def test_get_settings_relee_el_entorno_en_cada_llamada(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL_VALIDA)
    assert get_settings().database_url == URL_VALIDA

    monkeypatch.setenv("DATABASE_URL", URL_ALTERNATIVA)
    assert get_settings().database_url == URL_ALTERNATIVA


def test_get_settings_acepta_los_valores_de_env_example(monkeypatch):
    valores = dict(
        linea.split("=", 1)
        for linea in (Path(__file__).resolve().parents[1] / "env.example").read_text(encoding="utf-8").splitlines()
        if "=" in linea and not linea.lstrip().startswith("#")
    )
    monkeypatch.setenv("DATABASE_URL", valores["DATABASE_URL"].strip())
    monkeypatch.setenv("SQL_ECHO", valores["SQL_ECHO"].strip())

    settings = get_settings()

    assert settings.database_url == "postgresql+asyncpg://usuario:password@host:5432/base"
    assert settings.sql_echo is False
