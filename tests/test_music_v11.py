from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import discord
import pytest
from discord.ext import commands

import music.autoplay_recommendations as recommendations
import music.permissions as music_permissions
import music.playback_clock as clock_module
from commands.music.panel import (
    CTXMusicView,
    MusicPanelRegistry,
    build_music_help_embed,
    build_player_embed,
)
from config.hierarchy import HierarchyLevel
from music.audio_priority import begin_tts_interruption, finish_tts_interruption
from music.autoplay_controller import enable_autoplay
from music.auto_playback import start_prepared_track
from music.backend_manager import playback_backend_manager
from music.loop_controller import enable_loop
from music.mock_backend import MockPlaybackBackend
from music.operation_lock import reset_operation_locks
from music.pause_controller import pause_current_track
from music.play_controller import play_music_request
from music.playback_backend import PlaybackResult
from music.playback_clock import PlaybackClockManager, playback_clock_manager
from music.playback_events import emit_playback_error, emit_track_finished
from music.player import PlayerStatus, music_player_manager
from music.request_deduplicator import reset_request_deduplicator
from music.resume_controller import resume_current_track
from music.runtime import initialize_music_runtime, reset_music_runtime
from music.session import music_session_manager
from music.skip_controller import skip_current_track
from music.state_events import (
    MusicStateEventType,
    emit_music_state_event,
    music_state_event_bus,
)
from music.stop_controller import stop_music
from music.track import Track
from music.voice_controller import connect_to_voice, disconnect_from_voice
from music.volume_controller import set_music_volume


@pytest.fixture(autouse=True)
def clean_music_globals():
    reset_music_runtime()
    reset_operation_locks()
    reset_request_deduplicator()
    playback_backend_manager.clear()
    music_state_event_bus.clear()
    yield
    reset_music_runtime()
    reset_operation_locks()
    reset_request_deduplicator()
    music_state_event_bus.clear()


def make_track(
    guild_id: int,
    title: str,
    *,
    requester_id: int = 1,
    requester_name: str = "User",
) -> Track:
    slug = title.lower().replace(" ", "-")
    return Track(
        title=title,
        query=f"https://example.com/{slug}.mp3",
        url=f"https://example.com/{slug}.mp3",
        stream_url=f"https://example.com/{slug}.mp3",
        duration=240,
        requester_id=requester_id,
        requester_name=requester_name,
        guild_id=guild_id,
        source="direct",
    )


async def wait_for_tasks() -> None:
    for _ in range(8):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_concurrent_play_uses_one_fifo_guild_queue():
    guild_id = 11001
    backend = MockPlaybackBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)

    results = await asyncio.gather(
        *(play_music_request(
            guild_id, 501, f"https://example.com/song-{index}.mp3",
            100 + index, f"Member {index}", request_id=f"play-{index}",
        )
        for index in range(3))
    )

    session = music_session_manager.get_session(guild_id)
    assert sum(result.started for result in results) == 1
    assert [result.position for result in results if result.queued] == [1, 2]
    assert [track.requester_id for track in session.queue.get_all()] == [101, 102]
    assert backend.play_count == 1


@pytest.mark.asyncio
async def test_duplicate_discord_request_is_rejected():
    guild_id = 11002
    backend = MockPlaybackBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)
    first = await play_music_request(
        guild_id, 501, "https://example.com/a.mp3", 1, "A", request_id=77
    )
    duplicate = await play_music_request(
        guild_id, 501, "https://example.com/a.mp3", 1, "A", request_id=77
    )
    assert first.success
    assert not duplicate.success
    assert "ya fue procesada" in duplicate.message
    assert backend.play_count == 1


@pytest.mark.asyncio
async def test_pause_resume_volume_stop_and_clock_integration():
    guild_id = 11003
    backend = MockPlaybackBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)
    started = await play_music_request(
        guild_id, 501, "https://example.com/a.mp3", 1, "A"
    )
    assert started.started
    assert playback_clock_manager.get_state(guild_id).running

    paused = await pause_current_track(guild_id)
    assert paused.success and playback_clock_manager.get_state(guild_id).paused
    resumed = await resume_current_track(guild_id)
    assert resumed.success and playback_clock_manager.get_state(guild_id).running
    volume = await set_music_volume(guild_id, 130)
    assert volume.success and volume.final_volume == 100 and backend.volume == 100
    stopped = await stop_music(guild_id)
    assert stopped.success
    assert music_session_manager.get_session(guild_id).current_track is None
    assert playback_clock_manager.elapsed_seconds(guild_id) == 0


