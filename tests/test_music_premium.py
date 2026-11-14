from __future__ import annotations

import asyncio
import inspect
import time
import warnings
from types import SimpleNamespace

import discord
import pytest

import commands.music.panel as panel_module
from commands.music.panel import (
    CTXMusicView,
    MusicPanelRegistry,
    PanelReference,
    build_player_presentation,
)
from commands.music.play import _format_play_result
from music.audio_priority import is_tts_active, tts_audio_session
from music.backend_manager import playback_backend_manager
from music.mock_backend import MockPlaybackBackend
from music.pause_controller import pause_current_track
from music.play_controller import PlayRequestResult, play_music_request
from music.playback_backend import PlaybackResult, PlaybackState
from music.player import PlayerStatus, music_player_manager
from music.runtime import reset_music_runtime
from music.session import music_session_manager
from music.skip_controller import skip_current_track
from music.state_events import MusicStateEvent, MusicStateEventType, emit_music_state_event
from music.stop_controller import stop_music
from music.track import Track


@pytest.fixture(autouse=True)
def clean_music_runtime():
    reset_music_runtime()
    yield
    reset_music_runtime()


def premium_track(
    guild_id: int,
    title: str,
    *,
    thumbnail: str | None = "https://example.com/cover.jpg",
    requester_name: str = "Zarek",
) -> Track:
    return Track(
        title=title,
        query="https://example.com/audio.mp3",
        url="https://example.com/watch",
        stream_url="https://example.com/audio.mp3",
        duration=263,
        thumbnail=thumbnail,
        requester_id=10,
        requester_name=requester_name,
        guild_id=guild_id,
        voice_channel_id=501,
        source="direct",
    )


def button_map(view: CTXMusicView) -> dict[str, discord.ui.Button]:
    return {
        item.custom_id: item
        for item in view.walk_children()
        if isinstance(item, discord.ui.Button) and item.custom_id
    }


@pytest.mark.asyncio
async def test_components_v2_panel_uses_gallery_and_state_aware_controls():
    guild_id = 12001
    session = music_session_manager.get_session(guild_id)
    current = premium_track(guild_id, "Blinding Lights — The Weeknd")
    upcoming = premium_track(guild_id, "Starboy — The Weeknd")
    session.queue.current = current
    session.add_track(upcoming)
    session.mark_connected()
    emit_music_state_event(guild_id, MusicStateEventType.TRACK_STARTED, track=current)

    view = CTXMusicView(guild_id)
    presentation = view.presentation
    controls = button_map(view)

    assert isinstance(view, discord.ui.LayoutView)
    assert isinstance(view.children[0], discord.ui.Container)
    assert any(isinstance(item, discord.ui.MediaGallery) for item in view.walk_children())
    assert presentation.media_url == current.thumbnail
    assert "Blinding Lights" in presentation.track_block
    assert "Starboy" in presentation.next_block
    assert "LIVE" in presentation.header
    assert len(controls) == 9
    assert view.total_children_count <= 40
    assert view.content_length() <= 4000
    assert not controls["ctx_music:pause_resume"].disabled
    assert controls["ctx_music:autoplay"].label == "Auto · OFF"
    assert view.is_persistent()


def test_idle_panel_is_compact_and_disables_impossible_actions():
    guild_id = 12002
    view = CTXMusicView(guild_id)
    controls = button_map(view)

    assert view.presentation.media_url is None
    assert "EN ESPERA" in view.presentation.track_block
    assert controls["ctx_music:pause_resume"].disabled
    assert controls["ctx_music:skip"].disabled
    assert controls["ctx_music:stop"].disabled
    assert controls["ctx_music:volume_down"].disabled
    assert not controls["ctx_music:queue"].disabled
    assert not controls["ctx_music:refresh"].disabled


