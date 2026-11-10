"""Pruebas del arranque y apagado de la aplicación (D-07)."""

import pytest
from sqlmodel import SQLModel

from app.core.config import ConfigurationError
from app.main import create_app

URL = "postgresql+asyncpg://usuario:secreto@localhost:5432/libreria"


class _ConexionFalsa:
    def __init__(self) -> None:
        self.ejecutadas: list[object] = []

    async def run_sync(self, funcion: object) -> None:
        self.ejecutadas.append(funcion)


class _ContextoDeMotorFalso:
    def __init__(self, conexion: _ConexionFalsa) -> None:
        self._conexion = conexion

    async def __aenter__(self) -> _ConexionFalsa:
        return self._conexion

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


class _MotorFalso:
    def __init__(self) -> None:
        self.conexion = _ConexionFalsa()
        self.veces_que_abrio_transaccion = 0
        self.dispose_invocado = False

    def begin(self) -> _ContextoDeMotorFalso:
        self.veces_que_abrio_transaccion += 1
        return _ContextoDeMotorFalso(self.conexion)

    async def dispose(self) -> None:
        self.dispose_invocado = True


@pytest.fixture(autouse=True)
def entorno_aislado(tmp_path, monkeypatch):
    """Aísla cada prueba de un `.env` real y de variables heredadas."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)


def _sustituir_motor(monkeypatch, motor: _MotorFalso, fabrica: object) -> None:
    monkeypatch.setattr("app.main.build_engine", lambda settings: motor)
    monkeypatch.setattr("app.main.build_session_factory", lambda engine: fabrica)


async def test_lifespan_sin_database_url_falla_nombrando_la_variable():
    aplicacion = create_app()

    with pytest.raises(ConfigurationError) as excinfo:
        async with aplicacion.router.lifespan_context(aplicacion):
            pass

    assert "DATABASE_URL" in str(excinfo.value)


async def test_create_app_no_construye_el_motor_fuera_del_lifespan(monkeypatch):
    def _no_debe_llamarse(settings):
        raise AssertionError("build_engine no debe ejecutarse al crear la app")

    monkeypatch.setattr("app.main.build_engine", _no_debe_llamarse)

    create_app()


async def test_lifespan_publica_motor_y_fabrica_en_el_estado(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    motor = _MotorFalso()
    fabrica = object()
    _sustituir_motor(monkeypatch, motor, fabrica)
    aplicacion = create_app()

    async with aplicacion.router.lifespan_context(aplicacion):
        assert aplicacion.state.engine is motor
        assert aplicacion.state.session_factory is fabrica


async def test_lifespan_libera_el_motor_al_apagar(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    motor = _MotorFalso()
    _sustituir_motor(monkeypatch, motor, object())
    aplicacion = create_app()

    async with aplicacion.router.lifespan_context(aplicacion):
        assert motor.dispose_invocado is False

    assert motor.dispose_invocado is True


async def test_lifespan_crea_el_esquema_en_una_transaccion_del_motor(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    motor = _MotorFalso()
    _sustituir_motor(monkeypatch, motor, object())
    aplicacion = create_app()

    async with aplicacion.router.lifespan_context(aplicacion):
        pass

    assert motor.veces_que_abrio_transaccion == 1
    assert motor.conexion.ejecutadas == [SQLModel.metadata.create_all]
