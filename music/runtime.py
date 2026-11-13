"""
CTX V11
Runtime principal del sistema musical.

Inicializa y coordina:

Discord Client
      ↓
AsyncScheduler
      ↓
PlaybackEventHandler
      ↓
AutoAdvance
      ↓
AutoPlayback
      ↓
PlaybackBackendManager
      ↓
DiscordPlaybackBackend
      ↓
FFmpeg

ORDEN DE EVENTOS IMPORTANTE:

1. PlaybackEventHandler
2. AutoAdvance
3. AutoPlayback

De esta manera, cuando termina una canción:

- se limpia la canción anterior
- se prepara la siguiente
- se programa su reproducción

TODAVÍA NO:
- contiene comandos
- contiene interfaz
- realiza búsqueda musical real
"""

import asyncio

import discord

from music.async_scheduler import (
    initialize_async_scheduler,
    is_async_scheduler_initialized,
    reset_async_scheduler,
)

from music.auto_advance import (
    is_auto_advance_registered,
    register_auto_advance,
    unregister_auto_advance,
)

from music.auto_playback import (
    is_auto_playback_registered,
    register_auto_playback,
    unregister_auto_playback,
)

from music.backend_manager import (
    playback_backend_manager,
)

from music.discord_backend import (
    DiscordPlaybackBackend,
)

from music.playback_backend import (
    PlaybackBackend,
)

from music.playback_event_handler import (
    is_playback_event_handler_registered,
    register_playback_event_handler,
    unregister_playback_event_handler,
)


# ============================================================
# CLIENTE PRINCIPAL DE DISCORD
# ============================================================

_discord_client: discord.Client | None = None


# ============================================================
# ESTADO DEL RUNTIME
# ============================================================

_initialized = False


# ============================================================
# CREAR BACKEND DISCORD
# ============================================================

def _create_discord_backend(
    guild_id: int
) -> PlaybackBackend:
    """
    Crea un backend Discord + FFmpeg
    independiente para cada servidor.
    """

    if _discord_client is None:

        raise RuntimeError(
            "CTX Music todavía no tiene "
            "un cliente de Discord configurado."
        )


    return DiscordPlaybackBackend(
        guild_id=guild_id,
        client=_discord_client,
    )


# ============================================================
# INICIALIZAR RUNTIME
# ============================================================

def initialize_music_runtime(
    client: discord.Client
) -> None:
    """
    Inicializa todo CTX Music.

    Debe ejecutarse dentro del Event Loop
    principal de Discord.
    """

    global _discord_client
    global _initialized


    if client is None:

        raise ValueError(
            "Se necesita un cliente Discord válido."
        )


    # ========================================================
    # 1. ASYNC SCHEDULER
    # ========================================================

    if not is_async_scheduler_initialized():

        initialize_async_scheduler()


    # ========================================================
    # 2. CLIENTE DISCORD
    # ========================================================

    _discord_client = client


    # ========================================================
    # 3. FACTORY DE BACKENDS
    # ========================================================

    playback_backend_manager.set_factory(
        _create_discord_backend
    )


    # ========================================================
    # 4. PLAYBACK EVENT HANDLER
    # ========================================================
    #
    # PRIMERO:
    # limpia/sincroniza la canción anterior.
    #

    register_playback_event_handler()


    # ========================================================
    # 5. AUTO ADVANCE
    # ========================================================
    #
    # SEGUNDO:
    # prepara la próxima canción.
    #

    register_auto_advance()


    # ========================================================
    # 6. AUTO PLAYBACK
    # ========================================================
    #
    # TERCERO:
    # reproduce la canción que AutoAdvance preparó.
    #

    register_auto_playback()


    # ========================================================
    # 7. RUNTIME LISTO
    # ========================================================

    _initialized = True


# ============================================================
# ¿ESTÁ COMPLETAMENTE LISTO?
# ============================================================

def is_music_runtime_initialized() -> bool:

    return (

        _initialized

        and _discord_client is not None

        and is_async_scheduler_initialized()

        and playback_backend_manager.has_factory()

        and is_playback_event_handler_registered()

        and is_auto_advance_registered()

        and is_auto_playback_registered()
    )


