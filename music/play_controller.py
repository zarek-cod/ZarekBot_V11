"""
CTX V11
Controlador principal de PLAY.

Une:

- búsqueda musical
- ResolverRegistry
- YouTube / audio directo
- MusicPipeline
- MusicSession
- conexión de voz
- Backend de reproducción
- stream
- GuildMusicPlayer

Comportamiento:

SI NO HAY MÚSICA:
    búsqueda
       ↓
    conecta a voz
       ↓
    prepara Track
       ↓
    reproduce

SI YA HAY MÚSICA:
    búsqueda
       ↓
    agrega a la cola

NO:
- contiene comandos Discord
- contiene interfaz
- decide permisos
"""

import asyncio

from dataclasses import dataclass

from music.backend_manager import (
    playback_backend_manager,
)

from music.operation_lock import get_guild_operation_lock

from music.pipeline import (
    MusicPipelineResult,
    process_music_request,
)

from music.player import (
    PlayerStatus,
    music_player_manager,
)

from music.resolver_setup import (
    configure_music_resolvers,
)
from music.request_deduplicator import claim_music_request

from music.session import (
    music_session_manager,
)

from music.stream_refresher import (
    refresh_track_stream,
)

from music.track import Track

from music.state_events import (
    MusicStateEventType,
    emit_music_state_event,
)

from music.voice_controller import (
    connect_to_voice,
    disconnect_from_voice,
)


# ============================================================
# RESULTADO DE PLAY
# ============================================================

@dataclass(frozen=True)
class PlayRequestResult:
    """
    Resultado completo de una solicitud PLAY.
    """

    success: bool

    track: Track | None

    started: bool

    queued: bool

    position: int | None

    connected: bool

    stream_ready: bool

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_play_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_play_lock(
    guild_id: int
) -> asyncio.Lock:

    if guild_id not in _play_locks:

        _play_locks[guild_id] = get_guild_operation_lock(guild_id)

    return _play_locks[
        guild_id
    ]


# ============================================================
# CONTADORES
# ============================================================

_play_requests = 0

_tracks_started = 0

_tracks_queued = 0

_play_failures = 0

_auto_joins = 0

_stream_refresh_attempts = 0

_stream_refresh_successes = 0


# ============================================================
# PLAY PRINCIPAL
# ============================================================

