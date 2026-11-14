"""
CTX V11
Controlador de COLA MUSICAL.

Este módulo permite:

- consultar la canción actual
- consultar canciones pendientes
- conocer posiciones
- quitar una canción pendiente
- limpiar canciones pendientes

NO:
- contiene comandos Discord
- contiene interfaz
- decide permisos
- reproduce audio
- busca canciones
"""

import asyncio

from dataclasses import dataclass

from music.session import (
    music_session_manager,
)

from music.operation_lock import get_guild_operation_lock

from music.state_events import (
    MusicStateEventType,
    emit_music_state_event,
)

from music.track import Track


# ============================================================
# ELEMENTO DE COLA
# ============================================================

@dataclass(frozen=True)
class QueueItem:
    """
    Representa una canción pendiente
    junto con su posición visible.
    """

    position: int

    track: Track


# ============================================================
# SNAPSHOT DE LA COLA
# ============================================================

@dataclass(frozen=True)
class QueueSnapshot:
    """
    Estado completo y seguro de la cola
    en un momento determinado.
    """

    guild_id: int

    current_track: Track | None

    pending_tracks: tuple[QueueItem, ...]

    pending_count: int

    total_count: int


# ============================================================
# RESULTADO DE ELIMINACIÓN
# ============================================================

@dataclass(frozen=True)
class RemoveQueueTrackResult:

    success: bool

    removed_track: Track | None

    position: int

    message: str


# ============================================================
# RESULTADO DE LIMPIEZA
# ============================================================

@dataclass(frozen=True)
class ClearQueueResult:

    success: bool

    removed_count: int

    current_track_preserved: bool

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_queue_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_queue_lock(
    guild_id: int
) -> asyncio.Lock:
    """
    Devuelve un lock independiente
    para cada servidor.
    """

    if guild_id not in _queue_locks:

        _queue_locks[guild_id] = get_guild_operation_lock(guild_id)


    return _queue_locks[
        guild_id
    ]


# ============================================================
# OBTENER SNAPSHOT
# ============================================================

def get_queue_snapshot(
    guild_id: int
) -> QueueSnapshot:
    """
    Obtiene una copia del estado actual
    de la cola musical.
    """

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    pending_tracks = (
        session.queue.get_all()
    )


    items = tuple(

        QueueItem(
            position=index,
            track=track,
        )

        for index, track
        in enumerate(
            pending_tracks,
            start=1,
        )
    )


    pending_count = len(
        items
    )


    total_count = (
        pending_count
        + (
            1
            if session.current_track
            is not None
            else 0
        )
    )


    return QueueSnapshot(

        guild_id=guild_id,

        current_track=(
            session.current_track
        ),

        pending_tracks=items,

        pending_count=pending_count,

        total_count=total_count,
    )


# ============================================================
# QUITAR CANCIÓN PENDIENTE
# ============================================================

async def remove_queue_track(
    guild_id: int,
    position: int,
) -> RemoveQueueTrackResult:
    """
    Elimina una canción PENDIENTE
    según su posición visible.

    La canción actual NO se elimina aquí.
    Para ella utilizamos SKIP.
    """

    lock = _get_queue_lock(
        guild_id
    )


    async with lock:

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        # ====================================================
        # POSICIÓN INVÁLIDA
        # ====================================================

        if position <= 0:

            return RemoveQueueTrackResult(
                success=False,
                removed_track=None,
                position=position,
                message=(
                    "La posición debe ser "
                    "mayor que 0."
                ),
            )


        # ====================================================
        # ELIMINAR
        # ====================================================

        removed_track = (
            session.queue.remove(
                position
            )
        )


        if removed_track is None:

            return RemoveQueueTrackResult(
                success=False,
                removed_track=None,
                position=position,
                message=(
                    f"No existe una canción "
                    f"en la posición {position}."
                ),
            )


        # ====================================================
        # ÉXITO
        # ====================================================

        result = RemoveQueueTrackResult(
            success=True,
            removed_track=removed_track,
            position=position,
            message=(
                f"{removed_track.title} fue "
                f"eliminada de la posición "
                f"{position}."
            ),
        )

        emit_music_state_event(
            guild_id,
            MusicStateEventType.QUEUE_CHANGED,
            track=removed_track,
        )
        return result


# ============================================================
# LIMPIAR COLA PENDIENTE
# ============================================================

async def clear_pending_queue(
    guild_id: int
) -> ClearQueueResult:
    """
    Elimina solamente las canciones pendientes.

    La canción que está sonando se conserva.
    """

    lock = _get_queue_lock(
        guild_id
    )


    async with lock:

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        removed_count = (
            session.queue.size()
        )


        current_track_preserved = (
            session.current_track
            is not None
        )


        session.queue.clear()


        result = ClearQueueResult(
            success=True,
            removed_count=removed_count,
            current_track_preserved=(
                current_track_preserved
            ),
            message=(
                f"Se eliminaron "
                f"{removed_count} canciones "
                f"pendientes."
            ),
        )

        emit_music_state_event(
            guild_id,
            MusicStateEventType.QUEUE_CHANGED,
        )
        return result


# ============================================================
# OBTENER UNA POSICIÓN
# ============================================================

def get_track_at_position(
    guild_id: int,
    position: int,
) -> Track | None:
    """
    Obtiene una canción pendiente
    sin quitarla de la cola.
    """

    if position <= 0:
        return None


    snapshot = get_queue_snapshot(
        guild_id
    )


    for item in (
        snapshot.pending_tracks
    ):

        if item.position == position:

            return item.track


    return None


# ============================================================
# ¿LA COLA ESTÁ VACÍA?
# ============================================================

def is_queue_empty(
    guild_id: int
) -> bool:
    """
    Comprueba solamente canciones pendientes.
    """

    snapshot = get_queue_snapshot(
        guild_id
    )


    return (
        snapshot.pending_count
        == 0
    )


# ============================================================
# RESUMEN SEGURO
# ============================================================

def queue_snapshot_to_safe_dict(
    snapshot: QueueSnapshot
) -> dict:
    """
    Convierte el snapshot en información
    fácil de mostrar y depurar.
    """

    return {

        "guild_id":
            snapshot.guild_id,

        "current_track":
            (
                snapshot.current_track.title
                if snapshot.current_track
                else None
            ),

        "pending_count":
            snapshot.pending_count,

        "total_count":
            snapshot.total_count,

        "pending_tracks": [

            {
                "position":
                    item.position,

                "title":
                    item.track.title,

                "requester":
                    item.track.requester_name,

                "duration":
                    item.track.formatted_duration,
            }

            for item
            in snapshot.pending_tracks
        ],
    }


# ============================================================
# RESUMEN DEL CONTROLADOR
# ============================================================

def get_queue_controller_summary() -> dict:

    return {

        "queue_available":
            True,

        "current_track":
            True,

        "pending_tracks":
            True,

        "remove_track":
            True,

        "clear_pending":
            True,

        "position_lookup":
            True,

        "guild_locks":
            len(_queue_locks),

        "concurrent_queue_protection":
            True,
    }
