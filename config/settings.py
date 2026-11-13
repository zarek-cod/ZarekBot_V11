"""
CTX V11
Configuración general y carga segura de variables de entorno.

Este archivo NO contiene tokens ni claves privadas.
Las credenciales se cargan desde .env en desarrollo
o desde variables de entorno cuando CTX esté en Render.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


# ============================================================
# VARIABLES DE ENTORNO
# ============================================================

# En PC cargará automáticamente el archivo .env.
# En Render también funcionará aunque .env no exista,
# porque Render utilizará sus propias Environment Variables.
load_dotenv(dotenv_path=ENV_FILE)


# ============================================================
# DISCORD
# ============================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()


# ============================================================
# GEMINI
# ============================================================

# CTX puede utilizar varias API Keys.
# Las claves vacías son descartadas automáticamente.
GEMINI_API_KEYS = [
    os.getenv(f"GEMINI_API_KEY_{numero}", "").strip()
    for numero in range(1, 8)
]

GEMINI_API_KEYS = [
    key
    for key in GEMINI_API_KEYS
    if key
]


# ============================================================
# CONFIGURACIÓN DEL BOT
# ============================================================

BOT_PREFIX = os.getenv("BOT_PREFIX", "!").strip() or "!"
BOT_VERSION = os.getenv("BOT_VERSION", "V11").strip() or "V11"
ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development"
).strip().lower()


# ============================================================
# MODOS
# ============================================================

IS_DEVELOPMENT = ENVIRONMENT == "development"
IS_PRODUCTION = ENVIRONMENT == "production"


# ============================================================
# VALIDACIÓN
# ============================================================

def validate_settings() -> None:
    """
    Comprueba que CTX tenga la configuración mínima necesaria
    antes de intentar conectarse.
    """

    errores = []

    if not DISCORD_TOKEN:
        errores.append(
            "Falta DISCORD_TOKEN."
        )

    if not GEMINI_API_KEYS:
        errores.append(
            "No se encontró ninguna GEMINI_API_KEY."
        )

    if errores:
        mensaje = "\n".join(
            f" - {error}"
            for error in errores
        )

        raise RuntimeError(
            "\n"
            "CTX V11 no puede iniciar por errores "
            "de configuración:\n"
            f"{mensaje}\n"
        )


# ============================================================
# RESUMEN SEGURO
# ============================================================

def get_safe_config_summary() -> dict:
    """
    Devuelve información de configuración que sí puede
    mostrarse en consola.

    Nunca devuelve tokens ni API Keys.
    """

    return {
        "version": BOT_VERSION,
        "environment": ENVIRONMENT,
        "prefix": BOT_PREFIX,
        "gemini_keys_loaded": len(GEMINI_API_KEYS),
        "discord_token_loaded": bool(DISCORD_TOKEN),
    }