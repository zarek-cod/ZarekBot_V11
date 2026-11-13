"""
CTX V11
Pipeline central de solicitudes musicales.

Este módulo conecta:

- SearchRequest
- ResolverRegistry
- ResolvedAudioSource
- TrackFactory
- MusicService
- MusicSession

POR AHORA:
- procesa búsquedas
- resuelve fuentes
- crea Tracks
- agrega canciones

TODAVÍA NO:
- usa Internet real
- reproduce audio
- contiene comandos Discord
- contiene interfaz
"""

from dataclasses import dataclass

from music.audio_source import (
    ResolvedAudioSource,
)
from music.resolver import (
    resolver_registry,
)
from music.search import (
    SearchRequest,
    create_search_request,
    validate_search_request,
)
from music.service import (
    EnqueueResult,
    enqueue_source,
)
from music.track import Track


# ============================================================
# RESULTADO DEL PIPELINE
# ============================================================

@dataclass(frozen=True)
class MusicPipelineResult:
    """
    Resultado completo de una solicitud musical.
    """

    success: bool

    query: str

    request: SearchRequest | None

    source: ResolvedAudioSource | None

    track: Track | None

    position: int | None

    started_immediately: bool

    message: str


# ============================================================
# PROCESAR SOLICITUD
# ============================================================

async def process_music_request(
    query: str,
    requester_id: int,
    requester_name: str,
    guild_id: int,
    voice_channel_id: int | None = None,
) -> MusicPipelineResult:
    """
    Procesa una solicitud musical completa.

    Flujo:

        texto
          ↓
        SearchRequest
          ↓
        Resolver
          ↓
        ResolvedAudioSource
          ↓
        Track
          ↓
        Queue
    """

    # --------------------------------------------------------
    # CREAR BÚSQUEDA
    # --------------------------------------------------------

    request = create_search_request(
        query
    )


    # --------------------------------------------------------
    # VALIDAR
    # --------------------------------------------------------

    try:

        validate_search_request(
            request
        )

    except ValueError as error:

        return MusicPipelineResult(
            success=False,
            query=query,
            request=request,
            source=None,
            track=None,
            position=None,
            started_immediately=False,
            message=str(error),
        )


    # --------------------------------------------------------
    # RESOLVER FUENTE
    # --------------------------------------------------------

    try:

        source = await resolver_registry.resolve(
            request
        )

    except Exception as error:

        return MusicPipelineResult(
            success=False,
            query=query,
            request=request,
            source=None,
            track=None,
            position=None,
            started_immediately=False,
            message=str(error),
        )


    # --------------------------------------------------------
    # CREAR TRACK Y AGREGAR
    # --------------------------------------------------------

    try:

        enqueue_result: EnqueueResult = (
            enqueue_source(
                source=source,
                query=request.normalized_query,
                requester_id=requester_id,
                requester_name=requester_name,
                guild_id=guild_id,
                voice_channel_id=voice_channel_id,
            )
        )

    except Exception as error:

        return MusicPipelineResult(
            success=False,
            query=query,
            request=request,
            source=source,
            track=None,
            position=None,
            started_immediately=False,
            message=str(error),
        )


    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    track = enqueue_result.track


    if enqueue_result.started_immediately:

        message = (
            f"{track.title} está preparada "
            "como canción actual."
        )

    else:

        message = (
            f"{track.title} fue agregada "
            f"a la posición "
            f"{enqueue_result.position}."
        )


    return MusicPipelineResult(
        success=True,
        query=query,
        request=request,
        source=source,
        track=track,
        position=enqueue_result.position,
        started_immediately=(
            enqueue_result.started_immediately
        ),
        message=message,
    )


# ============================================================
# RESUMEN SEGURO
# ============================================================

def pipeline_result_to_safe_dict(
    result: MusicPipelineResult
) -> dict:
    """
    Convierte el resultado en información
    fácil de mostrar durante las pruebas.
    """

    return {

        "success":
            result.success,

        "query":
            result.query,

        "source":
            (
                result.source.source_type.value
                if result.source
                else None
            ),

        "track":
            (
                result.track.title
                if result.track
                else None
            ),

        "position":
            result.position,

        "started_immediately":
            result.started_immediately,

        "message":
            result.message,
    }


# ============================================================
# RESUMEN DEL SISTEMA
# ============================================================

def get_music_pipeline_summary() -> dict:

    return {

        "search":
            True,

        "resolver":
            True,

        "track_creation":
            True,

        "queue":
            True,

        "real_internet":
            False,

        "real_playback":
            False,

        "discord_commands":
            False,
    }