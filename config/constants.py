"""
CTX V11
Constantes globales del proyecto.

Aquí solamente deben existir valores públicos y estáticos.
NO colocar tokens, API Keys ni credenciales.
"""


# ============================================================
# IDENTIDAD DE CTX
# ============================================================

BOT_NAME = "CTX"

BOT_FULL_NAME = "ASISTENTE CTX"

BOT_CREATOR = "Zarek"

BOT_DESCRIPTION = (
    "Asistente inteligente de jerarquía, voz, música, "
    "moderación y entretenimiento."
)


# ============================================================
# IDENTIDAD VISUAL
# ============================================================

BOT_EMOJI = "🤖"
AI_EMOJI = "🧠"
MUSIC_EMOJI = "🎵"
VOICE_EMOJI = "🔊"
MODERATION_EMOJI = "🛡️"
HIERARCHY_EMOJI = "👑"
CASINO_EMOJI = "🎰"
ERROR_EMOJI = "❌"
SUCCESS_EMOJI = "✅"
WARNING_EMOJI = "⚠️"


# ============================================================
# DISCORD
# ============================================================

DISCORD_MESSAGE_LIMIT = 2000

# Dejamos margen para evitar errores cuando CTX responda
# con mensajes demasiado largos.
SAFE_MESSAGE_LIMIT = 1900


# ============================================================
# COMANDO PRINCIPAL
# ============================================================

MAIN_COMMAND = "ctx"

HELP_COMMAND = "ctx_help"


# ============================================================
# CATEGORÍAS DE COMANDOS
# ============================================================

CATEGORY_AI = "Inteligencia Artificial"
CATEGORY_MUSIC = "Música"
CATEGORY_VOICE = "Voz"
CATEGORY_MODERATION = "Moderación"
CATEGORY_CASINO = "Casino"
CATEGORY_SYSTEM = "Sistema"


# ============================================================
# NOMBRES DE SISTEMAS
# ============================================================

SYSTEM_AI = "CTX AI"
SYSTEM_MUSIC = "CTX Music"
SYSTEM_VOICE = "CTX Voice"
SYSTEM_MODERATION = "CTX Moderation"
SYSTEM_HIERARCHY = "CTX Hierarchy"
SYSTEM_CASINO = "CTX Casino"


# ============================================================
# ESTADOS INTERNOS
# ============================================================

STATUS_READY = "ready"
STATUS_STARTING = "starting"
STATUS_STOPPED = "stopped"
STATUS_ERROR = "error"


# ============================================================
# CONFIGURACIÓN DE DESARROLLO
# ============================================================

PROJECT_NAME = "ZarekBot"

PROJECT_EDITION = "CTX V11"


# ============================================================
# COMPORTAMIENTO GENERAL
# ============================================================

# En V11 eliminaremos los mensajes automáticos molestos
# enviados periódicamente a los canales de texto.
AUTOMATIC_TEXT_MESSAGES_ENABLED = False

# La interacción automática de voz se gestionará después
# desde el módulo voice/.
VOICE_AUTOMATIC_BEHAVIOR_ENABLED = True