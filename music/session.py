"""
CTX V11
Sesiones musicales por servidor.

Este archivo une:

- Cola musical
- Estado del reproductor
- Canción actual

NO busca canciones.
NO reproduce audio.
NO contiene comandos de Discord.
"""

from music.queue_manager import MusicQueue, queue_manager
from music.state import GuildMusicState, music_state_manager
from music.track import Track


# ============================================================
# SESIÓN MUSICAL DE UN SERVIDOR
# ============================================================

class MusicSession:
    """
    Representa toda la sesión musical
    de un servidor de Discord.
    """

    def __init__(
        self,
        guild_id: int
    ) -> None:

        self.guild_id = guild_id

        # Cola propia del servidor
        self.queue: MusicQueue = (
            queue_manager.get_queue(
                guild_id
            )
        )

        # Estado propio del servidor
        self.state: GuildMusicState = (
            music_state_manager.get_state(
                guild_id
            )
        )


    # ========================================================
    # CANCIÓN ACTUAL
    # ========================================================

    @property
    def current_track(
        self
    ) -> Track | None:
        """
        Devuelve la canción actualmente seleccionada.
        """

        return self.queue.current


    # ========================================================
    # AGREGAR CANCIÓN
    # ========================================================

    def add_track(
        self,
        track: Track
    ) -> int:
        """
        Agrega una canción a la cola.

        Devuelve la posición donde quedó.
        """

        # Nos aseguramos de que la canción
        # pertenezca al servidor correcto.
        track.guild_id = self.guild_id

        return self.queue.add(
            track
        )


    # ========================================================
    # PREPARAR SIGUIENTE CANCIÓN
    # ========================================================

    def move_to_next(
        self
    ) -> Track | None:
        """
        Obtiene la siguiente canción de la cola.

        Todavía NO reproduce audio.
        """

        track = self.queue.next()

        if track is None:
            return None

        # Una canción nueva comienza
        # en estado no pausado.
        self.state.resume()

        return track


    # ========================================================
    # PAUSAR ESTADO
    # ========================================================

    def pause(
        self
    ) -> None:
        """
        Marca la sesión como pausada.

        Más adelante player.py será quien
        pause realmente Discord Voice.
        """

        self.state.pause()


    # ========================================================
    # CONTINUAR ESTADO
    # ========================================================

    def resume(
        self
    ) -> None:
        """
        Marca la sesión como activa.
        """

        self.state.resume()


    # ========================================================
    # VOLUMEN
    # ========================================================

    def set_volume(
        self,
        volume: int
    ) -> int:
        """
        Cambia el volumen lógico de la sesión.
        """

        return self.state.set_volume(
            volume
        )


    # ========================================================
    # LOOP
    # ========================================================

    def toggle_loop(
        self
    ) -> bool:

        return self.state.toggle_loop()


    # ========================================================
    # AUTOPLAY
    # ========================================================

    def toggle_autoplay(
        self
    ) -> bool:

        return self.state.toggle_autoplay()


    # ========================================================
    # CONEXIÓN
    # ========================================================

    def mark_connected(
        self
    ) -> None:

        self.state.mark_connected()


    def mark_disconnected(
        self
    ) -> None:

        self.state.mark_disconnected()


    # ========================================================
    # DETENER / REINICIAR SESIÓN
    # ========================================================

    def reset(
        self,
        clear_queue: bool = True
    ) -> None:
        """
        Reinicia la sesión.

        clear_queue=True:
            también borra las canciones pendientes.

        clear_queue=False:
            conserva la cola.
        """

        if clear_queue:
            self.queue.clear()

        self.queue.current = None

        self.state.reset()


    # ========================================================
    # ¿TIENE MÚSICA?
    # ========================================================

    def has_current_track(
        self
    ) -> bool:

        return (
            self.current_track
            is not None
        )


    def has_pending_tracks(
        self
    ) -> bool:

        return (
            not self.queue.is_empty()
        )


    # ========================================================
    # RESUMEN SEGURO
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:
        """
        Resumen útil para pruebas y logs.
        """

        return {

            "guild_id":
                self.guild_id,

            "current_track":
                (
                    self.current_track.title
                    if self.current_track
                    else None
                ),

            "queue_size":
                self.queue.size(),

            "volume":
                self.state.volume,

            "paused":
                self.state.paused,

            "loop":
                self.state.loop_enabled,

            "autoplay":
                self.state.autoplay_enabled,

            "connected":
                self.state.connected,
        }


# ============================================================
# ADMINISTRADOR GLOBAL DE SESIONES
# ============================================================

class MusicSessionManager:
    """
    Mantiene una sesión independiente
    para cada servidor donde funcione CTX.
    """

    def __init__(
        self
    ) -> None:

        self._sessions: dict[
            int,
            MusicSession
        ] = {}


    # ========================================================
    # OBTENER SESIÓN
    # ========================================================

    def get_session(
        self,
        guild_id: int
    ) -> MusicSession:
        """
        Obtiene la sesión del servidor.

        Si todavía no existe,
        la crea automáticamente.
        """

        if guild_id not in self._sessions:

            self._sessions[
                guild_id
            ] = MusicSession(
                guild_id=guild_id
            )

        return self._sessions[
            guild_id
        ]


    # ========================================================
    # COMPROBAR SI EXISTE
    # ========================================================

    def has_session(
        self,
        guild_id: int
    ) -> bool:

        return (
            guild_id
            in self._sessions
        )


    # ========================================================
    # ELIMINAR SESIÓN
    # ========================================================

    def remove_session(
        self,
        guild_id: int
    ) -> bool:

        if guild_id not in self._sessions:
            return False

        del self._sessions[
            guild_id
        ]

        queue_manager.remove_queue(
            guild_id
        )

        music_state_manager.remove_state(
            guild_id
        )

        return True


    # ========================================================
    # NÚMERO DE SESIONES
    # ========================================================

    def active_sessions(
        self
    ) -> int:

        return len(
            self._sessions
        )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

music_session_manager = MusicSessionManager()