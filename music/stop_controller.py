"""
CTX V11
Controlador seguro de STOP.

Detiene completamente la reproducción actual
y sincroniza:

- Backend
- MusicSession
- GuildMusicPlayer

Por defecto también limpia la cola pendiente.

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
from music.operation_lock import get_guild_operation_lock

from music.session import (
    music_session_manager,
)

from music.track import Track
from music.state_events import (
    MusicStateEventType,
    emit_music_state_event,
)


# ============================================================
# RESULTADO
# ============================================================

@dataclass(frozen=True)
class StopResult:

    success: bool

    stopped_track: Track | None

    queue_cleared: bool

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_stop_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_stop_lock(
    guild_id: int
) -> asyncio.Lock:

    if guild_id not in _stop_locks:

        _stop_locks[guild_id] = get_guild_operation_lock(guild_id)

    return _stop_locks[
        guild_id
    ]


# ============================================================
# STOP
# ============================================================

async def stop_music(
    guild_id: int,
    clear_queue: bool = True
) -> StopResult:
    """
    Detiene completamente CTX Music.

    clear_queue=True:
        borra canciones pendientes.

    clear_queue=False:
        conserva la cola.
    """

    from music.autoplay_recommendations import cancel_pending_autoplay

    cancel_pending_autoplay(guild_id)

    lock = _get_stop_lock(
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

        stopped_track = (
            session.current_track
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

            return StopResult(
                success=False,
                stopped_track=stopped_track,
                queue_cleared=False,
                message=(
                    "CTX Music no pudo obtener "
                    f"el backend: {error}"
                ),
            )


        # ====================================================
        # DETENER BACKEND
        # ====================================================

        try:

            backend_result = (
                await backend.stop()
            )

        except Exception as error:

            return StopResult(
                success=False,
                stopped_track=stopped_track,
                queue_cleared=False,
                message=(
                    "No se pudo detener "
                    f"la reproducción: {error}"
                ),
            )


        if not backend_result.success:

            return StopResult(
                success=False,
                stopped_track=stopped_track,
                queue_cleared=False,
                message=backend_result.message,
            )


        # ====================================================
        # LIMPIAR CANCIÓN ACTUAL
        # ====================================================

        session.queue.current = None


        # ====================================================
        # LIMPIAR COLA
        # ====================================================

        if clear_queue:

            session.queue.clear()


        # ====================================================
        # ESTADO DE SESIÓN
        # ====================================================

        session.state.resume()


        # ====================================================
        # PLAYER
        # ====================================================

        player.status = (
            PlayerStatus.STOPPED
        )


        # ====================================================
        # RESULTADO
        # ====================================================

        if stopped_track is None:

            message = (
                "CTX Music fue detenido."
            )

        else:

            message = (
                f"Se detuvo {stopped_track.title}."
            )


        if clear_queue:

            message += (
                " La cola fue limpiada."
            )


        result = StopResult(
            success=True,
            stopped_track=stopped_track,
            queue_cleared=clear_queue,
            message=message,
        )

        emit_music_state_event(
            guild_id,
            MusicStateEventType.STOPPED,
            track=stopped_track,
        )
        if clear_queue:
            emit_music_state_event(
                guild_id,
                MusicStateEventType.QUEUE_CHANGED,
            )
        return result


# ============================================================
# RESUMEN
# ============================================================

def get_stop_controller_summary() -> dict:

    return {

        "stop_available":
            True,

        "guild_locks":
            len(_stop_locks),

        "concurrent_stop_protection":
            True,

        "clear_queue_supported":
            True,

        "session_sync":
            True,

        "player_sync":
            True,

        "backend_sync":
            True,
    }