def test_playback_clock_freezes_and_resumes(monkeypatch):
    values = iter([100.0, 110.0, 112.0, 122.0, 125.0, 125.0, 125.0])
    monkeypatch.setattr(clock_module.time, "monotonic", lambda: next(values))
    manager = PlaybackClockManager()
    manager.start(1, make_track(1, "Clock"))
    assert manager.elapsed_seconds(1) == 10
    manager.pause(1)
    assert manager.elapsed_seconds(1) == 12
    manager.resume(1)
    assert manager.elapsed_seconds(1) == 15
    assert "00:15" in manager.progress_text(1, 60)


@pytest.mark.asyncio
async def test_natural_finish_advances_and_starts_next_track():
    guild_id = 11004
    client = discord.Client(intents=discord.Intents.none())
    initialize_music_runtime(client)
    playback_backend_manager.clear()
    playback_backend_manager.set_factory(MockPlaybackBackend)
    session = music_session_manager.get_session(guild_id)
    first, second = make_track(guild_id, "First"), make_track(guild_id, "Second")
    session.add_track(first)
    session.add_track(second)
    session.move_to_next()
    backend = playback_backend_manager.get_backend(guild_id)
    await backend.connect(501)
    await backend.play(first)
    music_player_manager.get_player(guild_id).status = PlayerStatus.PLAYING

    emit_track_finished(guild_id, first)
    await wait_for_tasks()
    assert session.current_track is second
    assert backend.current_track is second
    assert backend.play_count == 2


@pytest.mark.asyncio
async def test_loop_repeats_without_consuming_manual_queue():
    guild_id = 11005
    client = discord.Client(intents=discord.Intents.none())
    initialize_music_runtime(client)
    playback_backend_manager.clear()
    playback_backend_manager.set_factory(MockPlaybackBackend)
    session = music_session_manager.get_session(guild_id)
    first, second = make_track(guild_id, "Loop"), make_track(guild_id, "Waiting")
    session.add_track(first)
    session.add_track(second)
    session.move_to_next()
    backend = playback_backend_manager.get_backend(guild_id)
    await backend.connect(501)
    await backend.play(first)
    await enable_loop(guild_id)

    emit_track_finished(guild_id, first)
    await wait_for_tasks()
    assert session.current_track is first
    assert session.queue.peek() is second
    assert backend.play_count == 2


@pytest.mark.asyncio
async def test_playback_error_recovers_with_next_manual_track():
    guild_id = 11006
    client = discord.Client(intents=discord.Intents.none())
    initialize_music_runtime(client)
    playback_backend_manager.clear()
    playback_backend_manager.set_factory(MockPlaybackBackend)
    session = music_session_manager.get_session(guild_id)
    first, second = make_track(guild_id, "Broken"), make_track(guild_id, "Recovery")
    session.add_track(first)
    session.add_track(second)
    session.move_to_next()
    backend = playback_backend_manager.get_backend(guild_id)
    await backend.connect(501)
    await backend.play(first)

    emit_playback_error(guild_id, first, RuntimeError("ffmpeg failed"))
    await wait_for_tasks()
    assert session.current_track is second
    assert backend.current_track is second
    assert backend.play_count == 2


@pytest.mark.asyncio
async def test_stale_finish_cannot_replace_new_track():
    guild_id = 11007
    client = discord.Client(intents=discord.Intents.none())
    initialize_music_runtime(client)
    playback_backend_manager.clear()
    playback_backend_manager.set_factory(MockPlaybackBackend)
    session = music_session_manager.get_session(guild_id)
    old, current = make_track(guild_id, "Old"), make_track(guild_id, "Current")
    session.queue.current = current
    backend = playback_backend_manager.get_backend(guild_id)
    await backend.connect(501)
    await backend.play(current)

    emit_track_finished(guild_id, old)
    await wait_for_tasks()
    assert session.current_track is current
    assert backend.current_track is current
    assert backend.play_count == 1


