"""
CTX V11
Sistema de actualización de streams temporales.

YouTube entrega URLs internas de audio que pueden
caducar después de cierto tiempo.

Por eso CTX conserva:

- URL pública
- ID
- título
- query original

y justo antes de reproducir puede volver a resolver
la canción y obtener un stream fresco.

NO:
- reproduce audio
- contiene comandos
- contiene interfaz
"""

from dataclasses import dataclass

from music.audio_source import (
    AudioSourceType,
    ResolvedAudioSource,
)

from music.providers.youtube_resolver import (
    youtube_resolver,
)

from music.search import (
    create_search_request,
)

from music.track import Track


# ============================================================
# RESULTADO
# ============================================================

@dataclass(frozen=True)
class StreamRefreshResult:
    """
    Resultado de actualizar un Track.
    """

    success: bool

    refreshed: bool

    track: Track

    old_stream_available: bool

    new_stream_available: bool

    message: str


# ============================================================
# ¿NECESITA REFRESH?
# ============================================================

def supports_stream_refresh(
    track: Track
) -> bool:
    """
    Por ahora refrescamos únicamente
    canciones provenientes de YouTube.
    """

    return (
        track.source
        == AudioSourceType.YOUTUBE.value
    )


# ============================================================
# OBTENER CONSULTA PARA REFRESH
# ============================================================

def _get_refresh_query(
    track: Track
) -> str:
    """
    Prioridad:

    1. URL pública de YouTube
    2. query original
    3. título
    """

    if track.url:

        return track.url


    if track.query.strip():

        return track.query


    return track.title


# ============================================================
# APLICAR FUENTE AL TRACK
# ============================================================

def _update_track_from_source(
    track: Track,
    source: ResolvedAudioSource,
) -> None:
    """
    Actualiza únicamente información
    obtenida del proveedor.

    NO cambia:
    - requester
    - guild
    - voice_channel
    - requested_at
    """

    # ========================================================
    # STREAM
    # ========================================================

    track.stream_url = (
        source.stream_url
    )


    # ========================================================
    # URL PÚBLICA
    # ========================================================

    if source.webpage_url:

        track.url = (
            source.webpage_url
        )


    # ========================================================
    # DURACIÓN
    # ========================================================

    if source.duration is not None:

        track.duration = (
            source.duration
        )


    # ========================================================
    # PORTADA
    # ========================================================

    if source.thumbnail:

        track.thumbnail = (
            source.thumbnail
        )


    # ========================================================
    # ORIGEN
    # ========================================================

    track.source = (
        source.source_type.value
    )


# ============================================================
# REFRESCAR STREAM
# ============================================================

async def refresh_track_stream(
    track: Track
) -> StreamRefreshResult:
    """
    Obtiene un stream nuevo para un Track.

    Si el proveedor no necesita actualización,
    conserva el stream actual.
    """

    old_stream_available = bool(
        track.stream_url
    )


    # ========================================================
    # PROVEEDOR SIN REFRESH
    # ========================================================

    if not supports_stream_refresh(
        track
    ):

        return StreamRefreshResult(

            success=True,

            refreshed=False,

            track=track,

            old_stream_available=(
                old_stream_available
            ),

            new_stream_available=bool(
                track.stream_url
            ),

            message=(
                "Esta fuente no necesita "
                "actualización de stream."
            ),
        )


    # ========================================================
    # PREPARAR CONSULTA
    # ========================================================

    query = _get_refresh_query(
        track
    )


    request = create_search_request(
        query
    )


    # ========================================================
    # RESOLVER YOUTUBE NUEVAMENTE
    # ========================================================

    try:

        source = (
            await youtube_resolver.resolve(
                request
            )
        )

    except Exception as error:

        return StreamRefreshResult(

            success=False,

            refreshed=False,

            track=track,

            old_stream_available=(
                old_stream_available
            ),

            new_stream_available=bool(
                track.stream_url
            ),

            message=(
                "No se pudo actualizar el "
                f"stream de YouTube: {error}"
            ),
        )


    # ========================================================
    # COMPROBAR NUEVO STREAM
    # ========================================================

    if not source.stream_url:

        return StreamRefreshResult(

            success=False,

            refreshed=False,

            track=track,

            old_stream_available=(
                old_stream_available
            ),

            new_stream_available=False,

            message=(
                "YouTube no devolvió un "
                "stream actualizado."
            ),
        )


    # ========================================================
    # ACTUALIZAR TRACK
    # ========================================================

    _update_track_from_source(
        track,
        source,
    )


    # ========================================================
    # ÉXITO
    # ========================================================

    return StreamRefreshResult(

        success=True,

        refreshed=True,

        track=track,

        old_stream_available=(
            old_stream_available
        ),

        new_stream_available=True,

        message=(
            "Stream de YouTube actualizado."
        ),
    )


# ============================================================
# RESUMEN
# ============================================================

def get_stream_refresher_summary() -> dict:

    return {

        "stream_refresh":
            True,

        "youtube_refresh":
            True,

        "direct_audio_refresh":
            False,

        "preserves_requester":
            True,

        "preserves_guild":
            True,

        "preserves_voice_channel":
            True,

        "refresh_before_playback":
            False,
    }