def test_panel_rebuild_updates_artwork_title_and_next_track():
    guild_id = 12003
    session = music_session_manager.get_session(guild_id)
    first = premium_track(
        guild_id, "First Song — Artist A", thumbnail="https://example.com/a.jpg"
    )
    second = premium_track(
        guild_id, "Second Song — Artist B", thumbnail="https://example.com/b.jpg"
    )
    session.queue.current = first
    session.add_track(second)
    session.mark_connected()
    before = build_player_presentation(guild_id)

    session.queue.current = second
    session.queue.clear()
    after = build_player_presentation(guild_id)

    assert before.media_url.endswith("a.jpg")
    assert "First Song" in before.track_block
    assert "Second Song" in before.next_block
    assert after.media_url.endswith("b.jpg")
    assert "Second Song" in after.track_block
    assert after.next_block is None


@pytest.mark.asyncio
async def test_simultaneous_player_requests_create_only_one_message(monkeypatch, tmp_path):
    monkeypatch.setattr(panel_module, "PANEL_STORE", tmp_path / "panels.json")
    registry = MusicPanelRegistry()
    registry._save = lambda: None

    class FakeMessage:
        id = 991
        channel = SimpleNamespace(id=881)
        jump_url = "https://discord.test/panel"
        flags = SimpleNamespace(components_v2=True)

        async def edit(self, **kwargs):
            return self

    message = FakeMessage()

    class FakeChannel:
        def __init__(self):
            self.sent = 0

        async def send(self, **kwargs):
            self.sent += 1
            await asyncio.sleep(0)
            return message

    channel = FakeChannel()
    results = await asyncio.gather(
        registry.get_or_create(12004, channel),
        registry.get_or_create(12004, channel),
        registry.get_or_create(12004, channel),
    )

    assert channel.sent == 1
    assert sum(created for _, created in results) == 1
    assert all(returned is message for returned, _ in results)


