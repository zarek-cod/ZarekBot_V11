"""
CTX V11
Sistema lógico de avance automático.

Cuando una canción termina normalmente:

SIN LOOP:
    Canción termina
          ↓
    toma la siguiente de la cola

CON LOOP:
    Canción termina
          ↓
    vuelve a preparar la misma canción

AutoPlayback se encargará después
de iniciar realmente el audio.

NO:
- contiene comandos
- contiene interfaz
- busca música
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
    music_session_manager,
)

from music.track import Track


# ============================================================
# ESTADO
# ============================================================

_auto_advance_registered = False


# ============================================================
# CONTADORES
# ============================================================

_finished_received = 0

_tracks_prepared = 0

_loop_repeats = 0

_empty_queue_events = 0


# ============================================================
# ÚLTIMA CANCIÓN PREPARADA
# ============================================================

_last_prepared_track: dict[
    int,
    Track
] = {}


# ============================================================
# PREPARAR SIGUIENTE CANCIÓN
# ============================================================

def prepare_next_track(
    guild_id: int,
    finished_track: Track | None = None,
) -> Track | None:
    """
    Prepara la canción que deberá sonar después.

    Si LOOP está activo:
        vuelve a utilizar finished_track.

    Si LOOP está apagado:
        toma la siguiente canción pendiente.

    NO reproduce audio.
    """

    global _tracks_prepared
    global _loop_repeats
    global _empty_queue_events


    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    player = (
        music_player_manager.get_player(
            guild_id
        )
    )


    # ========================================================
    # YA EXISTE UNA CANCIÓN ACTUAL
    # ========================================================

    if session.current_track is not None:

        return session.current_track


    # ========================================================
    # LOOP ACTIVO
    # ========================================================

    if (
        session.state.loop_enabled
        and finished_track is not None
    ):

        # Volvemos a colocar exactamente
        # la misma canción como actual.
        session.queue.current = (
            finished_track
        )


        session.state.resume()


        player.status = (
            PlayerStatus.IDLE
        )


        _tracks_prepared += 1

        _loop_repeats += 1


        _last_prepared_track[
            guild_id
        ] = finished_track


        return finished_track


    # ========================================================
    # LOOP DESACTIVADO
    # ========================================================

    next_track = (
        session.move_to_next()
    )


    # ========================================================
    # COLA VACÍA
    # ========================================================

    if next_track is None:

        _empty_queue_events += 1


        player.status = (
            PlayerStatus.IDLE
        )


        return None


    # ========================================================
    # SIGUIENTE CANCIÓN PREPARADA
    # ========================================================

    _tracks_prepared += 1


    _last_prepared_track[
        guild_id
    ] = next_track


    player.status = (
        PlayerStatus.IDLE
    )


    return next_track


# ============================================================
# EVENTO FINISHED
# ============================================================

def handle_auto_advance_event(
    event: PlaybackEvent
) -> None:
    """
    Reacciona solamente a FINISHED.

    STOPPED y ERROR NO provocan
    avance automático.
    """

    global _finished_received


    if (
        event.event_type
        != PlaybackEventType.FINISHED
    ):

        return


    _finished_received += 1


    prepare_next_track(
        guild_id=event.guild_id,
        finished_track=event.track,
    )


# ============================================================
# REGISTRAR
# ============================================================

def register_auto_advance() -> None:

    global _auto_advance_registered


    if _auto_advance_registered:
        return


    playback_event_bus.subscribe(
        handle_auto_advance_event
    )


    _auto_advance_registered = True


# ============================================================
# DESREGISTRAR
# ============================================================

def unregister_auto_advance() -> None:

    global _auto_advance_registered


    playback_event_bus.unsubscribe(
        handle_auto_advance_event
    )


    _auto_advance_registered = False


# ============================================================
# CONSULTAS
# ============================================================

def is_auto_advance_registered() -> bool:

    return _auto_advance_registered


def get_last_prepared_track(
    guild_id: int
) -> Track | None:

    return _last_prepared_track.get(
        guild_id
    )


# ============================================================
# RESUMEN
# ============================================================

def get_auto_advance_summary() -> dict:

    return {

        "registered":
            _auto_advance_registered,

        "finished_received":
            _finished_received,

        "tracks_prepared":
            _tracks_prepared,

        "loop_repeats":
            _loop_repeats,

        "empty_queue_events":
            _empty_queue_events,

        "logical_auto_advance":
            True,

        "real_loop_repeat":
            True,

        # AutoPlayback es otro módulo.
        "automatic_audio_start":
            False,
    }