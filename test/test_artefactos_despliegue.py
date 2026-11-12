"""Contrato estático de los artefactos de despliegue en el VPS (C-09).

Estos tests no tocan el servidor ni ejecutan Docker: verifican el contenido de
``DEPLOY.md``, ``README.md``, los tres scripts de despliegue y las plantillas de
evidencia. La ejecución real vive en ``scripts/`` y en ``evidencia/``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DEPLOY = RAIZ / "DEPLOY.md"
README = RAIZ / "README.md"
GITIGNORE = RAIZ / ".gitignore"
DOCKERIGNORE = RAIZ / ".dockerignore"
SCRIPTS = RAIZ / "scripts"
EVIDENCIA = RAIZ / "evidencia"

DESPLEGAR = SCRIPTS / "desplegar_vps.sh"
VERIFICAR_PUBLICO = SCRIPTS / "verificar_publico.sh"
VERIFICAR_DESPLIEGUE = SCRIPTS / "verificar_despliegue.sh"
D03 = EVIDENCIA / "D-03-endpoints-publicos.txt"
D04 = EVIDENCIA / "D-04-restart.txt"
D07 = EVIDENCIA / "D-07-background.txt"

SCRIPTS_BASH = [DESPLEGAR, VERIFICAR_PUBLICO, VERIFICAR_DESPLIEGUE]

VARIABLES_DESPLIEGUE = [
    "IMAGEN",
    "CONTENEDOR",
    "PUERTO_PUBLICO",
    "HOST_BD",
    "NOMBRE_BD",
    "USUARIO_BD",
    "PASSWORD_BD",
    "ARCHIVO_ENV",
]

URL_EJEMPLO = "postgresql+asyncpg://usuario:password@"


def _leer(ruta: Path) -> str:
    assert ruta.is_file(), f"falta el artefacto {ruta.name}"
    return ruta.read_text(encoding="utf-8")


def _urls_bd(texto: str) -> list[str]:
    return re.findall(r"postgresql\+asyncpg://[^\s`\"'()]+", texto)


# --- DEPLOY.md: secciones obligatorias ------------------------------------


def test_deploy_declara_url_publica_y_fecha_reales() -> None:
    texto = _leer(DEPLOY)
    assert "http://46.202.151.202:8000" in texto
    assert "2026-11-12T17:26:00Z" in texto
    assert "46.202.151.202" in texto
    assert "libreria-zoriontech" in texto


def test_deploy_incluye_build_y_run_completos_del_vps() -> None:
    texto = _leer(DEPLOY)
    assert "docker build -t libreria-zoriontech ." in texto
    assert "--env-file /root/libreria-zoriontech.env" in texto
    assert "--restart unless-stopped" in texto
    assert "-p 8000:8000" in texto
    assert "docker run -d --name libreria-zoriontech" in texto
    assert "--network libreria-zoriontech-net" in texto


def test_deploy_documenta_el_plan_b_de_transferencia_de_imagen() -> None:
    texto = _leer(DEPLOY)
    assert "docker save" in texto
    assert "docker load" in texto
    assert "ssh" in texto
    assert "gzip" in texto
    assert "servidor limpio" in texto.lower()


def test_deploy_documenta_la_transferencia_del_codigo() -> None:
    texto = _leer(DEPLOY)
    assert "git clone" in texto
    assert "rsync" in texto
    for exclusion in (".venv", ".git", ".env", ".env.docker", "__pycache__"):
        assert exclusion in texto, f"falta documentar la exclusión {exclusion}"
    assert "scp" in texto


def test_deploy_documenta_el_archivo_de_variables_del_servidor() -> None:
    texto = _leer(DEPLOY)
    assert "install -m 600 /dev/null libreria-zoriontech.env" in texto
    assert "chmod 600 libreria-zoriontech.env" in texto
    assert "SQL_ECHO=false" in texto
    assert "percent-encoding" in texto
    assert ".env.docker" in texto, "debe distinguir el archivo local del del servidor"
    assert "fuera del repositorio" in texto.lower()


def test_deploy_documenta_la_regla_de_red() -> None:
    texto = _leer(DEPLOY)
    assert "--add-host=host.docker.internal:host-gateway" in texto
    assert "host.docker.internal" in texto
    assert "localhost" in texto
    assert "prohibido" in texto.lower()


def test_deploy_deja_claro_el_orden_d03_d07_d04() -> None:
    texto = _leer(DEPLOY)
    assert "D-03 → D-07 → D-04" in texto
    assert "borra los logs" in texto.lower() or "reiniciar antes" in texto.lower()


def test_deploy_documenta_la_limitacion_de_create_all() -> None:
    texto = _leer(DEPLOY)
    assert "create_all" in texto
    assert "DD-06" in texto
    assert "no altera" in texto.lower()


def test_deploy_menciona_la_regeneracion_de_evidencia_con_el_script() -> None:
    texto = _leer(DEPLOY)
    assert "scripts/verificar_imagen.sh" in texto
    for caso in ("D-01", "D-02", "D-05", "D-06"):
        assert caso in texto


# --- DEPLOY.md: sin credenciales ni contenido de un env-file ---------------


def test_deploy_no_expone_credenciales_reales() -> None:
    texto = _leer(DEPLOY)
    urls = _urls_bd(texto)
    assert urls, "DEPLOY.md debe mostrar la forma de ejemplo de la URL"
    for url in urls:
        assert url.startswith(URL_EJEMPLO), (
            f"DEPLOY.md contiene una URL que no es de ejemplo: {url}"
        )


def test_deploy_no_incluye_el_contenido_de_un_env_file() -> None:
    texto = _leer(DEPLOY)
    for numero, linea in enumerate(texto.splitlines(), start=1):
        limpia = linea.strip()
        if limpia.startswith("DATABASE_URL="):
            assert limpia.startswith(f"DATABASE_URL={URL_EJEMPLO}"), (
                f"DEPLOY.md:{numero} parece contener una URL real"
            )
        assert not re.match(r"^PASSWORD_BD=\S+", limpia), (
            f"DEPLOY.md:{numero} asigna una contraseña"
        )
    assert "PGPASSWORD=" not in texto
    assert "postgres://" not in texto


def test_deploy_no_deja_los_datos_del_vps_como_pendientes() -> None:
    texto = _leer(DEPLOY)
    assert "http://46.202.151.202:8000" in texto
    assert "(TBD)" not in texto, "los datos del VPS ya se conocen y se registraron"
    assert "Datos pendientes para el despliegue" not in texto


# --- README.md ------------------------------------------------------------


def test_readme_enlaza_el_documento_de_despliegue() -> None:
    texto = _leer(README)
    assert "[DEPLOY.md](DEPLOY.md)" in texto
    assert "http://46.202.151.202:8000" in texto
    assert "libreria-zoriontech" in texto
    assert "<IP_VPS>" not in texto and "<PUERTO_PUBLICO>" not in texto
    for url in _urls_bd(texto):
        assert url.startswith(URL_EJEMPLO)


# --- Scripts: forma general -----------------------------------------------


@pytest.mark.parametrize("script", SCRIPTS_BASH, ids=lambda ruta: ruta.name)
def test_script_existe_y_tiene_cabecera_bash(script: Path) -> None:
    texto = _leer(script)
    assert texto.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in texto


@pytest.mark.parametrize("script", SCRIPTS_BASH, ids=lambda ruta: ruta.name)
def test_script_usa_finales_de_linea_lf(script: Path) -> None:
    crudo = script.read_bytes()
    assert b"\r\n" not in crudo, f"{script.name} tiene CRLF; debe quedar en LF"


@pytest.mark.parametrize("script", SCRIPTS_BASH, ids=lambda ruta: ruta.name)
def test_script_bash_tiene_sintaxis_valida_si_hay_interprete(script: Path) -> None:
    if os.name == "nt":  # El Windows del curso no trae un bash funcional.
        pytest.skip("sin bash funcional en Windows; se validan contenido y flags")
    interprete = shutil.which("bash") or shutil.which("sh")
    if not interprete:
        pytest.skip("no hay bash ni sh disponibles")
    resultado = subprocess.run(
        [interprete, "-n", str(script)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stderr


# --- scripts/desplegar_vps.sh ---------------------------------------------


@pytest.mark.parametrize("variable", VARIABLES_DESPLIEGUE)
def test_desplegar_exige_cada_variable_obligatoria(variable: str) -> None:
    texto = _leer(DESPLEGAR)
    assert variable in texto, f"el script no menciona {variable}"
    assert re.search(rf'\[ -n "\$\{{{variable}:-}}" \]', texto), (
        f"el script no valida que {variable} esté definida"
    )


def test_desplegar_falla_nombrando_la_variable_faltante() -> None:
    texto = _leer(DESPLEGAR)
    assert "faltan variables obligatorias" in texto.lower()
    assert "${faltantes[*]}" in texto
    assert "exit 1" in texto


@pytest.mark.parametrize(
    "script", [DESPLEGAR, VERIFICAR_DESPLIEGUE], ids=lambda ruta: ruta.name
)
def test_scripts_rechazan_los_contenedores_de_otro_grupo(script: Path) -> None:
    texto = _leer(script)
    assert re.search(r"libreria\|libreria-db", texto), (
        "debe negarse a usar los contenedores `libreria` y `libreria-db` ajenos"
    )
    assert "otro grupo" in texto


def test_desplegar_no_tiene_default_para_imagen_ni_contenedor() -> None:
    texto = _leer(DESPLEGAR)
    assert 'IMAGEN="${IMAGEN:-}"' in texto
    assert 'CONTENEDOR="${CONTENEDOR:-}"' in texto
    assert 'IMAGEN="${IMAGEN:-libreria}"' not in texto
    assert 'CONTENEDOR="${CONTENEDOR:-libreria}"' not in texto


def test_desplegar_rechaza_localhost_en_la_base() -> None:
    texto = _leer(DESPLEGAR)
    assert re.search(r"localhost\|127\.0\.0\.1", texto), (
        "el script debe rechazar localhost y 127.0.0.1 como host de base"
    )
    assert "apunta al propio contenedor" in texto


def test_desplegar_no_asume_host_ni_puerto() -> None:
    texto = _leer(DESPLEGAR)
    assert not re.search(r"^HOST_BD=", texto, re.MULTILINE)
    assert not re.search(r"^PUERTO_PUBLICO=", texto, re.MULTILINE)
    assert not re.search(r"^NOMBRE_BD=", texto, re.MULTILINE)


def test_desplegar_arma_el_run_con_los_flags_obligatorios() -> None:
    texto = _leer(DESPLEGAR)
    assert "--restart unless-stopped" in texto
    assert '--env-file "$ARCHIVO_ENV"' in texto
    assert '--name "$CONTENEDOR"' in texto
    assert "-p \"${PUERTO_PUBLICO}:8000\"" in texto
    assert "--add-host=host.docker.internal:host-gateway" in texto


def test_desplegar_soporta_dry_run() -> None:
    texto = _leer(DESPLEGAR)
    assert re.search(r'DRY_RUN:-0', texto)
    assert "DRY_RUN=1" in texto


def test_desplegar_verifica_permisos_600_del_env_file() -> None:
    texto = _leer(DESPLEGAR)
    assert "600" in texto
    assert "stat" in texto
    assert "permisos" in texto


def test_desplegar_espera_healthy_y_muestra_diagnostico() -> None:
    texto = _leer(DESPLEGAR)
    assert "State.Health.Status" in texto
    assert "healthy" in texto
    assert "docker logs" in texto


def test_desplegar_nunca_imprime_el_env_file_ni_la_password() -> None:
    texto = _leer(DESPLEGAR)
    assert 'cat "$ARCHIVO_ENV"' not in texto
    assert "cat $ARCHIVO_ENV" not in texto
    for linea in texto.splitlines():
        limpia = linea.strip()
        if limpia.startswith("#"):
            continue
        assert "echo" not in limpia or "PASSWORD_BD" not in limpia, (
            f"el script imprime la contraseña: {limpia}"
        )
        assert "echo" not in limpia or "url_bd" not in limpia, (
            f"el script imprime la URL de la base: {limpia}"
        )


# --- scripts/verificar_publico.sh -----------------------------------------


def test_verificar_publico_exige_url_y_rechaza_loopback() -> None:
    texto = _leer(VERIFICAR_PUBLICO)
    assert "URL_PUBLICA" in texto
    assert "falta URL_PUBLICA" in texto
    assert re.search(r"\*localhost\*", texto)
    assert "*127.0.0.1*" in texto
    assert "se niega" in texto.lower() or "no es una prueba pública" in texto.lower()


def test_verificar_publico_cubre_los_tres_endpoints_y_el_total() -> None:
    texto = _leer(VERIFICAR_PUBLICO)
    assert "/health/ready" in texto
    assert "/libros/" in texto
    assert "/ventas/" in texto
    assert "77000.00" in texto
    assert "25000.00" in texto
    assert "27000.00" in texto
    assert "D-03-endpoints-publicos.txt" in texto
    assert "ESTADO:" in texto


# --- scripts/verificar_despliegue.sh --------------------------------------


def test_verificar_despliegue_respeta_el_orden_y_no_reinicia_sin_confirmacion() -> None:
    texto = _leer(VERIFICAR_DESPLIEGUE)
    assert "D-03 → D-07 → D-04" in texto
    assert "CONFIRMAR_REINICIO" in texto
    assert 'CONFIRMAR_REINICIO:-0' in texto
    assert re.search(r'CONFIRMAR_REINICIO" != "1"', texto)


def test_verificar_despliegue_cubre_ps_id_logs_y_restart() -> None:
    texto = _leer(VERIFICAR_DESPLIEGUE)
    assert "docker ps" in texto
    assert 'docker exec "$CONTENEDOR" id' in texto
    assert "Aviso de comprobante enviado" in texto
    assert 'docker rm -f "$CONTENEDOR"' in texto
    assert '--env-file "$ARCHIVO_ENV" "$IMAGEN"' in texto
    assert '--network "$RED"' in texto
    assert "D-04-restart.txt" in texto


def test_verificar_despliegue_revalida_el_env_file_antes_de_reiniciar() -> None:
    texto = _leer(VERIFICAR_DESPLIEGUE)
    assert "ARCHIVO_ENV" in texto
    assert "600" in texto
    assert re.search(r"localhost\|127\.0\.0\.1", texto)


# --- Plantillas de evidencia ----------------------------------------------


@pytest.mark.parametrize("plantilla", [D03, D04], ids=["D-03", "D-04"])
def test_evidencia_declara_verificada(plantilla: Path) -> None:
    texto = _leer(plantilla)
    assert "ESTADO: VERIFICADO (2026-11-12" in texto
    assert "SALIDA REAL" in texto


@pytest.mark.parametrize("plantilla", [D03, D04], ids=["D-03", "D-04"])
def test_evidencia_no_conserva_marcadores_de_plantilla(plantilla: Path) -> None:
    texto = _leer(plantilla)
    assert "<IP_VPS>" not in texto
    assert "<PUERTO_PUBLICO>" not in texto
    assert "PENDIENTE" not in texto
    assert "(TBD)" not in texto


def test_d07_conserva_la_seccion_local_y_verifica_la_del_vps() -> None:
    texto = _leer(D07)
    assert "ESTADO: VERIFICADO (2026-11-12)" in texto
    assert "Aviso de comprobante enviado" in texto
    assert "=== VPS ===" in texto
    seccion = texto.split("=== VPS ===", 1)[1]
    assert "ESTADO: VERIFICADO" in seccion
    assert "46.202.151.202" in seccion
    assert "Aviso de comprobante enviado" in seccion
    assert "docker logs" in seccion


# --- Archivos de variables fuera del repositorio ---------------------------


def test_env_files_del_servidor_no_viven_en_el_repositorio() -> None:
    for nombre in ("libreria.env", "libreria-zoriontech.env"):
        assert not (RAIZ / nombre).exists(), (
            f"{nombre} es del servidor y nunca se guarda en el repositorio"
        )
    gitignore = _leer(GITIGNORE).splitlines()
    assert "libreria.env" in gitignore
    assert "libreria-zoriontech.env" in gitignore
    assert ".env.docker" in gitignore
    assert ".env" in gitignore
    dockerignore = _leer(DOCKERIGNORE).splitlines()
    assert ".env" in dockerignore
    assert ".env.docker" in dockerignore
    assert "libreria.env" in dockerignore
    assert "libreria-zoriontech.env" in dockerignore


def test_git_no_trackea_libreria_env_ni_env_docker() -> None:
    if shutil.which("git") is None:
        pytest.skip("git no disponible")
    resultado = subprocess.run(
        ["git", "ls-files"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stderr
    trackeados = set(resultado.stdout.splitlines())
    assert "libreria.env" not in trackeados
    assert ".env.docker" not in trackeados
    assert ".env" not in trackeados
