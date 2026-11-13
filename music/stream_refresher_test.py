"""
CTX V11
Prueba real del refresco de streams de YouTube.
"""

import asyncio

from music.pipeline import (
    process_music_request,
)

from music.resolver_setup import (
    configure_music_resolvers,
)

from music.session import (
    music_session_manager,
)

from music.stream_refresher import (
    refresh_track_stream,
    get_stream_refresher_summary,
)


async def run_stream_refresh_test() -> dict:

    guild_id = 9200


    # ========================================================
    # PROVEEDORES
    # ========================================================

    configure_music_resolvers()


    # ========================================================
    # CREAR TRACK REAL
    # ========================================================

    result = await process_music_request(

        query="Blinding Lights The Weeknd",

        requester_id=123,

        requester_name="Zarek",

        guild_id=guild_id,

        voice_channel_id=999,
    )


    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    track = (
        session.current_track
    )


    if track is None:

        return {
            "success": False,
            "error": "No se creó ningún Track.",
        }


    # ========================================================
    # GUARDAR DATOS IMPORTANTES
    # ========================================================

    requester_before = (
        track.requester_name
    )

    requester_id_before = (
        track.requester_id
    )

    guild_before = (
        track.guild_id
    )

    voice_before = (
        track.voice_channel_id
    )

    old_stream_exists = bool(
        track.stream_url
    )


    # ========================================================
    # SIMULAR STREAM VIEJO / PERDIDO
    # ========================================================

    track.stream_url = None


    # ========================================================
    # REFRESCAR
    # ========================================================

    refresh_result = (
        await refresh_track_stream(
            track
        )
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    return {

        "pipeline_success":
            result.success,

        "old_stream_existed":
            old_stream_exists,

        "stream_removed_for_test":
            True,

        "refresh_success":
            refresh_result.success,

        "refreshed":
            refresh_result.refreshed,

        "new_stream_available":
            bool(track.stream_url),

        "source":
            track.source,

        "requester_preserved":
            (
                track.requester_name
                == requester_before
            ),

        "requester_id_preserved":
            (
                track.requester_id
                == requester_id_before
            ),

        "guild_preserved":
            (
                track.guild_id
                == guild_before
            ),

        "voice_channel_preserved":
            (
                track.voice_channel_id
                == voice_before
            ),

        "ready_for_playback":
            bool(
                track.stream_url
            ),

        "refresher":
            get_stream_refresher_summary(),
    }


if __name__ == "__main__":

    print(
        asyncio.run(
            run_stream_refresh_test()
        )
    )