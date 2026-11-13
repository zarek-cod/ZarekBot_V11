"""
CTX V11
Conversor de fuentes de audio a canciones de CTX.

Este módulo toma un ResolvedAudioSource
y lo convierte en un Track listo para entrar
en la cola musical.

NO busca música.
NO reproduce audio.
NO contiene comandos.
"""

from music.audio_source import ResolvedAudioSource
from music.track import Track


# ============================================================
# CREAR TRACK DESDE UNA FUENTE RESUELTA
# ============================================================

def create_track_from_source(
    source: ResolvedAudioSource,
    query: str,
    requester_id: int,
    requester_name: str,
    guild_id: int,
    voice_channel_id: int | None = None,
) -> Track:
    """
    Convierte una fuente de audio resuelta
    en una canción compatible con CTX Music.
    """

    if not source.is_valid():
        raise ValueError(
            "La fuente de audio no es válida."
        )


    return Track(

        # ----------------------------------------------------
        # CANCIÓN
        # ----------------------------------------------------

        title=source.display_title,

        query=query,

        url=source.webpage_url,

        stream_url=source.stream_url,

        duration=source.duration,

        thumbnail=source.thumbnail,


        # ----------------------------------------------------
        # USUARIO
        # ----------------------------------------------------

        requester_id=requester_id,

        requester_name=requester_name,


        # ----------------------------------------------------
        # SERVIDOR
        # ----------------------------------------------------

        guild_id=guild_id,

        voice_channel_id=voice_channel_id,


        # ----------------------------------------------------
        # ORIGEN
        # ----------------------------------------------------

        source=source.source_type.value,
    )


# ============================================================
# VALIDAR ANTES DE ENCOLAR
# ============================================================

def can_create_track(
    source: ResolvedAudioSource
) -> bool:
    """
    Comprueba si una fuente tiene información
    suficiente para convertirse en Track.
    """

    return source.is_valid()


# ============================================================
# RESUMEN DE CONVERSIÓN
# ============================================================

def get_track_creation_summary(
    source: ResolvedAudioSource,
    requester_name: str,
) -> dict:
    """
    Información segura para logs o pruebas.
    """

    return {

        "title":
            source.display_title,

        "source":
            source.source_type.value,

        "duration":
            source.formatted_duration,

        "requester":
            requester_name,

        "ready":
            source.is_valid(),
    }