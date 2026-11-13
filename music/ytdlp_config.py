"""
CTX V11
Configuración central de yt-dlp para YouTube.

Objetivos:
- usar cookies del navegador SOLO si el usuario lo habilita en .env
- reducir solicitudes agresivas a YouTube
- ocultar trazas enormes de yt-dlp y mostrar errores cortos en CTX
- reutilizar la misma configuración en PLAY y AUTOPLAY

.env opcional:
    YTDLP_BROWSER=chrome

Otros valores posibles habituales:
    firefox
    edge
    brave
    chromium

IMPORTANTE:
No exporta cookies a archivos. yt-dlp las lee directamente del navegador.
"""

from __future__ import annotations

import os


# ============================================================
# LOGGER SILENCIOSO
# ============================================================

class _CtxYtDlpLogger:
    def debug(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


YTDLP_LOGGER = _CtxYtDlpLogger()


# ============================================================
# NAVEGADOR / COOKIES
# ============================================================

def get_ytdlp_browser() -> str | None:
    """
    Devuelve el navegador configurado en .env.

    Ejemplo:
        YTDLP_BROWSER=chrome
    """

    browser = os.getenv(
        "YTDLP_BROWSER",
        "",
    ).strip().lower()

    if not browser:
        return None

    return browser


# ============================================================
# CONFIGURACIÓN BASE
# ============================================================

def build_ytdlp_options(
    *,
    flat: bool = False,
    audio: bool = False,
) -> dict:
    """
    Construye las opciones comunes de yt-dlp.

    flat=True:
        se usa para búsquedas rápidas de candidatos.

    audio=True:
        se usa cuando necesitamos un stream reproducible.
    """

    options: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "logger": YTDLP_LOGGER,
        "extract_flat": flat,

        # Evita insistir demasiado cuando YouTube está inestable.
        "retries": 2,
        "extractor_retries": 2,
        "socket_timeout": 20,

        # Pequeña separación entre solicitudes internas.
        "sleep_interval_requests": 0.75,
    }

    if audio:
        options["format"] = "bestaudio/best"

    browser = get_ytdlp_browser()

    if browser:
        # La API de yt-dlp espera una tupla.
        options["cookiesfrombrowser"] = (
            browser,
        )

    return options


# ============================================================
# DETECCIÓN ANTI-BOT / AUTENTICACIÓN
# ============================================================

ANTI_BOT_MARKERS = (
    "sign in to confirm you're not a bot",
    "sign in to confirm you’re not a bot",
    "use --cookies-from-browser",
    "use --cookies for the authentication",
    "login_required",
    "login required",
    "verificación anti-bot",
    "verificacion anti-bot",
    "rechazó temporalmente la extracción",
    "rechazo temporalmente la extraccion",
)


def is_youtube_antibot_error(
    error: BaseException | str,
) -> bool:

    text = str(error).lower()

    return any(
        marker in text
        for marker in ANTI_BOT_MARKERS
    )


# ============================================================
# RESUMEN
# ============================================================

def get_ytdlp_config_summary() -> dict:

    browser = get_ytdlp_browser()

    return {
        "browser_cookies_enabled": bool(browser),
        "browser": browser,
        "quiet_logger": True,
        "request_sleep_seconds": 0.75,
    }
