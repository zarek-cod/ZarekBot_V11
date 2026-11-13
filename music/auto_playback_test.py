"""
CTX V11
Prueba integral del cambio automático de canción.

Este archivo comprueba:

Canción 1
    ↓
FINISHED
    ↓
PlaybackEventHandler
    ↓
AutoAdvance
    ↓
Canción 2 preparada
    ↓
AutoPlayback
    ↓
MockPlaybackBackend
    ↓
Canción 2 reproduciéndose

NO:
- conecta a Discord real
- utiliza token
- ejecuta FFmpeg
- reproduce audio real
"""

import asyncio

import discord

from music.backend_manager import (
    playback_backend_manager,
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


# ============================================================
# PRUEBA PRINCIPAL
# ============================================================

async def run_auto_playback_test() -> dict:
    """
    Ejecuta una simulación completa de dos canciones.
    """

    guild_id = 9001

    channel_id = 7777


    # ========================================================
    # 1. CLIENTE DISCORD LOCAL
    # ========================================================

    client = discord.Client(
        intents=discord.Intents.none()
    )


    # ========================================================
    # 2. INICIALIZAR RUNTIME
    # ========================================================

    initialize_music_runtime(
        client
    )


    # ========================================================
    # 3. CAMBIAR BACKEND REAL POR MOCK
    # ========================================================

    playback_backend_manager.clear()


    playback_backend_manager.set_factory(
        lambda current_guild_id: (
            MockPlaybackBackend(
                current_guild_id
            )
        )
    )


    # ========================================================
    # 4. OBTENER SESIÓN
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
    # 5. CREAR DOS CANCIONES
    # ========================================================

    track_1 = Track(
        title="Cancion 1",
        query="uno",
        requester_id=1,
        requester_name="Zarek",
        guild_id=guild_id,
        stream_url="https://example.com/one.mp3",
        source="direct",
    )


    track_2 = Track(
        title="Cancion 2",
        query="dos",
        requester_id=1,
        requester_name="Zarek",
        guild_id=guild_id,
        stream_url="https://example.com/two.mp3",
        source="direct",
    )


    # ========================================================
    # 6. AGREGAR A COLA
    # ========================================================

    session.add_track(
        track_1
    )


    session.add_track(
        track_2
    )


    # Canción 1 pasa a ser current_track.
    session.move_to_next()


    # ========================================================
    # 7. OBTENER MOCK BACKEND
    # ========================================================

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
        channel_id
    )


    # ========================================================
    # 8. REPRODUCIR CANCIÓN 1
    # ========================================================

    await backend.play(
        session.current_track
    )


    player.status = (
        PlayerStatus.PLAYING
    )


    first_track = (
        backend.current_track.title
        if backend.current_track
        else None
    )


    first_play_count = (
        backend.play_count
    )


    # ========================================================
    # 9. SIMULAR QUE CANCIÓN 1 TERMINÓ
    # ========================================================

    emit_track_finished(
        guild_id,
        session.current_track,
    )


    # ========================================================
    # 10. DAR TIEMPO A AUTOPLAYBACK
    # ========================================================
    #
    # AutoPlayback crea una asyncio.Task.
    # Cedemos el control al Event Loop para ejecutarla.
    #

    await asyncio.sleep(
        0
    )


    await asyncio.sleep(
        0
    )


    # ========================================================
    # 11. RESULTADO
    # ========================================================

    second_track = (
        backend.current_track.title
        if backend.current_track
        else None
    )


    result = {

        "first_track":
            first_track,

        "first_play_count":
            first_play_count,

        "second_track":
            second_track,

        "final_play_count":
            backend.play_count,

        "session_current_track":
            (
                session.current_track.title
                if session.current_track
                else None
            ),

        "queue_size":
            session.queue.size(),

        "player_status":
            player.status.value,

        "backend_state":
            backend.state.value,

        "automatic_change_worked":
            (
                second_track == "Cancion 2"
                and backend.play_count == 2
                and player.status
                == PlayerStatus.PLAYING
            ),
    }


    # ========================================================
    # 12. LIMPIAR
    # ========================================================

    reset_music_runtime()


    return result


# ============================================================
# EJECUTAR ARCHIVO DIRECTAMENTE
# ============================================================

if __name__ == "__main__":

    result = asyncio.run(
        run_auto_playback_test()
    )

    assert result["automatic_change_worked"], result

    print(
        result
    )
