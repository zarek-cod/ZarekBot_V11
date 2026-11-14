"""
CTX V11
Detector y configuración de FFmpeg.

Este módulo localiza FFmpeg de forma compatible con:

- Windows local
- Render / Linux
- Una ruta personalizada mediante FFMPEG_PATH

NO reproduce música.
NO conecta a Discord.
"""

import os
import shutil
from pathlib import Path

from config.settings import BASE_DIR


# ============================================================
# VARIABLE PERSONALIZADA
# ============================================================

FFMPEG_ENV_PATH = os.getenv(
    "FFMPEG_PATH",
    ""
).strip()


# ============================================================
# COMPROBAR ARCHIVO
# ============================================================

def _valid_file(
    path: str | Path | None
) -> bool:
    """
    Comprueba si una ruta existe
    y apunta a un archivo.
    """

    if not path:
        return False

    try:
        candidate = Path(path)

        return (
            candidate.exists()
            and candidate.is_file()
        )

    except (OSError, TypeError):
        return False


# ============================================================
# BUSCAR FFMPEG
# ============================================================

def resolve_ffmpeg_executable() -> str | None:
    """
    Busca FFmpeg siguiendo este orden:

    1. FFMPEG_PATH del entorno.
    2. ffmpeg instalado en el sistema.
    3. ffmpeg.exe dentro del proyecto.
    4. ffmpeg dentro del proyecto.
    """

    # --------------------------------------------------------
    # 1. RUTA PERSONALIZADA
    # --------------------------------------------------------

    if _valid_file(
        FFMPEG_ENV_PATH
    ):
        return str(
            Path(
                FFMPEG_ENV_PATH
            ).resolve()
        )


    # --------------------------------------------------------
    # 2. FFMPEG DEL SISTEMA
    # --------------------------------------------------------

    system_ffmpeg = shutil.which(
        "ffmpeg"
    )

    if system_ffmpeg:
        return system_ffmpeg


    # --------------------------------------------------------
    # 3. WINDOWS - FFMPEG.EXE DEL PROYECTO
    # --------------------------------------------------------

    local_windows = (
        BASE_DIR
        / "ffmpeg.exe"
    )

    if _valid_file(
        local_windows
    ):
        return str(
            local_windows.resolve()
        )


    # --------------------------------------------------------
    # 4. LINUX - FFMPEG LOCAL
    # --------------------------------------------------------

    local_linux = (
        BASE_DIR
        / "ffmpeg"
    )

    if _valid_file(
        local_linux
    ):
        return str(
            local_linux.resolve()
        )


    return None


# ============================================================
# ¿ESTÁ DISPONIBLE?
# ============================================================

def is_ffmpeg_available() -> bool:
    """
    Devuelve True si CTX encontró FFmpeg.
    """

    return (
        resolve_ffmpeg_executable()
        is not None
    )


# ============================================================
# OBTENER FFMPEG O FALLAR
# ============================================================

def require_ffmpeg() -> str:
    """
    Devuelve la ruta de FFmpeg.

    Si no existe, genera un error claro.
    """

    executable = (
        resolve_ffmpeg_executable()
    )


    if executable is None:

        raise RuntimeError(
            "CTX Music no encontró FFmpeg. "
            "Instala FFmpeg o configura FFMPEG_PATH."
        )


    return executable


# ============================================================
# RESUMEN SEGURO
# ============================================================

def get_ffmpeg_summary() -> dict:
    """
    Información útil para comprobar
    la configuración.
    """

    executable = (
        resolve_ffmpeg_executable()
    )


    if executable is None:

        source = "not_found"


    elif (
        FFMPEG_ENV_PATH
        and _valid_file(
            FFMPEG_ENV_PATH
        )
    ):

        source = "environment"


    elif shutil.which(
        "ffmpeg"
    ):

        source = "system"


    else:

        source = "project"


    return {

        "available":
            executable is not None,

        "source":
            source,

        "executable":
            executable,
    }