"""Prueba unitaria del contador de consultas (helper de C-06)."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from contador_consultas import contador_consultas


async def test_contador_cuenta_una_consulta_conocida(motor_bd):
    """Una sola ejecución de ``SELECT 1`` se registra exactamente una vez."""
    fabrica = async_sessionmaker(motor_bd, expire_on_commit=False)

    with contador_consultas(motor_bd) as cuenta:
        async with fabrica() as sesion:
            await sesion.execute(text("SELECT 1"))

    assert cuenta.total == 1
    assert "SELECT 1" in cuenta.consultas[0]


async def test_contador_ignora_consultas_fuera_del_bloque(motor_bd):
    """Las ejecuciones previas a entrar al bloque no se cuentan."""
    fabrica = async_sessionmaker(motor_bd, expire_on_commit=False)

    async with fabrica() as sesion:
        await sesion.execute(text("SELECT 1"))

    with contador_consultas(motor_bd) as cuenta:
        async with fabrica() as sesion:
            await sesion.execute(text("SELECT 1"))
            await sesion.execute(text("SELECT 2"))

    assert cuenta.total == 2
