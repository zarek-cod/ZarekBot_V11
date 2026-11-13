"""
CTX V11
Prueba de SKIP con refresco real de YouTube.

NO utiliza Discord Voice real.
Utiliza MockPlaybackBackend.
"""

import asyncio

from music.backend_manager import (
    playback_backend_manager,
)

from music.mock_backend import (
    MockPlaybackBackend,
)

from music.player import (
    PlayerStatus,
    music_player_manager,
)

from music.session import (
    music_session_manager,
)

from music.skip_controller import (
    get_skip_controller_summary,
    skip_current_track,
)

from music.track import Track


async def run_test() -> dict:

    guild_id = 9400


    # ========================================================
    # SESIÓN
    # ========================================================

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
    # CANCIÓN ACTUAL
    # ========================================================

    current = Track(

        title="Cancion ACTUAL",

        query="actual",

        stream_url="mock-stream",

        guild_id=guild_id,

        requester_name="Zarek",
    )


    # ========================================================
    # CANCIÓN YOUTUBE SIN STREAM
    # ========================================================

    next_track = Track(

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

        guild_id=guild_id,

        requester_name="Zarek",

        source="youtube",
    )


    # ========================================================
    # COLA
    # ========================================================

    session.add_track(
        current
    )

    session.add_track(
        next_track
    )

    session.move_to_next()


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


    await backend.connect(
        999
    )


    await backend.play(
        current
    )


    player.status = (
        PlayerStatus.PLAYING
    )


    stream_before = bool(
        next_track.stream_url
    )


    # ========================================================
    # SKIP
    # ========================================================

    result = await skip_current_track(
        guild_id
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    return {

        "success":
            result.success,

        "skipped_track":
            (
                result.skipped_track.title
                if result.skipped_track
                else None
            ),

        "next_track":
            (
                result.next_track.title
                if result.next_track
                else None
            ),

        "next_started":
            result.next_started,

        "stream_before":
            stream_before,

        "stream_after":
            bool(
                next_track.stream_url
            ),

        "stream_refreshed":
            result.stream_refreshed,

        "backend_track":
            (
                backend.current_track.title
                if backend.current_track
                else None
            ),

        "play_count":
            backend.play_count,

        "stop_count":
            backend.stop_count,

        "player_status":
            player.status.value,

        "skip_controller":
            get_skip_controller_summary(),

        "skip_refresh_worked":
            (
                result.success
                and result.next_started
                and not stream_before
                and bool(next_track.stream_url)
                and backend.current_track
                is next_track
                and backend.play_count == 2
                and backend.stop_count == 1
            ),
    }


if __name__ == "__main__":

    print(
        asyncio.run(
            run_test()
        )
    )