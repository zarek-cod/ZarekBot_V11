"""
CTX V11
Controlador seguro de SKIP.

Flujo:

    Canción actual
          ↓
        STOP
          ↓
    siguiente canción
          ↓
    StreamRefresher
          ↓
    stream fresco
          ↓
       PLAY

Incluye:

- locks por servidor
- protección contra SKIP simultáneo
- refresh de streams de YouTube
- compatibilidad con eventos atrasados

NO:
- contiene comandos Discord
- contiene interfaz
- decide permisos
- busca canciones por sí mismo
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

from music.stream_refresher import (
    refresh_track_stream,
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
class SkipResult:
    """
    Resultado de una operación SKIP.
    """

    success: bool

    skipped_track: Track | None

    next_track: Track | None

    next_started: bool

    stream_refreshed: bool

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_skip_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_skip_lock(
    guild_id: int
) -> asyncio.Lock:

    if guild_id not in _skip_locks:

        _skip_locks[guild_id] = get_guild_operation_lock(guild_id)


    return _skip_locks[
        guild_id
    ]


# ============================================================
# CONTADORES
# ============================================================

_skip_count = 0

_skip_failures = 0

_refresh_attempts = 0

_refresh_successes = 0

_refresh_failures = 0


# ============================================================
# SKIP
# ============================================================

async def skip_current_track(
    guild_id: int
) -> SkipResult:
    """
    Salta la canción actual.

    Si existe otra canción pendiente:

        1. obtiene la siguiente
        2. refresca su stream si es necesario
        3. inicia reproducción

    Si no quedan canciones:
        deja el reproductor detenido.
    """

    global _skip_count
    global _skip_failures

    global _refresh_attempts
    global _refresh_successes
    global _refresh_failures

    from music.autoplay_recommendations import cancel_pending_autoplay

    cancel_pending_autoplay(guild_id)


    lock = _get_skip_lock(
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

        skipped_track = (
            session.current_track
        )


        if skipped_track is None:

            _skip_failures += 1


            return SkipResult(
                success=False,
                skipped_track=None,
                next_track=None,
                next_started=False,
                stream_refreshed=False,
                message=(
                    "No hay ninguna canción "
                    "para saltar."
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

            _skip_failures += 1


            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=None,
                next_started=False,
                stream_refreshed=False,
                message=(
                    "CTX Music no pudo obtener "
                    f"el backend: {error}"
                ),
            )


        # ====================================================
        # DETENER CANCIÓN ACTUAL
        # ====================================================

        try:

            stop_result = (
                await backend.stop()
            )


        except Exception as error:

            _skip_failures += 1


            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=None,
                next_started=False,
                stream_refreshed=False,
                message=(
                    "No se pudo detener "
                    f"la canción actual: {error}"
                ),
            )


        if not stop_result.success:

            _skip_failures += 1


            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=None,
                next_started=False,
                stream_refreshed=False,
                message=stop_result.message,
            )


        # ====================================================
        # LIMPIAR CANCIÓN ANTERIOR
        # ====================================================

        session.queue.current = None

        session.state.resume()


        # ====================================================
        # OBTENER SIGUIENTE
        # ====================================================

        next_track = (
            session.move_to_next()
        )


        # ====================================================
        # COLA VACÍA
        # ====================================================

        if next_track is None:

            _skip_count += 1


            player.status = (
                PlayerStatus.STOPPED
            )

            emit_music_state_event(
                guild_id,
                MusicStateEventType.STOPPED,
                track=skipped_track,
            )

            emit_music_state_event(
                guild_id,
                MusicStateEventType.QUEUE_CHANGED,
            )


            return SkipResult(
                success=True,
                skipped_track=skipped_track,
                next_track=None,
                next_started=False,
                stream_refreshed=False,
                message=(
                    f"Se saltó "
                    f"{skipped_track.title}. "
                    "No quedan más canciones."
                ),
            )


        # ====================================================
        # REFRESCAR STREAM
        # ====================================================

        _refresh_attempts += 1


        try:

            refresh_result = (
                await refresh_track_stream(
                    next_track
                )
            )


        except Exception as error:

            _refresh_failures += 1

            _skip_failures += 1


            player.status = (
                PlayerStatus.IDLE
            )

            session.queue.current = None
            emit_music_state_event(
                guild_id,
                MusicStateEventType.PLAYBACK_ERROR,
                track=next_track,
                notice=str(error),
            )


            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=next_track,
                next_started=False,
                stream_refreshed=False,
                message=(
                    "Se saltó la canción actual, "
                    "pero no se pudo actualizar "
                    f"la siguiente: {error}"
                ),
            )


        # ====================================================
        # REFRESH RECHAZADO
        # ====================================================

        if not refresh_result.success:

            _refresh_failures += 1

            _skip_failures += 1


            player.status = (
                PlayerStatus.IDLE
            )

            session.queue.current = None
            emit_music_state_event(
                guild_id,
                MusicStateEventType.PLAYBACK_ERROR,
                track=next_track,
                notice=refresh_result.message,
            )


            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=next_track,
                next_started=False,
                stream_refreshed=False,
                message=(
                    "Se saltó la canción actual, "
                    "pero no se pudo preparar "
                    "el stream de la siguiente."
                ),
            )


        # ====================================================
        # COMPROBAR STREAM
        # ====================================================

        if not next_track.stream_url:

            _refresh_failures += 1

            _skip_failures += 1


            player.status = (
                PlayerStatus.IDLE
            )

            session.queue.current = None
            emit_music_state_event(
                guild_id,
                MusicStateEventType.PLAYBACK_ERROR,
                track=next_track,
                notice="La siguiente canción no tiene un stream reproducible.",
            )


            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=next_track,
                next_started=False,
                stream_refreshed=False,
                message=(
                    "La siguiente canción no tiene "
                    "un stream reproducible."
                ),
            )


        # ====================================================
        # REFRESH CORRECTO
        # ====================================================

        _refresh_successes += 1


        # ====================================================
        # REPRODUCIR SIGUIENTE
        # ====================================================

        if not backend.is_connected:
            if next_track.voice_channel_id is None:
                _skip_failures += 1
                session.queue.current = None
                return SkipResult(
                    success=False,
                    skipped_track=skipped_track,
                    next_track=next_track,
                    next_started=False,
                    stream_refreshed=refresh_result.refreshed,
                    message="CTX perdió la conexión de voz y no pudo recuperarla.",
                )
            reconnect_result = await backend.connect(next_track.voice_channel_id)
            if not reconnect_result.success:
                _skip_failures += 1
                session.queue.current = None
                return SkipResult(
                    success=False,
                    skipped_track=skipped_track,
                    next_track=next_track,
                    next_started=False,
                    stream_refreshed=refresh_result.refreshed,
                    message=reconnect_result.message,
                )
            session.mark_connected()

        try:

            play_result = (
                await backend.play(
                    next_track
                )
            )


        except Exception as error:

            _skip_failures += 1


            player.status = (
                PlayerStatus.IDLE
            )

            session.queue.current = None
            emit_music_state_event(
                guild_id,
                MusicStateEventType.PLAYBACK_ERROR,
                track=next_track,
                notice=str(error),
            )


            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=next_track,
                next_started=False,
                stream_refreshed=(
                    refresh_result.refreshed
                ),
                message=(
                    "La canción anterior fue saltada, "
                    "pero no se pudo iniciar "
                    f"la siguiente: {error}"
                ),
            )


        # ====================================================
        # PLAY RECHAZADO
        # ====================================================

        if not play_result.success:

            _skip_failures += 1


            player.status = (
                PlayerStatus.IDLE
            )

            session.queue.current = None
            emit_music_state_event(
                guild_id,
                MusicStateEventType.PLAYBACK_ERROR,
                track=next_track,
                notice=play_result.message,
            )


            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=next_track,
                next_started=False,
                stream_refreshed=(
                    refresh_result.refreshed
                ),
                message=(
                    "La canción anterior fue saltada, "
                    "pero la siguiente no pudo comenzar. "
                    f"{play_result.message}"
                ),
            )

        if session.current_track is not next_track:
            _skip_failures += 1
            return SkipResult(
                success=False,
                skipped_track=skipped_track,
                next_track=next_track,
                next_started=False,
                stream_refreshed=refresh_result.refreshed,
                message="La siguiente canción terminó antes de estabilizarse.",
            )


        # ====================================================
        # ÉXITO
        # ====================================================

        session.state.resume()


        player.status = (
            PlayerStatus.PLAYING
        )


        _skip_count += 1

        emit_music_state_event(
            guild_id,
            MusicStateEventType.TRACK_STARTED,
            track=next_track,
        )

        emit_music_state_event(
            guild_id,
            MusicStateEventType.QUEUE_CHANGED,
        )


        return SkipResult(
            success=True,
            skipped_track=skipped_track,
            next_track=next_track,
            next_started=True,
            stream_refreshed=(
                refresh_result.refreshed
            ),
            message=(
                f"Se saltó {skipped_track.title}. "
                f"Ahora suena {next_track.title}."
            ),
        )


# ============================================================
# RESUMEN
# ============================================================

def get_skip_controller_summary() -> dict:

    return {

        "skip_available":
            True,

        "guild_locks":
            len(_skip_locks),

        "skip_count":
            _skip_count,

        "skip_failures":
            _skip_failures,

        "refresh_attempts":
            _refresh_attempts,

        "refresh_successes":
            _refresh_successes,

        "refresh_failures":
            _refresh_failures,

        "concurrent_skip_protection":
            True,

        "automatic_next_start":
            True,

        "refresh_before_next_play":
            True,

        "stale_event_compatible":
            True,
    }
