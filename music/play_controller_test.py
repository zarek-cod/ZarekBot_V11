"""
CTX V11
Prueba del controlador principal PLAY.

Utiliza:

- Pipeline real
- DirectAudioResolver
- VoiceController
- Queue
- MockPlaybackBackend

NO:
- Discord real
- FFmpeg real
- audio real
"""

import asyncio

from music.backend_manager import (
    playback_backend_manager,
)

from music.mock_backend import (
    MockPlaybackBackend,
)

from music.play_controller import (
    get_play_controller_summary,
    play_music_request,
)

from music.session import (
    music_session_manager,
)


async def run_test() -> dict:

    guild_id = 9500
    voice_channel_id = 999


    # ========================================================
    # BACKEND FALSO
    # ========================================================

    backend = (
        MockPlaybackBackend(
            guild_id
        )
    )


    playback_backend_manager.register_backend(
        guild_id,
        backend,
    )


    # ========================================================
    # PRIMER PLAY
    # ========================================================

    first = await play_music_request(

        guild_id=guild_id,

        voice_channel_id=voice_channel_id,

        query=(
            "https://example.com/"
            "musica/cancion_1.mp3"
        ),

        requester_id=123,

        requester_name="Zarek",
    )


    # ========================================================
    # SEGUNDO PLAY
    # ========================================================
    #
    # Como ya existe una canción reproduciéndose,
    # esta debe ir a la cola.
    #

    second = await play_music_request(

        guild_id=guild_id,

        voice_channel_id=voice_channel_id,

        query=(
            "https://example.com/"
            "musica/cancion_2.mp3"
        ),

        requester_id=456,

        requester_name="Centi",
    )


    # ========================================================
    # SESIÓN
    # ========================================================

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    return {

        "first_success":
            first.success,

        "first_started":
            first.started,

        "first_queued":
            first.queued,

        "first_track":
            (
                first.track.title
                if first.track
                else None
            ),

        "second_success":
            second.success,

        "second_started":
            second.started,

        "second_queued":
            second.queued,

        "second_position":
            second.position,

        "second_track":
            (
                second.track.title
                if second.track
                else None
            ),

        "voice_connected":
            session.state.connected,

        "current_track":
            (
                session.current_track.title
                if session.current_track
                else None
            ),

        "queue_size":
            session.queue.size(),

        "next_track":
            (
                session.queue.peek().title
                if session.queue.peek()
                else None
            ),

        "backend_state":
            backend.state.value,

        "backend_play_count":
            backend.play_count,

        "backend_channel":
            backend.connected_channel_id,

        "controller":
            get_play_controller_summary(),

        "play_controller_worked":
            (
                first.success
                and first.started
                and not first.queued
                and second.success
                and second.queued
                and not second.started
                and session.state.connected
                and session.queue.size() == 1
                and backend.play_count == 1
            ),
    }


if __name__ == "__main__":

    print(
        asyncio.run(
            run_test()
        )
    )