@pytest.mark.asyncio
async def test_restore_upgrades_legacy_embed_to_persistent_components_v2(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(panel_module, "PANEL_STORE", tmp_path / "panels.json")
    registry = MusicPanelRegistry()
    registry.references[12005] = PanelReference(12005, 88, 99)
    edits: list[dict] = []

    class FakeMessage:
        flags = SimpleNamespace(components_v2=False)

        async def edit(self, **kwargs):
            edits.append(kwargs)
            self.flags = SimpleNamespace(components_v2=True)
            return self

    message = FakeMessage()

    class FakeBot:
        def __init__(self):
            self.views = []

        def add_view(self, view, *, message_id):
            self.views.append((view, message_id))

    registry.bot = FakeBot()

    async def fetch(ref):
        return message

    monkeypatch.setattr(registry, "_fetch_message", fetch)
    monkeypatch.setattr(registry, "start_progress_updates", lambda: None)
    await registry.restore()

    assert len(edits) == 1
    assert edits[0]["content"] is None
    assert edits[0]["embed"] is None
    assert edits[0]["attachments"] == []
    assert isinstance(edits[0]["view"], discord.ui.LayoutView)
    assert registry.bot.views[0][1] == 99


@pytest.mark.asyncio
async def test_state_event_refreshes_the_existing_panel(monkeypatch, tmp_path):
    monkeypatch.setattr(panel_module, "PANEL_STORE", tmp_path / "panels.json")
    monkeypatch.setattr(panel_module, "PANEL_DEBOUNCE_SECONDS", 0.0)
    registry = MusicPanelRegistry()
    registry._save = lambda: None
    registry.references[12006] = PanelReference(12006, 88, 99)
    rendered = []

    class FakeMessage:
        flags = SimpleNamespace(components_v2=True)

        async def edit(self, **kwargs):
            rendered.append(kwargs["view"].presentation)
            return self

    registry._messages[12006] = FakeMessage()
    track = premium_track(12006, "Automatic Update — Artist")
    session = music_session_manager.get_session(12006)
    session.queue.current = track
    session.mark_connected()
    registry.on_state_event(
        MusicStateEvent(12006, MusicStateEventType.TRACK_STARTED, track=track)
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert len(rendered) == 1
    assert "Automatic Update" in rendered[0].track_block


@pytest.mark.asyncio
async def test_refresh_button_does_not_override_discord_internal_refresh(monkeypatch):
    guild_id = 12014
    view = CTXMusicView(guild_id)
    refreshes = []

    async def refresh_coalesced(requested_guild_id, *, notice=None):
        refreshes.append((requested_guild_id, notice))
        return True

    monkeypatch.setattr(
        panel_module.panel_registry, "refresh_coalesced", refresh_coalesced
    )

    class FakeResponse:
        def __init__(self):
            self.deferred = False

        async def defer(self):
            self.deferred = True

    response = FakeResponse()
    interaction = SimpleNamespace(response=response, message=None)
    refresh_button = button_map(view)["ctx_music:refresh"]

    assert refresh_button.callback.__name__ == "_on_refresh_button"
    await refresh_button.callback(interaction)
    assert response.deferred
    assert refreshes == [(guild_id, "Panel sincronizado.")]

    own_methods = {
        name
        for name, value in CTXMusicView.__dict__.items()
        if inspect.isfunction(value)
    }
    inherited_methods = {
        name
        for base in CTXMusicView.__mro__[1:]
        for name, value in base.__dict__.items()
        if inspect.isfunction(value)
    }
    private_collisions = {
        name
        for name in own_methods & inherited_methods
        if name.startswith("_") and not name.startswith("__")
    }
    assert private_collisions == set()

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = view._refresh([])
    assert result is None
    assert not inspect.isawaitable(result)
    assert not any("was never awaited" in str(item.message) for item in captured)


@pytest.mark.asyncio
async def test_panel_refresh_burst_is_coalesced_and_rate_limited(
    monkeypatch, tmp_path
):
    guild_id = 12015
    monkeypatch.setattr(panel_module, "PANEL_STORE", tmp_path / "panels.json")
    monkeypatch.setattr(panel_module, "PANEL_DEBOUNCE_SECONDS", 0.01)
    monkeypatch.setattr(panel_module, "PANEL_MIN_EDIT_INTERVAL_SECONDS", 0.03)
    registry = MusicPanelRegistry()
    registry._save = lambda: None
    registry.references[guild_id] = PanelReference(guild_id, 88, 99)
    rendered = []

    class FakeMessage:
        flags = SimpleNamespace(components_v2=True)

        async def edit(self, **kwargs):
            rendered.append((time.monotonic(), kwargs["view"].presentation))
            return self

    registry._messages[guild_id] = FakeMessage()
    started_at = time.monotonic()
    registry._last_edits[guild_id] = started_at

    for notice in ("first", "second", "latest"):
        registry.on_state_event(
            MusicStateEvent(
                guild_id,
                MusicStateEventType.QUEUE_CHANGED,
                notice=notice,
            )
        )

    task = registry._pending_updates[guild_id]
    assert await asyncio.wait_for(asyncio.shield(task), timeout=0.5)
    assert len(rendered) == 1
    assert rendered[0][0] - started_at >= 0.025
    assert "latest" in rendered[0][1].notice_block


def test_play_confirmation_is_compact_and_links_the_single_panel():
    track = premium_track(12007, "Fly Love — Jamie Foxx")
    result = PlayRequestResult(
        success=True,
        track=track,
        started=False,
        queued=True,
        position=3,
        connected=True,
        stream_ready=True,
        message="Agregada a la cola.",
    )
    message = _format_play_result(result, panel_url="https://discord.test/panel")

    assert "AGREGADA A LA COLA" not in message
    assert "CTX MUSIC —" not in message
    assert "posición `3`" in message
    assert "Abrir panel" in message
    assert message.count("\n") == 0


@pytest.mark.asyncio
async def test_play_waits_until_tts_releases_voice_ownership():
    guild_id = 12008
    backend = MockPlaybackBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)

    async with tts_audio_session(guild_id):
        task = asyncio.create_task(
            play_music_request(
                guild_id,
                501,
                "https://example.com/new.mp3",
                1,
                "Member",
            )
        )
        await asyncio.sleep(0)
        assert is_tts_active(guild_id)
        assert not task.done()

    result = await task
    assert result.started
    assert backend.current_track is result.track


async def _playing_session(guild_id: int) -> tuple[MockPlaybackBackend, Track, Track]:
    backend = MockPlaybackBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)
    await backend.connect(501)
    current = premium_track(guild_id, "Current — Artist")
    waiting = premium_track(guild_id, "Waiting — Artist")
    session = music_session_manager.get_session(guild_id)
    session.queue.current = current
    session.add_track(waiting)
    session.mark_connected()
    await backend.play(current)
    music_player_manager.get_player(guild_id).status = PlayerStatus.PLAYING
    emit_music_state_event(guild_id, MusicStateEventType.TRACK_STARTED, track=current)
    return backend, current, waiting


