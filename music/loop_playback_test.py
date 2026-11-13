"""
CTX V11
Prueba integral de LOOP real.
"""

import asyncio

import discord

from music.backend_manager import (
    playback_backend_manager,
)

from music.loop_controller import (
    enable_loop,
)

from music.mock_backend import (
    MockPlaybackBackend,
)

from music.playback_events import (
    emit_track_finished,
)

from music.player import (
    PlayerStatus,
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


async def run_loop_test() -> dict:

    guild_id = 8001

    client = discord.Client(
        intents=discord.Intents.none()
    )


    # Inicializa listeners + scheduler
    initialize_music_runtime(
        client
    )


    # Sustituimos Discord real por backend falso
    playback_backend_manager.clear()

    playback_backend_manager.set_factory(
        lambda current_guild_id: (
            MockPlaybackBackend(
                current_guild_id
            )
        )
    )


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
    # DOS CANCIONES
    # ========================================================

    first = Track(
        title="Cancion LOOP",
        query="loop",
        guild_id=guild_id,
    )


    second = Track(
        title="Cancion SIGUIENTE",
        query="next",
        guild_id=guild_id,
    )


    session.add_track(
        first
    )

    session.add_track(
        second
    )


    session.move_to_next()


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


    await backend.play(
        session.current_track
    )


    player.status = (
        PlayerStatus.PLAYING
    )


    # ========================================================
    # ACTIVAR LOOP
    # ========================================================

    await enable_loop(
        guild_id
    )


    before_queue_size = (
        session.queue.size()
    )


    # ========================================================
    # SIMULAR FIN DE CANCIÓN
    # ========================================================

    emit_track_finished(
        guild_id,
        first,
    )


    # AutoPlayback crea una Task.
    await asyncio.sleep(0)
    await asyncio.sleep(0)


    result = {

        "loop_enabled":
            session.state.loop_enabled,

        "current_track":
            (
                session.current_track.title
                if session.current_track
                else None
            ),

        "backend_track":
            (
                backend.current_track.title
                if backend.current_track
                else None
            ),

        "queue_before":
            before_queue_size,

        "queue_after":
            session.queue.size(),

        "next_waiting":
            (
                session.queue.peek().title
                if session.queue.peek()
                else None
            ),

        "play_count":
            backend.play_count,

        "player_status":
            player.status.value,

        "loop_worked":
            (
                session.current_track
                is first
                and backend.current_track
                is first
                and session.queue.peek()
                is second
                and backend.play_count == 2
            ),
    }


    reset_music_runtime()


    return result


if __name__ == "__main__":

    print(
        asyncio.run(
            run_loop_test()
        )
    )