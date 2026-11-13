"""Safe, guild-scoped ownership hand-off between CTX Music and CTX Voice/TTS."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from music.backend_manager import playback_backend_manager
from music.operation_lock import get_guild_operation_lock
from music.playback_clock import playback_clock_manager
from music.player import PlayerStatus, music_player_manager
from music.session import music_session_manager
from music.state_events import MusicStateEventType, emit_music_state_event
from music.stream_refresher import refresh_track_stream
from music.track import Track


@dataclass(frozen=True)
class MusicInterruption:
    guild_id: int
    track: Track | None
    position_seconds: int
    was_paused: bool
    active: bool


_tts_locks: dict[int, asyncio.Lock] = {}
_active_tts_guilds: set[int] = set()
_pending_terminal_tasks: dict[int, set[asyncio.Task]] = {}


def _get_tts_lock(guild_id: int) -> asyncio.Lock:
    return _tts_locks.setdefault(guild_id, asyncio.Lock())


def is_tts_active(guild_id: int) -> bool:
    return guild_id in _active_tts_guilds


def register_terminal_operation_during_tts(guild_id: int) -> None:
    """Tell the active hand-off not to restart audio before SKIP/STOP runs."""

    if not is_tts_active(guild_id):
        return
    task = asyncio.current_task()
    if task is None:
        return
    tasks = _pending_terminal_tasks.setdefault(guild_id, set())
    tasks.add(task)

    def discard(completed: asyncio.Task) -> None:
        pending = _pending_terminal_tasks.get(guild_id)
        if pending is None:
            return
        pending.discard(completed)
        if not pending:
            _pending_terminal_tasks.pop(guild_id, None)

    task.add_done_callback(discard)


def _has_pending_terminal_operation(guild_id: int) -> bool:
    return any(
        not task.done() for task in _pending_terminal_tasks.get(guild_id, set())
    )


async def _begin_tts_interruption_locked(guild_id: int) -> MusicInterruption:
    """Begin hand-off while the caller owns the guild operation lock."""

    session = music_session_manager.get_session(guild_id)
    track = session.current_track
    if track is None:
        return MusicInterruption(guild_id, None, 0, False, False)

    backend = playback_backend_manager.get_backend(guild_id)
    interrupt = getattr(backend, "interrupt_for_external_audio", None)
    if not callable(interrupt):
        return MusicInterruption(guild_id, track, 0, session.state.paused, False)

    position = playback_clock_manager.elapsed_seconds(guild_id)
    was_paused = session.state.paused
    result = await interrupt()
    if not result.success:
        return MusicInterruption(guild_id, track, position, was_paused, False)

    session.pause()
    music_player_manager.get_player(guild_id).status = PlayerStatus.PAUSED
    emit_music_state_event(
        guild_id,
        MusicStateEventType.PAUSED,
        track=track,
        notice="CTX Voice tomó el canal temporalmente.",
    )
    return MusicInterruption(guild_id, track, position, was_paused, True)


def _mark_restore_failure(guild_id: int, track: Track, notice: str) -> None:
    session = music_session_manager.get_session(guild_id)
    if session.current_track is track:
        session.queue.current = None
    music_player_manager.get_player(guild_id).status = PlayerStatus.IDLE
    emit_music_state_event(
        guild_id,
        MusicStateEventType.PLAYBACK_ERROR,
        track=track,
        notice=notice,
    )


async def _finish_tts_interruption_locked(
    interruption: MusicInterruption,
) -> bool:
    """Restore music while the caller still owns the guild operation lock."""

    if not interruption.active or interruption.track is None:
        return True

    guild_id = interruption.guild_id
    track = interruption.track
    session = music_session_manager.get_session(guild_id)
    if session.current_track is not track:
        return False

    refresh_result = await refresh_track_stream(track)
    if not refresh_result.success or not track.stream_url:
        _mark_restore_failure(
            guild_id,
            track,
            "No se pudo refrescar la música después de CTX Voice.",
        )
        return False

    backend = playback_backend_manager.get_backend(guild_id)
    play_from = getattr(backend, "play_from", None)
    if not callable(play_from):
        _mark_restore_failure(
            guild_id,
            track,
            "El backend no permite restaurar la música después de CTX Voice.",
        )
        return False

    result = await play_from(track, interruption.position_seconds)
    if not result.success:
        _mark_restore_failure(guild_id, track, result.message)
        return False

    player = music_player_manager.get_player(guild_id)
    if interruption.was_paused:
        pause_result = await backend.pause()
        if not pause_result.success:
            _mark_restore_failure(guild_id, track, pause_result.message)
            return False
        session.pause()
        player.status = PlayerStatus.PAUSED
        emit_music_state_event(
            guild_id,
            MusicStateEventType.PAUSED,
            track=track,
            notice="CTX Voice terminó; la música sigue pausada.",
        )
    else:
        session.resume()
        player.status = PlayerStatus.PLAYING
        emit_music_state_event(
            guild_id,
            MusicStateEventType.RESUMED,
            track=track,
            notice="CTX Voice terminó; música reanudada.",
        )
    return True


async def begin_tts_interruption(guild_id: int) -> MusicInterruption:
    """Compatibility API for a short, explicit music hand-off."""

    async with get_guild_operation_lock(guild_id):
        return await _begin_tts_interruption_locked(guild_id)


async def finish_tts_interruption(interruption: MusicInterruption) -> bool:
    """Compatibility API for restoring an explicit music hand-off."""

    if not interruption.active or interruption.track is None:
        return True
    async with get_guild_operation_lock(interruption.guild_id):
        return await _finish_tts_interruption_locked(interruption)


@asynccontextmanager
async def tts_audio_session(guild_id: int) -> AsyncIterator[MusicInterruption]:
    """Own the VoiceClient for the complete TTS duration.

    Music operations for this guild wait on the same operation lock. Other
    guilds remain independent. Restoration is attempted before ownership is
    released, including when TTS playback raises or the coroutine is cancelled.
    """

    async with _get_tts_lock(guild_id):
        operation_lock = get_guild_operation_lock(guild_id)
        await operation_lock.acquire()
        interruption = MusicInterruption(guild_id, None, 0, False, False)
        _active_tts_guilds.add(guild_id)
        try:
            interruption = await _begin_tts_interruption_locked(guild_id)
            yield interruption
        finally:
            try:
                if not _has_pending_terminal_operation(guild_id):
                    await _finish_tts_interruption_locked(interruption)
            finally:
                _active_tts_guilds.discard(guild_id)
                operation_lock.release()


def reset_audio_priority_runtime() -> None:
    """Forget test/shutdown-only coordination state."""

    _tts_locks.clear()
    _active_tts_guilds.clear()
    _pending_terminal_tasks.clear()
