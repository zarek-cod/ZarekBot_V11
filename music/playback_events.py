"""
CTX V11
Sistema interno de eventos de reproducción.

Este módulo permite que el backend de audio
avise al resto de CTX cuando ocurre algo.

Ejemplos:

- una canción terminó
- ocurrió un error
- una canción fue detenida

NO:
- reproduce audio
- busca música
- contiene comandos
- contiene interfaz
"""

from dataclasses import dataclass
from enum import Enum
from collections.abc import Callable

from music.track import Track


# ============================================================
# TIPOS DE EVENTO
# ============================================================

class PlaybackEventType(str, Enum):

    FINISHED = "finished"

    STOPPED = "stopped"

    ERROR = "error"


# ============================================================
# EVENTO
# ============================================================

@dataclass(frozen=True)
class PlaybackEvent:
    """
    Información emitida por el reproductor.
    """

    guild_id: int

    event_type: PlaybackEventType

    track: Track | None = None

    error: Exception | None = None


# ============================================================
# CALLBACK
# ============================================================

PlaybackEventListener = Callable[
    [PlaybackEvent],
    None
]


# ============================================================
# BUS DE EVENTOS
# ============================================================

class PlaybackEventBus:
    """
    Administrador central de eventos musicales.
    """

    def __init__(
        self
    ) -> None:

        self._listeners: list[
            PlaybackEventListener
        ] = []


    # ========================================================
    # REGISTRAR LISTENER
    # ========================================================

    def subscribe(
        self,
        listener: PlaybackEventListener
    ) -> None:

        if listener in self._listeners:
            return

        self._listeners.append(
            listener
        )


    # ========================================================
    # ELIMINAR LISTENER
    # ========================================================

    def unsubscribe(
        self,
        listener: PlaybackEventListener
    ) -> bool:

        if listener not in self._listeners:
            return False

        self._listeners.remove(
            listener
        )

        return True


    # ========================================================
    # EMITIR EVENTO
    # ========================================================

    def emit(
        self,
        event: PlaybackEvent
    ) -> None:
        """
        Envía el evento a todos
        los listeners registrados.
        """

        for listener in list(
            self._listeners
        ):

            try:

                listener(
                    event
                )

            except Exception:

                # Un listener roto no debe
                # impedir que los demás reciban
                # el evento.
                continue


    # ========================================================
    # CANTIDAD
    # ========================================================

    def listener_count(
        self
    ) -> int:

        return len(
            self._listeners
        )


    # ========================================================
    # LIMPIAR
    # ========================================================

    def clear(
        self
    ) -> None:

        self._listeners.clear()


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

playback_event_bus = PlaybackEventBus()


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def emit_track_finished(
    guild_id: int,
    track: Track | None
) -> None:

    playback_event_bus.emit(
        PlaybackEvent(
            guild_id=guild_id,
            event_type=PlaybackEventType.FINISHED,
            track=track,
        )
    )


def emit_track_stopped(
    guild_id: int,
    track: Track | None
) -> None:

    playback_event_bus.emit(
        PlaybackEvent(
            guild_id=guild_id,
            event_type=PlaybackEventType.STOPPED,
            track=track,
        )
    )


def emit_playback_error(
    guild_id: int,
    track: Track | None,
    error: Exception
) -> None:

    playback_event_bus.emit(
        PlaybackEvent(
            guild_id=guild_id,
            event_type=PlaybackEventType.ERROR,
            track=track,
            error=error,
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_playback_event_summary() -> dict:

    return {

        "event_bus":
            True,

        "listeners":
            playback_event_bus.listener_count(),

        "finished_event":
            True,

        "stopped_event":
            True,

        "error_event":
            True,

        "automatic_next_track":
            False,
    }