async def play_music_request(
    guild_id: int,
    voice_channel_id: int,
    query: str,
    requester_id: int,
    requester_name: str,
    request_id: str | int | None = None,
) -> PlayRequestResult:
    """
    Procesa una solicitud PLAY completa.

    Ejemplo futuro:

        !ctx_play Blinding Lights

    o:

        /play Blinding Lights
    """

    global _play_requests
    global _tracks_started
    global _tracks_queued
    global _play_failures
    global _auto_joins

    global _stream_refresh_attempts
    global _stream_refresh_successes


    _play_requests += 1

    if not claim_music_request(request_id):
        return PlayRequestResult(
            success=False,
            track=None,
            started=False,
            queued=False,
            position=None,
            connected=False,
            stream_ready=False,
            message="Esta solicitud ya fue procesada.",
        )


    # ========================================================
    # VALIDACIONES BÁSICAS
    # ========================================================

    if guild_id <= 0:

        _play_failures += 1

        return PlayRequestResult(
            success=False,
            track=None,
            started=False,
            queued=False,
            position=None,
            connected=False,
            stream_ready=False,
            message="Servidor inválido.",
        )


    if voice_channel_id <= 0:

        _play_failures += 1

        return PlayRequestResult(
            success=False,
            track=None,
            started=False,
            queued=False,
            position=None,
            connected=False,
            stream_ready=False,
            message=(
                "Debes estar en un canal de voz."
            ),
        )


    if not query or not query.strip():

        _play_failures += 1

        return PlayRequestResult(
            success=False,
            track=None,
            started=False,
            queued=False,
            position=None,
            connected=False,
            stream_ready=False,
            message=(
                "Debes indicar una canción "
                "o un enlace."
            ),
        )


    lock = _get_play_lock(
        guild_id
    )

    # A manual request always supersedes an in-flight recommendation.
    from music.autoplay_recommendations import cancel_pending_autoplay

    cancel_pending_autoplay(guild_id)


    async with lock:

        # ====================================================
        # PROVEEDORES
        # ====================================================

        configure_music_resolvers()


        # ====================================================
        # SESIÓN
        # ====================================================

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


        # ====================================================
        # CONECTAR AUTOMÁTICAMENTE
        # ====================================================
        #
        # Solo hacemos auto-join si CTX todavía
        # no estaba conectado.
        #
        # Más adelante la capa de comandos comprobará
        # si el usuario está en el canal correcto.
        #

        joined_for_this_request = False


        backend_connected = False
        if playback_backend_manager.has_backend(guild_id):
            try:
                backend_connected = playback_backend_manager.get_backend(guild_id).is_connected
            except Exception:
                backend_connected = False

        if not session.state.connected or not backend_connected:

            connect_result = (
                await connect_to_voice(
                    guild_id=guild_id,
                    channel_id=voice_channel_id,
                )
            )


            if not connect_result.success:

                _play_failures += 1

                return PlayRequestResult(
                    success=False,
                    track=None,
                    started=False,
                    queued=False,
                    position=None,
                    connected=False,
                    stream_ready=False,
                    message=connect_result.message,
                )


            joined_for_this_request = True

            _auto_joins += 1


        # ====================================================
        # PIPELINE
        # ====================================================

        pipeline_result: MusicPipelineResult = (
            await process_music_request(

                query=query,

                requester_id=requester_id,

                requester_name=requester_name,

                guild_id=guild_id,

                voice_channel_id=voice_channel_id,
            )
        )


        # ====================================================
        # ERROR DE BÚSQUEDA
        # ====================================================

        if not pipeline_result.success:

            _play_failures += 1


            # Si CTX entró exclusivamente por esta
            # solicitud fallida, salimos de voz.
            if joined_for_this_request:

                try:

                    await disconnect_from_voice(
                        guild_id
                    )

                except Exception:

                    pass


            return PlayRequestResult(
                success=False,
                track=None,
                started=False,
                queued=False,
                position=None,
                connected=(
                    session.state.connected
                ),
                stream_ready=False,
                message=(
                    pipeline_result.message
                ),
            )


        track = (
            pipeline_result.track
        )

        def clear_unstarted_track() -> None:
            if session.current_track is track:
                session.queue.current = None
                emit_music_state_event(
                    guild_id,
                    MusicStateEventType.QUEUE_CHANGED,
                    notice="No se pudo iniciar la canción preparada.",
                )


        if track is None:

            _play_failures += 1

            return PlayRequestResult(
                success=False,
                track=None,
                started=False,
                queued=False,
                position=None,
                connected=(
                    session.state.connected
                ),
                stream_ready=False,
                message=(
                    "CTX no pudo crear "
                    "la canción solicitada."
                ),
            )


        # ====================================================
        # YA HABÍA UNA CANCIÓN
        # ====================================================
        #
        # Pipeline la agregó a la cola.
        #

        if not pipeline_result.started_immediately:

            _tracks_queued += 1


            return PlayRequestResult(
                success=True,
                track=track,
                started=False,
                queued=True,
                position=(
                    pipeline_result.position
                ),
                connected=(
                    session.state.connected
                ),
                stream_ready=bool(
                    track.stream_url
                ),
                message=(
                    f"{track.title} fue agregada "
                    f"a la cola en la posición "
                    f"{pipeline_result.position}."
                ),
            )


        # ====================================================
        # PRIMERA CANCIÓN
        # ====================================================
        #
        # El stream acaba de resolverse, así que normalmente
        # ya estará listo.
        #
        # Si por algún motivo no existe, intentamos
        # recuperarlo mediante StreamRefresher.
        #

        if not track.stream_url:

            _stream_refresh_attempts += 1


            refresh_result = (
                await refresh_track_stream(
                    track
                )
            )


            if not refresh_result.success:

                _play_failures += 1

                player.status = (
                    PlayerStatus.IDLE
                )

                clear_unstarted_track()


                return PlayRequestResult(
                    success=False,
                    track=track,
                    started=False,
                    queued=False,
                    position=0,
                    connected=(
                        session.state.connected
                    ),
                    stream_ready=False,
                    message=(
                        "CTX encontró la canción, "
                        "pero no pudo preparar "
                        "su stream de audio."
                    ),
                )


            _stream_refresh_successes += 1


        # ====================================================
        # COMPROBAR STREAM
        # ====================================================

        if not track.stream_url:

            _play_failures += 1


            player.status = (
                PlayerStatus.IDLE
            )

            clear_unstarted_track()


            return PlayRequestResult(
                success=False,
                track=track,
                started=False,
                queued=False,
                position=0,
                connected=(
                    session.state.connected
                ),
                stream_ready=False,
                message=(
                    "La canción no tiene "
                    "un stream reproducible."
                ),
            )


        # ====================================================
        # BACKEND
        # ====================================================

        try:

            backend = (
                playback_backend_manager.get_backend(
                    guild_id
                )
            )

        except Exception as error:

            _play_failures += 1

            clear_unstarted_track()


            return PlayRequestResult(
                success=False,
                track=track,
                started=False,
                queued=False,
                position=0,
                connected=(
                    session.state.connected
                ),
                stream_ready=True,
                message=(
                    "CTX no pudo obtener "
                    f"el reproductor: {error}"
                ),
            )


        # ====================================================
        # REPRODUCIR
        # ====================================================

        try:

            backend_result = (
                await backend.play(
                    track
                )
            )

        except Exception as error:

            _play_failures += 1

            player.status = (
                PlayerStatus.IDLE
            )

            clear_unstarted_track()


            return PlayRequestResult(
                success=False,
                track=track,
                started=False,
                queued=False,
                position=0,
                connected=(
                    session.state.connected
                ),
                stream_ready=True,
                message=(
                    "CTX preparó la canción, "
                    "pero no pudo reproducirla: "
                    f"{error}"
                ),
            )


        # ====================================================
        # BACKEND RECHAZÓ PLAY
        # ====================================================

        if not backend_result.success:

            _play_failures += 1

            player.status = (
                PlayerStatus.IDLE
            )

            clear_unstarted_track()


            return PlayRequestResult(
                success=False,
                track=track,
                started=False,
                queued=False,
                position=0,
                connected=(
                    session.state.connected
                ),
                stream_ready=True,
                message=(
                    backend_result.message
                ),
            )

        if session.current_track is not track:
            _play_failures += 1
            return PlayRequestResult(
                success=False,
                track=track,
                started=False,
                queued=False,
                position=0,
                connected=session.state.connected,
                stream_ready=True,
                message="El stream terminó antes de que Discord pudiera estabilizarlo.",
            )


        # ====================================================
        # SINCRONIZAR
        # ====================================================

        session.state.resume()


        player.status = (
            PlayerStatus.PLAYING
        )


        _tracks_started += 1

        emit_music_state_event(
            guild_id,
            MusicStateEventType.TRACK_STARTED,
            track=track,
        )


        # ====================================================
        # ÉXITO
        # ====================================================

        return PlayRequestResult(
            success=True,
            track=track,
            started=True,
            queued=False,
            position=0,
            connected=True,
            stream_ready=True,
            message=(
                f"Reproduciendo "
                f"{track.title}."
            ),
        )


# ============================================================
# RESUMEN
# ============================================================

def get_play_controller_summary() -> dict:

    return {

        "play_available":
            True,

        "play_requests":
            _play_requests,

        "tracks_started":
            _tracks_started,

        "tracks_queued":
            _tracks_queued,

        "play_failures":
            _play_failures,

        "auto_joins":
            _auto_joins,

        "stream_refresh_attempts":
            _stream_refresh_attempts,

        "stream_refresh_successes":
            _stream_refresh_successes,

        "guild_locks":
            len(_play_locks),

        "concurrent_play_protection":
            True,

        "auto_join_from_play":
            True,

        "queue_integration":
            True,

        "youtube_integration":
            True,

        "direct_audio_integration":
            True,
    }
