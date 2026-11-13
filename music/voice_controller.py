"""
CTX V11
Controlador de conexión de voz.

Administra:

- conectar CTX a un canal
- cambiar CTX de canal
- desconectar CTX
- sincronizar MusicSession con el backend

NO:
- contiene comandos Discord
- decide permisos
- busca música
- contiene interfaz
"""

import asyncio

from dataclasses import dataclass

from music.backend_manager import (
    playback_backend_manager,
)

from music.session import (
    music_session_manager,
)


# ============================================================
# RESULTADO DE CONEXIÓN
# ============================================================

@dataclass(frozen=True)
class VoiceConnectResult:

    success: bool

    channel_id: int | None

    connected: bool

    message: str


# ============================================================
# RESULTADO DE DESCONEXIÓN
# ============================================================

@dataclass(frozen=True)
class VoiceDisconnectResult:

    success: bool

    connected: bool

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_voice_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_voice_lock(
    guild_id: int
) -> asyncio.Lock:
    """
    Cada servidor tiene su propio lock.

    Evita dos conexiones/desconexiones
    simultáneas.
    """

    if guild_id not in _voice_locks:

        _voice_locks[
            guild_id
        ] = asyncio.Lock()


    return _voice_locks[
        guild_id
    ]


# ============================================================
# CONECTAR
# ============================================================

async def connect_to_voice(
    guild_id: int,
    channel_id: int,
) -> VoiceConnectResult:
    """
    Conecta CTX al canal indicado.

    Si ya está conectado en otro canal,
    el backend real podrá moverlo.
    """

    lock = _get_voice_lock(
        guild_id
    )


    async with lock:

        # ====================================================
        # VALIDAR CANAL
        # ====================================================

        if channel_id <= 0:

            return VoiceConnectResult(
                success=False,
                channel_id=channel_id,
                connected=False,
                message=(
                    "El canal de voz indicado "
                    "no es válido."
                ),
            )


        # ====================================================
        # SESIÓN
        # ====================================================

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        # ====================================================
        # BACKEND
        # ====================================================

        try:

            backend = (
                playback_backend_manager.get_backend(
                    guild_id
                )
            )

        except Exception as error:

            return VoiceConnectResult(
                success=False,
                channel_id=channel_id,
                connected=False,
                message=(
                    "CTX Music no pudo obtener "
                    f"el backend: {error}"
                ),
            )


        # ====================================================
        # CONECTAR
        # ====================================================

        try:

            result = await backend.connect(
                channel_id
            )

        except Exception as error:

            return VoiceConnectResult(
                success=False,
                channel_id=channel_id,
                connected=False,
                message=(
                    "CTX no pudo conectarse "
                    f"al canal de voz: {error}"
                ),
            )


        # ====================================================
        # BACKEND RECHAZÓ CONEXIÓN
        # ====================================================

        if not result.success:

            session.mark_disconnected()


            return VoiceConnectResult(
                success=False,
                channel_id=channel_id,
                connected=False,
                message=result.message,
            )


        # ====================================================
        # SINCRONIZAR SESIÓN
        # ====================================================

        session.mark_connected()


        return VoiceConnectResult(
            success=True,
            channel_id=channel_id,
            connected=True,
            message=result.message,
        )


# ============================================================
# DESCONECTAR
# ============================================================

async def disconnect_from_voice(
    guild_id: int
) -> VoiceDisconnectResult:
    """
    Desconecta CTX del canal de voz.

    La cola NO se borra aquí.

    STOP será quien decida si debe
    limpiar la cola musical.
    """

    lock = _get_voice_lock(
        guild_id
    )


    async with lock:

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        # ====================================================
        # BACKEND
        # ====================================================

        try:

            backend = (
                playback_backend_manager.get_backend(
                    guild_id
                )
            )

        except Exception as error:

            return VoiceDisconnectResult(
                success=False,
                connected=(
                    session.state.connected
                ),
                message=(
                    "CTX Music no pudo obtener "
                    f"el backend: {error}"
                ),
            )


        # ====================================================
        # DESCONECTAR
        # ====================================================

        try:

            result = await backend.disconnect()

        except Exception as error:

            return VoiceDisconnectResult(
                success=False,
                connected=(
                    session.state.connected
                ),
                message=(
                    "CTX no pudo salir "
                    f"del canal de voz: {error}"
                ),
            )


        if not result.success:

            return VoiceDisconnectResult(
                success=False,
                connected=(
                    session.state.connected
                ),
                message=result.message,
            )


        # ====================================================
        # SINCRONIZAR
        # ====================================================

        session.mark_disconnected()


        return VoiceDisconnectResult(
            success=True,
            connected=False,
            message=result.message,
        )


# ============================================================
# CONSULTAR ESTADO
# ============================================================

def is_voice_connected(
    guild_id: int
) -> bool:

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    return session.state.connected


# ============================================================
# RESUMEN
# ============================================================

def get_voice_controller_summary() -> dict:

    return {

        "voice_connect":
            True,

        "voice_disconnect":
            True,

        "session_sync":
            True,

        "guild_locks":
            len(_voice_locks),

        "concurrent_voice_protection":
            True,

        "auto_join_from_play":
            False,
    }