# ============================================================
# OBTENER CLIENTE DISCORD
# ============================================================

def get_discord_client() -> discord.Client:

    if _discord_client is None:

        raise RuntimeError(
            "CTX Music todavía no ha sido inicializado."
        )


    return _discord_client


# ============================================================
# OBTENER BACKEND
# ============================================================

def get_guild_backend(
    guild_id: int
) -> PlaybackBackend:
    """
    Obtiene o crea el backend musical
    correspondiente a un servidor.
    """

    if not is_music_runtime_initialized():

        raise RuntimeError(
            "CTX Music todavía no está "
            "completamente inicializado."
        )


    return playback_backend_manager.get_backend(
        guild_id
    )


# ============================================================
# REINICIAR RUNTIME
# ============================================================

def reset_music_runtime() -> None:
    """
    Limpia el runtime musical.

    Se utiliza para:
    - pruebas
    - desarrollo
    - apagado controlado
    """

    global _discord_client
    global _initialized


    # ========================================================
    # DESREGISTRAR EN ORDEN INVERSO
    # ========================================================

    unregister_auto_playback()

    unregister_auto_advance()

    unregister_playback_event_handler()


    # ========================================================
    # ELIMINAR BACKENDS
    # ========================================================

    playback_backend_manager.clear()


    # ========================================================
    # ASYNC SCHEDULER
    # ========================================================

    reset_async_scheduler()


    # ========================================================
    # CLIENTE
    # ========================================================

    _discord_client = None


    # ========================================================
    # ESTADO
    # ========================================================

    _initialized = False


# ============================================================
# RESUMEN SEGURO
# ============================================================

def get_music_runtime_summary() -> dict:

    return {

        "initialized":
            _initialized,

        "fully_ready":
            is_music_runtime_initialized(),

        "discord_client_loaded":
            _discord_client is not None,

        "async_scheduler_initialized":
            is_async_scheduler_initialized(),

        "backend_factory_configured":
            playback_backend_manager.has_factory(),

        "playback_event_handler":
            is_playback_event_handler_registered(),

        "auto_advance":
            is_auto_advance_registered(),

        "auto_playback":
            is_auto_playback_registered(),

        "automatic_audio_start":
            is_auto_playback_registered(),

        "active_backends":
            playback_backend_manager.active_backends(),
    }


# ============================================================
# PRUEBA INTERNA
# ============================================================

def run_music_runtime_self_test() -> dict:
    """
    Prueba local de toda la arquitectura.

    NO:
    - inicia sesión en Discord
    - usa el token
    - entra a un canal
    - reproduce música
    """

    async def _test() -> dict:

        intents = (
            discord.Intents.none()
        )


        client = discord.Client(
            intents=intents
        )


        # ====================================================
        # INICIALIZAR
        # ====================================================

        initialize_music_runtime(
            client
        )


        # ====================================================
        # CREAR BACKEND DE PRUEBA
        # ====================================================

        backend = get_guild_backend(
            123
        )


        summary = (
            get_music_runtime_summary()
        )


        result = {

            "initialized":
                summary["initialized"],

            "fully_ready":
                summary["fully_ready"],

            "discord_client_loaded":
                summary[
                    "discord_client_loaded"
                ],

            "async_scheduler_initialized":
                summary[
                    "async_scheduler_initialized"
                ],

            "backend_factory_configured":
                summary[
                    "backend_factory_configured"
                ],

            "playback_event_handler":
                summary[
                    "playback_event_handler"
                ],

            "auto_advance":
                summary[
                    "auto_advance"
                ],

            "auto_playback":
                summary[
                    "auto_playback"
                ],

            "automatic_audio_start":
                summary[
                    "automatic_audio_start"
                ],

            "active_backends":
                summary[
                    "active_backends"
                ],

            "backend_name":
                backend.backend_name,
        }


        # ====================================================
        # LIMPIAR
        # ====================================================

        reset_music_runtime()


        return result


    return asyncio.run(
        _test()
    )