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

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from music.track import Track


logger = logging.getLogger(__name__)


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

    def _deliver(self, event: PlaybackEvent) -> None:
        for listener in tuple(self._listeners):
            try:
                listener(event)
            except Exception:
                logger.exception(
                    "Playback listener failed for guild %s (%s)",
                    event.guild_id,
                    event.event_type.value,
                )

    def emit(
        self,
        event: PlaybackEvent
    ) -> None:
        """Deliver callbacks on the main event loop, including voice-thread calls."""

        try:
            from music.async_scheduler import (
                get_music_event_loop,
                is_async_scheduler_initialized,
            )

            if not is_async_scheduler_initialized():
                self._deliver(event)
                return

            event_loop = get_music_event_loop()
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if current_loop is event_loop:
                self._deliver(event)
            else:
                event_loop.call_soon_threadsafe(self._deliver, event)
        except Exception:
            logger.exception("Could not dispatch playback event")


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
