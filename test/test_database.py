"""Pruebas de la capa de datos asincrónica (D-01)."""

from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import build_engine, build_session_factory, get_session

URL = "postgresql+asyncpg://usuario:secreto@localhost:5432/libreria"


class _SesionFalsa:
    """Sesión mínima que registra si se cerró."""

    def __init__(self) -> None:
        self.cerrada = False


class _ContextoFalso:
    def __init__(self, sesion: _SesionFalsa) -> None:
        self._sesion = sesion

    async def __aenter__(self) -> _SesionFalsa:
        return self._sesion

    async def __aexit__(self, *exc_info: object) -> bool:
        self._sesion.cerrada = True
        return False


class _FabricaFalsa:
    """Fábrica de sesiones que devuelve una sesión nueva por llamada."""

    def __init__(self) -> None:
        self.creadas: list[_SesionFalsa] = []

    def __call__(self) -> _ContextoFalso:
        sesion = _SesionFalsa()
        self.creadas.append(sesion)
        return _ContextoFalso(sesion)


def _peticion_con(fabrica: _FabricaFalsa) -> SimpleNamespace:
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=fabrica)))


async def test_build_engine_crea_motor_asincronico_con_echo_apagado():
    motor = build_engine(Settings(database_url=URL, sql_echo=False))

    try:
        assert motor.dialect.is_async is True
        assert motor.url.drivername == "postgresql+asyncpg"
        assert motor.echo is False
    finally:
        await motor.dispose()


async def test_build_engine_respeta_el_echo_activo():
    motor = build_engine(Settings(database_url=URL, sql_echo=True))

    try:
        assert motor.echo is True
    finally:
        await motor.dispose()


async def test_build_session_factory_no_expira_al_confirmar():
    motor = build_engine(Settings(database_url=URL, sql_echo=False))

    try:
        fabrica = build_session_factory(motor)
        async with fabrica() as sesion:
            assert isinstance(sesion, AsyncSession)
            assert sesion.sync_session.expire_on_commit is False
    finally:
        await motor.dispose()


async def test_get_session_entrega_la_sesion_de_app_state_y_la_cierra():
    fabrica = _FabricaFalsa()
    generador = get_session(_peticion_con(fabrica))

    sesion = await generador.__anext__()
    assert sesion is fabrica.creadas[0]
    assert sesion.cerrada is False

    await generador.aclose()
    assert sesion.cerrada is True


async def test_get_session_crea_una_sesion_distinta_por_peticion():
    fabrica = _FabricaFalsa()
    peticion = _peticion_con(fabrica)

    generador_uno = get_session(peticion)
    generador_dos = get_session(peticion)
    primera = await generador_uno.__anext__()
    segunda = await generador_dos.__anext__()

    await generador_uno.aclose()
    await generador_dos.aclose()

    assert primera is not segunda
    assert len(fabrica.creadas) == 2
    assert [sesion.cerrada for sesion in fabrica.creadas] == [True, True]