@pytest.mark.asyncio
async def test_skip_preserves_fifo_and_resets_clock():
    guild_id = 11008
    backend = MockPlaybackBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)
    await backend.connect(501)
    session = music_session_manager.get_session(guild_id)
    first, second = make_track(guild_id, "One"), make_track(guild_id, "Two")
    session.queue.current = first
    session.add_track(second)
    await backend.play(first)
    music_player_manager.get_player(guild_id).status = PlayerStatus.PLAYING
    emit_music_state_event(guild_id, MusicStateEventType.TRACK_STARTED, track=first)

    result = await skip_current_track(guild_id)
    assert result.success and result.next_track is second and result.next_started
    assert session.current_track is second
    assert playback_clock_manager.get_state(guild_id).track_key == second.url


@pytest.mark.asyncio
async def test_autoplay_never_overrides_pending_manual_queue():
    guild_id = 11009
    session = music_session_manager.get_session(guild_id)
    await enable_autoplay(guild_id)
    finished = make_track(guild_id, "Finished")
    session.add_track(make_track(guild_id, "Manual"))
    assert not await recommendations.continue_with_autoplay(guild_id, finished)
    assert session.queue.peek().title == "Manual"


@pytest.mark.asyncio
async def test_late_autoplay_result_is_invalidated(monkeypatch):
    guild_id = 11010
    session = music_session_manager.get_session(guild_id)
    await enable_autoplay(guild_id)
    finished = make_track(guild_id, "Finished")
    release = asyncio.Event()

    async def delayed_recommendation(*args, **kwargs):
        await release.wait()
        return make_track(guild_id, "Late")

    monkeypatch.setattr(recommendations, "_find_recommendation", delayed_recommendation)
    generation = recommendations._current_generation(guild_id)
    task = asyncio.create_task(
        recommendations.continue_with_autoplay(
            guild_id, finished, generation=generation
        )
    )
    await asyncio.sleep(0.45)
    recommendations.cancel_pending_autoplay(guild_id)
    release.set()
    assert not await task
    assert session.current_track is None


def test_permissions_allow_real_requests_but_only_hierarchy_controls(monkeypatch):
    class FakeMember:
        def __init__(self, *, bot: bool = False):
            self.bot = bot

    monkeypatch.setattr(music_permissions.discord, "Member", FakeMember)
    level = {"value": HierarchyLevel.SIMPLE_MORTAL}
    monkeypatch.setattr(
        music_permissions,
        "resolve_member_hierarchy",
        lambda member: SimpleNamespace(level=level["value"]),
    )
    member = FakeMember()
    assert music_permissions.can_request_music(member)
    assert not music_permissions.can_skip(member)
    level["value"] = HierarchyLevel.CREADOR
    assert music_permissions.can_skip(member)
    assert not music_permissions.can_request_music(FakeMember(bot=True))


@pytest.mark.asyncio
async def test_panel_has_real_controls_progress_and_help():
    guild_id = 11011
    track = make_track(guild_id, "Song — Artist", requester_name="Zarek")
    music_session_manager.get_session(guild_id).queue.current = track
    emit_music_state_event(guild_id, MusicStateEventType.TRACK_STARTED, track=track)
    embed = build_player_embed(guild_id)
    view = CTXMusicView(guild_id)
    custom_ids = {
        item.custom_id
        for item in view.walk_children()
        if getattr(item, "custom_id", None)
    }
    assert len(custom_ids) == 9
    assert "ctx_music:pause_resume" in custom_ids
    assert isinstance(view, discord.ui.LayoutView)
    assert "Components V2" in embed.footer.text
    assert "Song" in embed.description
    assert build_music_help_embed().title == "CTX MUSIC · Ayuda"


