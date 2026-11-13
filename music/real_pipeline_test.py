"""
CTX V11
Prueba integral del pipeline musical REAL.

Comprueba:

Texto
   ↓
ResolverRegistry
   ↓
YouTubeResolver
   ↓
YouTube real
   ↓
ResolvedAudioSource
   ↓
Track
   ↓
MusicSession / Queue

NO:
- conecta a Discord Voice
- reproduce audio
- ejecuta FFmpeg
- contiene comandos
- contiene interfaz

IMPORTANTE:
No mostramos stream_url porque es una URL temporal.
"""

import asyncio

from music.pipeline import (
    pipeline_result_to_safe_dict,
    process_music_request,
)

from music.resolver_setup import (
    configure_music_resolvers,
)

from music.session import (
    music_session_manager,
)


# ============================================================
# PRUEBA
# ============================================================

async def run_real_pipeline_test() -> dict:

    guild_id = 9100

    # ========================================================
    # 1. CONFIGURAR PROVEEDORES
    # ========================================================

    configure_music_resolvers()


    # ========================================================
    # 2. SOLICITUD REAL
    # ========================================================

    result = await process_music_request(

        query="Blinding Lights The Weeknd",

        requester_id=123,

        requester_name="Zarek",

        guild_id=guild_id,

        voice_channel_id=999,
    )


    # ========================================================
    # 3. OBTENER SESIÓN
    # ========================================================

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    # ========================================================
    # 4. TRACK ACTUAL
    # ========================================================

    track = (
        session.current_track
    )


    # ========================================================
    # 5. RESULTADO SEGURO
    # ========================================================

    return {

        "pipeline":
            pipeline_result_to_safe_dict(
                result
            ),

        "success":
            result.success,

        "source":
            (
                result.source.source_type.value
                if result.source
                else None
            ),

        "has_stream":
            (
                result.source.has_stream
                if result.source
                else False
            ),

        "has_thumbnail":
            (
                result.source.has_thumbnail
                if result.source
                else False
            ),

        "track_created":
            track is not None,

        "track_title":
            (
                track.title
                if track
                else None
            ),

        "track_source":
            (
                track.source
                if track
                else None
            ),

        "track_has_stream":
            (
                bool(track.stream_url)
                if track
                else False
            ),

        "requester":
            (
                track.requester_name
                if track
                else None
            ),

        "requester_id":
            (
                track.requester_id
                if track
                else None
            ),

        "voice_channel_id":
            (
                track.voice_channel_id
                if track
                else None
            ),

        "current_track":
            (
                session.current_track.title
                if session.current_track
                else None
            ),

        "queue_size":
            session.queue.size(),

        "ready_for_playback":
            (
                result.success
                and track is not None
                and bool(track.stream_url)
            ),
    }


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    try:

        result = asyncio.run(
            run_real_pipeline_test()
        )


        print(
            result
        )


    except Exception as error:

        print(
            "REAL PIPELINE TEST ERROR:"
        )

        print(
            type(error).__name__
        )

        print(
            str(error)
        )