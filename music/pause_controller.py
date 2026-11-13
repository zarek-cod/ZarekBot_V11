"""
CTX V11
Controlador seguro de PAUSE.

Este módulo pausa la reproducción actual
y mantiene sincronizados:

- Backend real
- MusicSession
- GuildMusicPlayer

NO:
- contiene comandos Discord
- contiene interfaz
- decide permisos
- busca canciones
"""

import asyncio

from dataclasses import dataclass

from music.backend_manager import (
    playback_backend_manager,
)

from music.player import (
    PlayerStatus,
    music_player_manager,
)

from music.session import (
    music_session_manager,
)

from music.track import Track


# ============================================================
# RESULTADO
# ============================================================

@dataclass(frozen=True)
class PauseResult:
    """
    Resultado de una operación PAUSE.
    """

    success: bool

    track: Track | None

    already_paused: bool

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_pause_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_pause_lock(
    guild_id: int
) -> asyncio.Lock:
    """
    Devuelve un lock independiente
    para cada servidor.
    """

    if guild_id not in _pause_locks:

        _pause_locks[
            guild_id
        ] = asyncio.Lock()


    return _pause_locks[
        guild_id
    ]


# ============================================================
# PAUSAR
# ============================================================

async def pause_current_track(
    guild_id: int
) -> PauseResult:
    """
    Pausa de forma segura la canción actual.
    """

    lock = _get_pause_lock(
        guild_id
    )


    async with lock:

        # ====================================================
        # SESIÓN
        # ====================================================

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        # ====================================================
        # PLAYER LÓGICO
        # ====================================================

        player = (
            music_player_manager.get_player(
                guild_id
            )
        )


        # ====================================================
        # CANCIÓN ACTUAL
        # ====================================================

        track = (
            session.current_track
        )


        if track is None:

            return PauseResult(
                success=False,
                track=None,
                already_paused=False,
                message=(
                    "No hay ninguna canción "
                    "para pausar."
                ),
            )


        # ====================================================
        # YA ESTÁ PAUSADO
        # ====================================================

        if (
            player.status
            == PlayerStatus.PAUSED
            or session.state.paused
        ):

            return PauseResult(
                success=True,
                track=track,
                already_paused=True,
                message=(
                    f"{track.title} ya está pausada."
                ),
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

            return PauseResult(
                success=False,
                track=track,
                already_paused=False,
                message=(
                    "CTX Music no pudo obtener "
                    f"el backend: {error}"
                ),
            )


        # ====================================================
        # PAUSAR BACKEND
        # ====================================================

        try:

            backend_result = (
                await backend.pause()
            )

        except Exception as error:

            return PauseResult(
                success=False,
                track=track,
                already_paused=False,
                message=(
                    "No se pudo pausar "
                    f"la reproducción: {error}"
                ),
            )


        # ====================================================
        # BACKEND RECHAZÓ PAUSE
        # ====================================================

        if not backend_result.success:

            return PauseResult(
                success=False,
                track=track,
                already_paused=False,
                message=backend_result.message,
            )


        # ====================================================
        # SINCRONIZAR ESTADO
        # ====================================================

        session.pause()


        player.status = (
            PlayerStatus.PAUSED
        )


        # ====================================================
        # RESULTADO
        # ====================================================

        return PauseResult(
            success=True,
            track=track,
            already_paused=False,
            message=(
                f"{track.title} fue pausada."
            ),
        )


# ============================================================
# RESUMEN
# ============================================================

def get_pause_controller_summary() -> dict:

    return {

        "pause_available":
            True,

        "guild_locks":
            len(_pause_locks),

        "concurrent_pause_protection":
            True,

        "session_sync":
            True,

        "player_sync":
            True,

        "backend_sync":
            True,
    }