@pytest.mark.asyncio
async def test_panel_registry_reuses_one_message(monkeypatch, tmp_path):
    import commands.music.panel as panel_module

    monkeypatch.setattr(panel_module, "PANEL_STORE", tmp_path / "panels.json")
    registry = MusicPanelRegistry()
    registry._save = lambda: None

    class FakeMessage:
        id = 99
        channel = SimpleNamespace(id=88)
        jump_url = "https://discord.test/message"

        async def edit(self, **kwargs):
            return self

    message = FakeMessage()

    class FakeChannel:
        def __init__(self):
            self.sent = 0

        async def send(self, **kwargs):
            self.sent += 1
            return message

    channel = FakeChannel()
    first, created = await registry.get_or_create(11012, channel)
    assert created and first is message and channel.sent == 1

    async def fetch(ref):
        return message

    monkeypatch.setattr(registry, "_fetch_message", fetch)
    second, created = await registry.get_or_create(11012, channel)
    assert not created and second is message and channel.sent == 1


def test_panel_reference_survives_restart(monkeypatch, tmp_path):
    import commands.music.panel as panel_module

    store = tmp_path / "panels.json"
    store.write_text(
        json.dumps({"44": {"channel_id": 55, "message_id": 66}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(panel_module, "PANEL_STORE", store)
    registry = MusicPanelRegistry()
    assert registry.references[44].channel_id == 55
    assert registry.references[44].message_id == 66


@pytest.mark.asyncio
async def test_panel_extension_registers_player_and_musichelp_without_duplicates():
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    await bot.load_extension("commands.music.panel")
    slash_names = [command.name for command in bot.tree.get_commands()]
    assert slash_names.count("player") == 1
    assert slash_names.count("musichelp") == 1
    assert bot.get_command("ctx_player") is not None
    assert bot.get_command("ctx_musichelp") is not None
    await bot.unload_extension("commands.music.panel")
    await bot.close()


@pytest.mark.asyncio
async def test_tts_interruption_restores_music_without_advancing_queue():
    guild_id = 11013
    backend = MockPlaybackBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)
    await backend.connect(501)
    session = music_session_manager.get_session(guild_id)
    track = make_track(guild_id, "Speaking Test")
    waiting = make_track(guild_id, "Still Waiting")
    session.queue.current = track
    session.add_track(waiting)
    await backend.play(track)
    session.mark_connected()
    music_player_manager.get_player(guild_id).status = PlayerStatus.PLAYING
    emit_music_state_event(guild_id, MusicStateEventType.TRACK_STARTED, track=track)

    interruption = await begin_tts_interruption(guild_id)
    assert interruption.active and session.current_track is track
    assert await finish_tts_interruption(interruption)
    assert session.current_track is track
    assert session.queue.peek() is waiting
    assert backend.current_track is track
    assert backend.play_count == 2


@pytest.mark.asyncio
async def test_multiple_guilds_remain_independent():
    backends = {}
    for guild_id in (11014, 11015):
        backend = MockPlaybackBackend(guild_id)
        backends[guild_id] = backend
        playback_backend_manager.register_backend(guild_id, backend)
        await play_music_request(
            guild_id, guild_id + 1, f"https://example.com/{guild_id}.mp3",
            guild_id, f"User {guild_id}",
        )
    await set_music_volume(11014, 20)
    assert music_session_manager.get_session(11014).state.volume == 20
    assert music_session_manager.get_session(11015).state.volume == 70
    assert backends[11014].current_track is not backends[11015].current_track


class RejectingBackend(MockPlaybackBackend):
    async def play(self, track: Track) -> PlaybackResult:
        return PlaybackResult(False, "play", "simulated stream failure")


@pytest.mark.asyncio
async def test_failed_first_stream_rolls_back_current_track():
    guild_id = 11016
    backend = RejectingBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)
    result = await play_music_request(
        guild_id, 501, "https://example.com/failure.mp3", 1, "A"
    )
    assert not result.success
    assert music_session_manager.get_session(guild_id).current_track is None


@pytest.mark.asyncio
async def test_voice_disconnect_and_reconnect_with_mock_backend():
    guild_id = 11017
    backend = MockPlaybackBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)
    assert (await connect_to_voice(guild_id, 501)).success
    assert (await disconnect_from_voice(guild_id)).success
    assert (await connect_to_voice(guild_id, 502)).success
    assert backend.connected_channel_id == 502