@pytest.mark.asyncio
async def test_stop_during_tts_does_not_restore_the_track_first():
    guild_id = 12009
    backend, _, _ = await _playing_session(guild_id)

    async with tts_audio_session(guild_id):
        task = asyncio.create_task(stop_music(guild_id))
        await asyncio.sleep(0)
        assert not task.done()

    result = await task
    assert result.success
    assert music_session_manager.get_session(guild_id).current_track is None
    assert backend.current_track is None
    assert backend.play_count == 1


@pytest.mark.asyncio
async def test_skip_during_tts_does_not_restore_the_old_track_first():
    guild_id = 12010
    backend, _, waiting = await _playing_session(guild_id)

    async with tts_audio_session(guild_id):
        task = asyncio.create_task(skip_current_track(guild_id))
        await asyncio.sleep(0)
        assert not task.done()

    result = await task
    assert result.success and result.next_track is waiting
    assert music_session_manager.get_session(guild_id).current_track is waiting
    assert backend.current_track is waiting
    assert backend.play_count == 2


@pytest.mark.asyncio
async def test_tts_preserves_an_already_paused_track_and_clock():
    guild_id = 12011
    backend, current, waiting = await _playing_session(guild_id)
    paused = await pause_current_track(guild_id)
    assert paused.success

    async with tts_audio_session(guild_id) as interruption:
        assert interruption.active and interruption.was_paused
        assert music_session_manager.get_session(guild_id).current_track is current

    session = music_session_manager.get_session(guild_id)
    assert session.state.paused
    assert backend.state == PlaybackState.PAUSED
    assert session.current_track is current
    assert session.queue.peek() is waiting


class RestoreFailBackend(MockPlaybackBackend):
    async def play_from(self, track, position_seconds):
        return PlaybackResult(False, "play", "simulated restore failure")


@pytest.mark.asyncio
async def test_tts_restore_failure_cleans_inconsistent_current_track():
    guild_id = 12012
    backend = RestoreFailBackend(guild_id)
    playback_backend_manager.register_backend(guild_id, backend)
    await backend.connect(501)
    track = premium_track(guild_id, "Broken Restore — Artist")
    session = music_session_manager.get_session(guild_id)
    session.queue.current = track
    session.mark_connected()
    await backend.play(track)
    emit_music_state_event(guild_id, MusicStateEventType.TRACK_STARTED, track=track)

    async with tts_audio_session(guild_id):
        pass

    assert session.current_track is None
    assert music_player_manager.get_player(guild_id).status == PlayerStatus.IDLE


@pytest.mark.asyncio
async def test_reserved_panel_button_rejects_normal_member(monkeypatch):
    guild_id = 12013
    view = CTXMusicView(guild_id)
    member = object.__new__(discord.Member)
    responses = []

    class FakeResponse:
        async def send_message(self, message, *, ephemeral):
            responses.append((message, ephemeral))

    interaction = SimpleNamespace(user=member, response=FakeResponse())
    monkeypatch.setattr(panel_module, "can_manage_music", lambda user: False)

    assert not await view._require_control(interaction)
    assert responses == [("No tienes permiso para controlar CTX Music.", True)]
