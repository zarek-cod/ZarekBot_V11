"""
CTX V11
Manejador central de eventos de reproducción.

Escucha eventos emitidos por el backend:

- FINISHED
- STOPPED
- ERROR

Incluye protección contra eventos atrasados.

Ejemplo:

Canción 1 se detiene
        ↓
Canción 2 comienza
        ↓
llega tarde el evento STOPPED de Canción 1

CTX NO debe borrar Canción 2.
"""

from music.playback_events import (
    PlaybackEvent,
    PlaybackEventType,
    playback_event_bus,
)

from music.player import (
    PlayerStatus,
    music_player_manager,
)

from music.session import (
    MusicSession,
    music_session_manager,
)

from music.state_events import (
    MusicStateEventType,
    emit_music_state_event,
)


# ============================================================
# ESTADO
# ============================================================

_handler_registered = False


# ============================================================
# CONTADORES
# ============================================================

_finished_events = 0

_stopped_events = 0

_error_events = 0

_stale_events_ignored = 0


# ============================================================
# COMPROBAR SI EL EVENTO PERTENECE
# A LA CANCIÓN ACTUAL
# ============================================================

def _event_matches_current_track(
    session: MusicSession,
    event: PlaybackEvent,
) -> bool:
    """
    Comprueba que el evento recibido todavía
    corresponda a la canción actual.

    Esto evita que un callback atrasado
    modifique una canción nueva.
    """

    current_track = (
        session.current_track
    )


    # Si ya no existe canción actual,
    # no hay nada nuevo que proteger.
    if current_track is None:

        return True


    # Si el evento no identifica canción,
    # no permitimos que borre una actual.
    if event.track is None:

        return False


    # Normalmente será exactamente
    # el mismo objeto Track.
    return (
        current_track
        is event.track
    )


def event_matches_current_track(event: PlaybackEvent) -> bool:
    """Public stale-event guard shared by the automatic playback listeners."""

    session = music_session_manager.get_session(event.guild_id)
    return _event_matches_current_track(session, event)


# ============================================================
# FINISHED
# ============================================================

def _handle_finished(
    event: PlaybackEvent
) -> None:

    global _finished_events
    global _stale_events_ignored


    _finished_events += 1


    session = (
        music_session_manager.get_session(
            event.guild_id
        )
    )


    player = (
        music_player_manager.get_player(
            event.guild_id
        )
    )


    # ========================================================
    # PROTECCIÓN CONTRA EVENTO VIEJO
    # ========================================================

    if not _event_matches_current_track(
        session,
        event,
    ):

        _stale_events_ignored += 1

        return


    # ========================================================
    # SINCRONIZAR
    # ========================================================

    session.queue.current = None

    session.state.resume()

    player.status = (
        PlayerStatus.IDLE
    )

    emit_music_state_event(
        event.guild_id,
        MusicStateEventType.TRACK_ENDED,
        track=event.track,
    )


# ============================================================
# STOPPED
# ============================================================

def _handle_stopped(
    event: PlaybackEvent
) -> None:

    global _stopped_events
    global _stale_events_ignored


    _stopped_events += 1


    session = (
        music_session_manager.get_session(
            event.guild_id
        )
    )


    player = (
        music_player_manager.get_player(
            event.guild_id
        )
    )


    # ========================================================
    # PROTECCIÓN CONTRA EVENTO VIEJO
    # ========================================================

    if not _event_matches_current_track(
        session,
        event,
    ):

        _stale_events_ignored += 1

        return


    # ========================================================
    # SINCRONIZAR
    # ========================================================

    session.queue.current = None

    session.state.resume()

    player.status = (
        PlayerStatus.STOPPED
    )

    emit_music_state_event(
        event.guild_id,
        MusicStateEventType.STOPPED,
        track=event.track,
    )


# ============================================================
# ERROR
# ============================================================

def _handle_error(
    event: PlaybackEvent
) -> None:

    global _error_events
    global _stale_events_ignored


    _error_events += 1


    session = (
        music_session_manager.get_session(
            event.guild_id
        )
    )


    player = (
        music_player_manager.get_player(
            event.guild_id
        )
    )


    # ========================================================
    # PROTECCIÓN CONTRA EVENTO VIEJO
    # ========================================================

    if not _event_matches_current_track(
        session,
        event,
    ):

        _stale_events_ignored += 1

        return


    # ========================================================
    # SINCRONIZAR
    # ========================================================

    session.queue.current = None

    session.state.resume()

    player.status = (
        PlayerStatus.IDLE
    )

    emit_music_state_event(
        event.guild_id,
        MusicStateEventType.PLAYBACK_ERROR,
        track=event.track,
        notice=(str(event.error) if event.error else None),
    )


# ============================================================
# HANDLER PRINCIPAL
# ============================================================

def handle_playback_event(
    event: PlaybackEvent
) -> None:

    if (
        event.event_type
        == PlaybackEventType.FINISHED
    ):

        _handle_finished(
            event
        )

        return


    if (
        event.event_type
        == PlaybackEventType.STOPPED
    ):

        _handle_stopped(
            event
        )

        return


    if (
        event.event_type
        == PlaybackEventType.ERROR
    ):

        _handle_error(
            event
        )

        return


# ============================================================
# REGISTRAR
# ============================================================

def register_playback_event_handler() -> None:

    global _handler_registered


    if _handler_registered:
        return


    playback_event_bus.subscribe(
        handle_playback_event
    )


    _handler_registered = True


# ============================================================
# DESREGISTRAR
# ============================================================

def unregister_playback_event_handler() -> None:

    global _handler_registered


    playback_event_bus.unsubscribe(
        handle_playback_event
    )


    _handler_registered = False


# ============================================================
# CONSULTAR
# ============================================================

def is_playback_event_handler_registered() -> bool:

    return _handler_registered


# ============================================================
# RESUMEN
# ============================================================

def get_playback_event_handler_summary() -> dict:

    return {

        "registered":
            _handler_registered,

        "listeners":
            playback_event_bus.listener_count(),

        "finished_events":
            _finished_events,

        "stopped_events":
            _stopped_events,

        "error_events":
            _error_events,

        "stale_events_ignored":
            _stale_events_ignored,

        "stale_event_protection":
            True,

        "automatic_next_track":
            False,
    }
