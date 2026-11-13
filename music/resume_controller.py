"""
CTX V11
Controlador seguro de RESUME.

Este módulo reanuda una canción pausada
y mantiene sincronizados:

- Backend
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
class ResumeResult:
    """
    Resultado de una operación RESUME.
    """

    success: bool

    track: Track | None

    already_playing: bool

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_resume_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_resume_lock(
    guild_id: int
) -> asyncio.Lock:
    """
    Devuelve un lock independiente
    para cada servidor.
    """

    if guild_id not in _resume_locks:

        _resume_locks[
            guild_id
        ] = asyncio.Lock()


    return _resume_locks[
        guild_id
    ]


# ============================================================
# REANUDAR
# ============================================================

async def resume_current_track(
    guild_id: int
) -> ResumeResult:
    """
    Reanuda de forma segura
    la canción actualmente pausada.
    """

    lock = _get_resume_lock(
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
        # PLAYER
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

            return ResumeResult(
                success=False,
                track=None,
                already_playing=False,
                message=(
                    "No hay ninguna canción "
                    "para reanudar."
                ),
            )


        # ====================================================
        # YA ESTÁ REPRODUCIÉNDOSE
        # ====================================================

        if (
            player.status
            == PlayerStatus.PLAYING
            and not session.state.paused
        ):

            return ResumeResult(
                success=True,
                track=track,
                already_playing=True,
                message=(
                    f"{track.title} ya está "
                    "reproduciéndose."
                ),
            )


        # ====================================================
        # COMPROBAR QUE ESTÉ PAUSADA
        # ====================================================

        if (
            player.status
            != PlayerStatus.PAUSED
            and not session.state.paused
        ):

            return ResumeResult(
                success=False,
                track=track,
                already_playing=False,
                message=(
                    "La canción actual no está pausada."
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

            return ResumeResult(
                success=False,
                track=track,
                already_playing=False,
                message=(
                    "CTX Music no pudo obtener "
                    f"el backend: {error}"
                ),
            )


        # ====================================================
        # REANUDAR BACKEND
        # ====================================================

        try:

            backend_result = (
                await backend.resume()
            )

        except Exception as error:

            return ResumeResult(
                success=False,
                track=track,
                already_playing=False,
                message=(
                    "No se pudo reanudar "
                    f"la reproducción: {error}"
                ),
            )


        # ====================================================
        # BACKEND RECHAZÓ RESUME
        # ====================================================

        if not backend_result.success:

            return ResumeResult(
                success=False,
                track=track,
                already_playing=False,
                message=backend_result.message,
            )


        # ====================================================
        # SINCRONIZAR SESIÓN
        # ====================================================

        session.resume()


        # ====================================================
        # SINCRONIZAR PLAYER
        # ====================================================

        player.status = (
            PlayerStatus.PLAYING
        )


        # ====================================================
        # RESULTADO
        # ====================================================

        return ResumeResult(
            success=True,
            track=track,
            already_playing=False,
            message=(
                f"{track.title} volvió a reproducirse."
            ),
        )


# ============================================================
# RESUMEN
# ============================================================

def get_resume_controller_summary() -> dict:

    return {

        "resume_available":
            True,

        "guild_locks":
            len(_resume_locks),

        "concurrent_resume_protection":
            True,

        "session_sync":
            True,

        "player_sync":
            True,

        "backend_sync":
            True,
    }