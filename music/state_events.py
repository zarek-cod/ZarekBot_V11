"""Observable, thread-safe state changes for CTX Music.

Playback terminal events describe what Discord Voice reported.  State events
describe what users and the UI should see.  Keeping those concepts separate
prevents a manual stop, a stale callback, or a TTS interruption from looking
like a naturally finished track.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from music.playback_clock import playback_clock_manager
from music.track import Track


logger = logging.getLogger(__name__)


class MusicStateEventType(str, Enum):
    TRACK_STARTED = "track_started"
    TRACK_ENDED = "track_ended"
    PLAYBACK_ERROR = "playback_error"
    QUEUE_CHANGED = "queue_changed"
    PAUSED = "paused"
    RESUMED = "resumed"
    STOPPED = "stopped"
    VOLUME_CHANGED = "volume_changed"
    LOOP_CHANGED = "loop_changed"
    AUTOPLAY_CHANGED = "autoplay_changed"
    VOICE_CHANGED = "voice_changed"


@dataclass(frozen=True)
class MusicStateEvent:
    guild_id: int
    event_type: MusicStateEventType
    track: Track | None = None
    notice: str | None = None


MusicStateListener = Callable[[MusicStateEvent], object]


class MusicStateEventBus:
    def __init__(self) -> None:
        self._listeners: list[MusicStateListener] = []

    def subscribe(self, listener: MusicStateListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: MusicStateListener) -> bool:
        if listener not in self._listeners:
            return False
        self._listeners.remove(listener)
        return True

    def _apply_clock(self, event: MusicStateEvent) -> None:
        event_type = event.event_type
        if event_type == MusicStateEventType.TRACK_STARTED:
            playback_clock_manager.start(event.guild_id, event.track)
        elif event_type == MusicStateEventType.PAUSED:
            playback_clock_manager.pause(event.guild_id)
        elif event_type == MusicStateEventType.RESUMED:
            playback_clock_manager.resume(event.guild_id)
        elif event_type in {
            MusicStateEventType.TRACK_ENDED,
            MusicStateEventType.PLAYBACK_ERROR,
            MusicStateEventType.STOPPED,
        }:
            playback_clock_manager.stop(event.guild_id)

    def _deliver(self, event: MusicStateEvent) -> None:
        self._apply_clock(event)

        for listener in tuple(self._listeners):
            try:
                result = listener(event)
                if inspect.isawaitable(result):
                    asyncio.create_task(result)
            except Exception:
                logger.exception(
                    "Music state listener failed for guild %s (%s)",
                    event.guild_id,
                    event.event_type.value,
                )

    def emit(self, event: MusicStateEvent) -> None:
        """Deliver on the Discord event loop when called from the voice thread."""

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
            logger.exception("Could not dispatch music state event")

    def clear(self) -> None:
        self._listeners.clear()

    def listener_count(self) -> int:
        return len(self._listeners)


music_state_event_bus = MusicStateEventBus()


def emit_music_state_event(
    guild_id: int,
    event_type: MusicStateEventType,
    *,
    track: Track | None = None,
    notice: str | None = None,
) -> None:
    music_state_event_bus.emit(
        MusicStateEvent(
            guild_id=guild_id,
            event_type=event_type,
            track=track,
            notice=notice,
        )
    )
