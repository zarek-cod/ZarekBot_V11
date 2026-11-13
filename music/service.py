"""
CTX V11
Servicio principal del núcleo musical.

Este módulo conecta:

- ResolvedAudioSource
- TrackFactory
- MusicSession
- QueueManager

NO busca canciones en Internet.
NO reproduce audio.
NO contiene comandos de Discord.
NO contiene interfaz.
"""

from dataclasses import dataclass

from music.audio_source import ResolvedAudioSource
from music.session import (
    MusicSession,
    music_session_manager,
)
from music.track import Track
from music.track_factory import create_track_from_source


# ============================================================
# RESULTADO AL AGREGAR UNA CANCIÓN
# ============================================================

@dataclass(frozen=True)
class EnqueueResult:
    """
    Resultado de agregar una canción
    al sistema musical.
    """

    track: Track

    position: int

    started_immediately: bool


# ============================================================
# OBTENER SESIÓN
# ============================================================

def get_music_session(
    guild_id: int
) -> MusicSession:
    """
    Obtiene la sesión musical de un servidor.
    """

    return music_session_manager.get_session(
        guild_id
    )


# ============================================================
# AGREGAR FUENTE A LA COLA
# ============================================================

def enqueue_source(
    source: ResolvedAudioSource,
    query: str,
    requester_id: int,
    requester_name: str,
    guild_id: int,
    voice_channel_id: int | None = None,
) -> EnqueueResult:
    """
    Convierte una fuente resuelta en Track
    y la agrega a la sesión correspondiente.
    """

    # --------------------------------------------------------
    # CONVERTIR FUENTE -> TRACK
    # --------------------------------------------------------

    track = create_track_from_source(
        source=source,
        query=query,
        requester_id=requester_id,
        requester_name=requester_name,
        guild_id=guild_id,
        voice_channel_id=voice_channel_id,
    )


    # --------------------------------------------------------
    # OBTENER SESIÓN DEL SERVIDOR
    # --------------------------------------------------------

    session = get_music_session(
        guild_id
    )


    # --------------------------------------------------------
    # SI NO HAY CANCIÓN ACTUAL
    # --------------------------------------------------------

    if (
        session.current_track is None
        and not session.has_pending_tracks()
    ):
        """
        La primera canción se deja preparada
        inmediatamente como canción actual.

        Más adelante player.py será quien
        realmente empiece a reproducirla.
        """

        session.add_track(
            track
        )

        session.move_to_next()

        return EnqueueResult(
            track=track,
            position=0,
            started_immediately=True,
        )


    # --------------------------------------------------------
    # SI YA HAY UNA CANCIÓN
    # --------------------------------------------------------

    position = session.add_track(
        track
    )


    return EnqueueResult(
        track=track,
        position=position,
        started_immediately=False,
    )


# ============================================================
# CANCIÓN ACTUAL
# ============================================================

def get_current_track(
    guild_id: int
) -> Track | None:
    """
    Devuelve la canción actual del servidor.
    """

    session = get_music_session(
        guild_id
    )

    return session.current_track


# ============================================================
# SIGUIENTE CANCIÓN
# ============================================================

def move_to_next_track(
    guild_id: int
) -> Track | None:
    """
    Avanza lógicamente a la siguiente canción.

    Todavía NO reproduce audio.
    """

    session = get_music_session(
        guild_id
    )

    return session.move_to_next()


# ============================================================
# OBTENER COLA
# ============================================================

def get_pending_tracks(
    guild_id: int
) -> list[Track]:
    """
    Devuelve las canciones que están esperando.
    """

    session = get_music_session(
        guild_id
    )

    return session.queue.get_all()


# ============================================================
# CANTIDAD DE CANCIONES PENDIENTES
# ============================================================

def get_queue_size(
    guild_id: int
) -> int:

    session = get_music_session(
        guild_id
    )

    return session.queue.size()


# ============================================================
# QUITAR CANCIÓN
# ============================================================

def remove_track(
    guild_id: int,
    position: int
) -> Track | None:
    """
    Quita una canción pendiente según
    su posición visible en la cola.
    """

    session = get_music_session(
        guild_id
    )

    return session.queue.remove(
        position
    )


# ============================================================
# LIMPIAR COLA
# ============================================================

def clear_queue(
    guild_id: int
) -> None:
    """
    Borra solamente las canciones pendientes.

    No elimina la canción actual.
    """

    session = get_music_session(
        guild_id
    )

    session.queue.clear()


# ============================================================
# DETENER SESIÓN LÓGICA
# ============================================================

def reset_music_session(
    guild_id: int
) -> None:
    """
    Reinicia completamente la sesión musical.

    Todavía no desconecta Discord Voice.
    Eso será responsabilidad del reproductor.
    """

    session = get_music_session(
        guild_id
    )

    session.reset(
        clear_queue=True
    )


# ============================================================
# RESUMEN SEGURO
# ============================================================

def get_music_service_summary(
    guild_id: int
) -> dict:
    """
    Información para pruebas y logs.
    """

    session = get_music_session(
        guild_id
    )

    return session.to_safe_dict()