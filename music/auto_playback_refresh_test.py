"""
CTX V11
Prueba de Stream Refresh justo antes de PLAY.

Usa:
- YouTube real
- yt-dlp real
- MockBackend

NO:
- entra a Discord Voice
- ejecuta FFmpeg
- reproduce sonido real
"""

import asyncio

import discord

from music.auto_playback import (
    get_auto_playback_summary,
    start_prepared_track,
)

from music.backend_manager import (
    playback_backend_manager,
)

from music.mock_backend import (
    MockPlaybackBackend,
)

from music.player import (
    music_player_manager,
)

from music.runtime import (
    initialize_music_runtime,
    reset_music_runtime,
)

from music.session import (
    music_session_manager,
)

from music.track import Track


async def run_test() -> dict:

    guild_id = 9300


    # ========================================================
    # RUNTIME
    # ========================================================

    client = discord.Client(
        intents=discord.Intents.none()
    )


    initialize_music_runtime(
        client
    )


    # ========================================================
    # BACKEND FALSO
    # ========================================================

    playback_backend_manager.clear()


    playback_backend_manager.set_factory(
        lambda current_guild_id: (
            MockPlaybackBackend(
                current_guild_id
            )
        )
    )


    backend = (
        playback_backend_manager.get_backend(
            guild_id
        )
    )


    assert isinstance(
        backend,
        MockPlaybackBackend
    )


    await backend.connect(
        999
    )


    # ========================================================
    # TRACK YOUTUBE SIN STREAM
    # ========================================================
    #
    # Simulamos una canción que estuvo mucho
    # tiempo esperando y perdió su stream.
    #

    track = Track(

        title=(
            "The Weeknd - "
            "Blinding Lights"
        ),

        query=(
            "Blinding Lights "
            "The Weeknd"
        ),

        url=(
            "https://www.youtube.com/"
            "watch?v=4NRXx6U8ABQ"
        ),

        stream_url=None,

        requester_id=123,

        requester_name="Zarek",

        guild_id=guild_id,

        voice_channel_id=999,

        source="youtube",
    )


    # ========================================================
    # SESIÓN
    # ========================================================

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    session.queue.current = (
        track
    )


    # ========================================================
    # ANTES
    # ========================================================

    before_has_stream = bool(
        track.stream_url
    )


    # ========================================================
    # PLAY
    # ========================================================

    started = (
        await start_prepared_track(
            guild_id
        )
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    player = (
        music_player_manager.get_player(
            guild_id
        )
    )


    result = {

        "stream_before":
            before_has_stream,

        "started":
            started,

        "stream_after":
            bool(
                track.stream_url
            ),

        "backend_track":
            (
                backend.current_track.title
                if backend.current_track
                else None
            ),

        "backend_play_count":
            backend.play_count,

        "player_status":
            player.status.value,

        "auto_playback":
            get_auto_playback_summary(),

        "refresh_before_playback_worked":
            (
                not before_has_stream
                and bool(track.stream_url)
                and started
                and backend.play_count == 1
            ),
    }


    reset_music_runtime()


    return result


if __name__ == "__main__":

    print(
        asyncio.run(
            run_test()
        )
    )