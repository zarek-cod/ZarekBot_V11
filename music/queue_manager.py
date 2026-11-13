"""
CTX V11
Gestor profesional de colas musicales.

Cada servidor de Discord tendrá su propia cola independiente.
Este archivo NO reproduce audio.
Solo administra canciones.
"""

from collections import deque

from music.track import Track


# ============================================================
# COLA DE UN SERVIDOR
# ============================================================

class MusicQueue:
    """
    Cola musical individual para un servidor.
    """

    def __init__(
        self,
        guild_id: int
    ) -> None:

        self.guild_id = guild_id

        self._queue: deque[Track] = deque()

        self.current: Track | None = None


    # ========================================================
    # AGREGAR CANCIÓN
    # ========================================================

    def add(
        self,
        track: Track
    ) -> int:
        """
        Agrega una canción al final de la cola.

        Devuelve la posición donde quedó.
        """

        self._queue.append(
            track
        )

        return len(
            self._queue
        )


    # ========================================================
    # SIGUIENTE CANCIÓN
    # ========================================================

    def next(
        self
    ) -> Track | None:
        """
        Saca la siguiente canción de la cola
        y la convierte en la canción actual.
        """

        if not self._queue:

            self.current = None

            return None


        self.current = self._queue.popleft()

        return self.current


    # ========================================================
    # VER SIGUIENTE SIN SACARLA
    # ========================================================

    def peek(
        self
    ) -> Track | None:

        if not self._queue:
            return None

        return self._queue[0]


    # ========================================================
    # QUITAR UNA CANCIÓN POR POSICIÓN
    # ========================================================

    def remove(
        self,
        position: int
    ) -> Track | None:
        """
        El usuario verá posiciones empezando desde 1.

        Ejemplo:

            1
            2
            3
        """

        index = position - 1

        if index < 0:
            return None

        if index >= len(
            self._queue
        ):
            return None


        track = self._queue[
            index
        ]


        del self._queue[
            index
        ]


        return track


    # ========================================================
    # BUSCAR CANCIONES DE UN USUARIO
    # ========================================================

    def get_tracks_by_user(
        self,
        user_id: int
    ) -> list[Track]:

        return [

            track

            for track in self._queue

            if track.requester_id
            == user_id

        ]


    # ========================================================
    # LIMPIAR
    # ========================================================

    def clear(
        self
    ) -> None:

        self._queue.clear()


    # ========================================================
    # ESTADO
    # ========================================================

    def is_empty(
        self
    ) -> bool:

        return (
            len(self._queue)
            == 0
        )


    def size(
        self
    ) -> int:

        return len(
            self._queue
        )


    # ========================================================
    # LISTA
    # ========================================================

    def get_all(
        self
    ) -> list[Track]:

        return list(
            self._queue
        )


    # ========================================================
    # RESUMEN
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:

        return {

            "guild_id":
                self.guild_id,

            "current":
                (
                    self.current.title
                    if self.current
                    else None
                ),

            "queue_size":
                self.size(),

            "queue": [

                {
                    "title":
                        track.title,

                    "requester":
                        track.requester_name,

                    "duration":
                        track.formatted_duration,
                }

                for track
                in self._queue
            ],
        }


# ============================================================
# MANAGER GLOBAL
# ============================================================

class QueueManager:
    """
    Administra las colas de todos los servidores.
    """

    def __init__(
        self
    ) -> None:

        self._guild_queues: dict[
            int,
            MusicQueue
        ] = {}


    # ========================================================
    # OBTENER COLA
    # ========================================================

    def get_queue(
        self,
        guild_id: int
    ) -> MusicQueue:
        """
        Si el servidor no tiene cola,
        se crea automáticamente.
        """

        if guild_id not in (
            self._guild_queues
        ):

            self._guild_queues[
                guild_id
            ] = MusicQueue(
                guild_id
            )


        return self._guild_queues[
            guild_id
        ]


    # ========================================================
    # ELIMINAR COLA
    # ========================================================

    def remove_queue(
        self,
        guild_id: int
    ) -> bool:

        if guild_id not in (
            self._guild_queues
        ):
            return False


        del self._guild_queues[
            guild_id
        ]

        return True


    # ========================================================
    # SERVIDORES ACTIVOS
    # ========================================================

    def active_guilds(
        self
    ) -> int:

        return len(
            self._guild_queues
        )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

queue_manager = QueueManager()