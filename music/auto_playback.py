"""
CTX V11
Inicio automático seguro de audio.

Este módulo escucha FINISHED.

Flujo:

    canción termina
          ↓
    PlaybackEventHandler
          ↓
    AutoAdvance
          ↓
    siguiente Track preparado
          ↓
    StreamRefresher
          ↓
    stream fresco
          ↓
    DiscordPlaybackBackend
          ↓
    FFmpeg

IMPORTANTE:

Las canciones de YouTube reciben un stream
nuevo justo antes de reproducirse.

Esto evita problemas cuando una canción estuvo
mucho tiempo esperando dentro de la cola.

NO:
- busca canciones por sí mismo
- contiene comandos Discord
- contiene interfaz
"""

from music.async_scheduler import (
    is_async_scheduler_initialized,
    schedule_coroutine,
)

from music.auto_advance import was_event_prepared

from music.playback_events import (
    PlaybackEvent,
    PlaybackEventType,
    playback_event_bus,
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

from music.state_events import (
    MusicStateEventType,
    emit_music_state_event,
)


# ============================================================
# ESTADO
# ============================================================

_auto_playback_registered = False


# ============================================================
# CONTADORES
# ============================================================

_finished_received = 0

_start_tasks_created = 0

_tracks_started = 0

_start_failures = 0

_no_track_events = 0


# ============================================================
# REFRESH
# ============================================================

_refresh_attempts = 0

_refresh_successes = 0

_refresh_failures = 0


# ============================================================
# INICIAR CANCIÓN PREPARADA
# ============================================================

async def _start_prepared_track_unlocked(
    guild_id: int
) -> bool:
    """
    Reproduce la canción que AutoAdvance
    dejó preparada como current_track.

    Antes de reproducir:

        YouTube
            ↓
        StreamRefresher
            ↓
        stream nuevo
            ↓
        Backend

    Devuelve:

        True  -> comenzó correctamente
        False -> no pudo comenzar
    """

    global _tracks_started
    global _start_failures
    global _no_track_events

    global _refresh_attempts
    global _refresh_successes
    global _refresh_failures


    # ========================================================
    # SESIÓN
    # ========================================================

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    # ========================================================
    # PLAYER
    # ========================================================

    player = (
        music_player_manager.get_player(
            guild_id
        )
    )


    # ========================================================
    # CANCIÓN PREPARADA
    # ========================================================

    track = (
        session.current_track
    )


    if track is None:

        _no_track_events += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return False


    # ========================================================
    # RUNTIME
    # ========================================================
    #
    # Import local para evitar dependencias
    # circulares durante el arranque.
    #

    from music.runtime import (
        get_guild_backend,
        is_music_runtime_initialized,
    )


    if not is_music_runtime_initialized():

        _start_failures += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return False


    # ========================================================
    # REFRESCAR STREAM
    # ========================================================
    #
    # Para YouTube:
    #     obtiene una URL nueva.
    #
    # Para fuentes directas:
    #     conserva la URL existente.
    #

    _refresh_attempts += 1


    try:

        refresh_result = (
            await refresh_track_stream(
                track
            )
        )


    except Exception:

        _refresh_failures += 1

        _start_failures += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return False


    # ========================================================
    # REFRESH FALLÓ
    # ========================================================

    if not refresh_result.success:

        _refresh_failures += 1

        _start_failures += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return False


    # ========================================================
    # COMPROBAR STREAM
    # ========================================================

    if not track.stream_url:

        _refresh_failures += 1

        _start_failures += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return False


    # ========================================================
    # REFRESH CORRECTO
    # ========================================================

    _refresh_successes += 1

    # A stop, skip, or manual play may have changed the selected track while
    # yt-dlp refreshed the URL.  Never let that delayed result take over.
    if session.current_track is not track:
        return False


    # ========================================================
    # OBTENER BACKEND
    # ========================================================

    try:

        backend = (
            get_guild_backend(
                guild_id
            )
        )


    except Exception:

        _start_failures += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return False

    if not backend.is_connected:
        channel_id = track.voice_channel_id
        if channel_id is None:
            _start_failures += 1
            return False
        connect_result = await backend.connect(channel_id)
        if not connect_result.success:
            _start_failures += 1
            return False
        session.mark_connected()


    # ========================================================
    # REPRODUCIR
    # ========================================================

    try:

        result = (
            await backend.play(
                track
            )
        )


    except Exception:

        _start_failures += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return False


    # ========================================================
    # BACKEND RECHAZÓ PLAY
    # ========================================================

    if not result.success:

        _start_failures += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return False

    if session.current_track is not track:
        _start_failures += 1
        return False


    # ========================================================
    # SINCRONIZAR SESIÓN
    # ========================================================

    session.state.resume()


    # ========================================================
    # PLAYER
    # ========================================================

    player.status = (
        PlayerStatus.PLAYING
    )


    # ========================================================
    # CONTADOR
    # ========================================================

    _tracks_started += 1

    emit_music_state_event(
        guild_id,
        MusicStateEventType.TRACK_STARTED,
        track=track,
    )


    return True


async def start_prepared_track(guild_id: int) -> bool:
    """Serialize automatic starts with play, skip, stop, and control actions."""

    async with get_guild_operation_lock(guild_id):
        return await _start_prepared_track_unlocked(guild_id)


# ============================================================
# EVENTO FINISHED
# ============================================================

def handle_auto_playback_event(
    event: PlaybackEvent
) -> None:
    """
    Escucha solamente FINISHED.

    El orden esperado es:

        PlaybackEventHandler
                ↓
        AutoAdvance
                ↓
        AutoPlayback
    """

    global _finished_received
    global _start_tasks_created


    if event.event_type not in {
        PlaybackEventType.FINISHED,
        PlaybackEventType.ERROR,
    }:

        return

    if not was_event_prepared(event):
        return


    _finished_received += 1


    # ========================================================
    # SCHEDULER
    # ========================================================

    if not is_async_scheduler_initialized():

        return


    # ========================================================
    # PROGRAMAR TAREA
    # ========================================================

    try:

        schedule_coroutine(
            start_prepared_track(
                event.guild_id
            )
        )


        _start_tasks_created += 1


    except RuntimeError:

        return


# ============================================================
# REGISTRAR
# ============================================================

def register_auto_playback() -> None:

    global _auto_playback_registered


    if _auto_playback_registered:
        return


    playback_event_bus.subscribe(
        handle_auto_playback_event
    )


    _auto_playback_registered = True


# ============================================================
# DESREGISTRAR
# ============================================================

def unregister_auto_playback() -> None:

    global _auto_playback_registered


    playback_event_bus.unsubscribe(
        handle_auto_playback_event
    )


    _auto_playback_registered = False


# ============================================================
# CONSULTAR ESTADO
# ============================================================

def is_auto_playback_registered() -> bool:

    return _auto_playback_registered


# ============================================================
# RESUMEN
# ============================================================

def get_auto_playback_summary() -> dict:

    return {

        "registered":
            _auto_playback_registered,

        "finished_received":
            _finished_received,

        "start_tasks_created":
            _start_tasks_created,

        "tracks_started":
            _tracks_started,

        "start_failures":
            _start_failures,

        "no_track_events":
            _no_track_events,

        "refresh_attempts":
            _refresh_attempts,

        "refresh_successes":
            _refresh_successes,

        "refresh_failures":
            _refresh_failures,

        "thread_safe":
            True,

        "automatic_audio_start":
            True,

        "refresh_before_playback":
            True,
    }
