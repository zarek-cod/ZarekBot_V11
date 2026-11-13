"""Safe ownership hand-off between CTX Music and short CTX Voice/TTS audio."""

from __future__ import annotations

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


async def begin_tts_interruption(guild_id: int) -> MusicInterruption:
    """Stop only the audio source while preserving the musical session."""

    async with get_guild_operation_lock(guild_id):
        session = music_session_manager.get_session(guild_id)
        track = session.current_track
        if track is None:
            return MusicInterruption(guild_id, None, 0, False, False)

        backend = playback_backend_manager.get_backend(guild_id)
        interrupt = getattr(backend, "interrupt_for_external_audio", None)
        if not callable(interrupt):
            return MusicInterruption(guild_id, track, 0, False, False)

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


async def finish_tts_interruption(interruption: MusicInterruption) -> bool:
    """Refresh and restore the interrupted track at its approximate position."""

    if not interruption.active or interruption.track is None:
        return True

    guild_id = interruption.guild_id
    track = interruption.track

    async with get_guild_operation_lock(guild_id):
        session = music_session_manager.get_session(guild_id)
        if session.current_track is not track:
            return False

        refresh_result = await refresh_track_stream(track)
        if not refresh_result.success or not track.stream_url:
            session.queue.current = None
            music_player_manager.get_player(guild_id).status = PlayerStatus.IDLE
            emit_music_state_event(
                guild_id,
                MusicStateEventType.PLAYBACK_ERROR,
                track=track,
                notice="No se pudo restaurar la música después de CTX Voice.",
            )
            return False

        backend = playback_backend_manager.get_backend(guild_id)
        play_from = getattr(backend, "play_from", None)
        if not callable(play_from):
            return False

        result = await play_from(track, interruption.position_seconds)
        if not result.success:
            emit_music_state_event(
                guild_id,
                MusicStateEventType.PLAYBACK_ERROR,
                track=track,
                notice=result.message,
            )
            return False

        player = music_player_manager.get_player(guild_id)
        if interruption.was_paused:
            await backend.pause()
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
