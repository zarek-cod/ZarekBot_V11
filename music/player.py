"""
CTX V11
Núcleo lógico del reproductor musical.

Este módulo administra el estado de reproducción.

POR AHORA:
- prepara canciones
- pausa
- continúa
- salta
- detiene
- controla volumen

TODAVÍA NO:
- reproduce audio real
- conecta a Discord Voice
- busca canciones
- contiene comandos
- contiene interfaz
"""

from dataclasses import dataclass
from enum import Enum

from music.session import (
    MusicSession,
    music_session_manager,
)
from music.track import Track


# ============================================================
# ESTADO DEL REPRODUCTOR
# ============================================================

class PlayerStatus(str, Enum):

    IDLE = "idle"

    PLAYING = "playing"

    PAUSED = "paused"

    STOPPED = "stopped"


# ============================================================
# RESULTADO DE UNA ACCIÓN
# ============================================================

@dataclass(frozen=True)
class PlayerActionResult:

    success: bool

    action: str

    message: str

    track: Track | None = None


# ============================================================
# REPRODUCTOR DE UN SERVIDOR
# ============================================================

class GuildMusicPlayer:
    """
    Reproductor lógico independiente
    para un servidor de Discord.
    """

    def __init__(
        self,
        guild_id: int
    ) -> None:

        self.guild_id = guild_id

        self.session: MusicSession = (
            music_session_manager.get_session(
                guild_id
            )
        )

        self.status = PlayerStatus.IDLE


    # ========================================================
    # CANCIÓN ACTUAL
    # ========================================================

    @property
    def current_track(
        self
    ) -> Track | None:

        return self.session.current_track


    # ========================================================
    # ¿ESTÁ REPRODUCIENDO?
    # ========================================================

    @property
    def is_playing(
        self
    ) -> bool:

        return (
            self.status
            == PlayerStatus.PLAYING
        )


    # ========================================================
    # ¿ESTÁ PAUSADO?
    # ========================================================

    @property
    def is_paused(
        self
    ) -> bool:

        return (
            self.status
            == PlayerStatus.PAUSED
        )


    # ========================================================
    # PREPARAR REPRODUCCIÓN
    # ========================================================

    def start(
        self
    ) -> PlayerActionResult:
        """
        Marca la canción actual como reproduciéndose.

        Todavía NO reproduce audio real.
        """

        track = self.current_track


        if track is None:

            track = self.session.move_to_next()


        if track is None:

            self.status = PlayerStatus.IDLE

            return PlayerActionResult(
                success=False,
                action="start",
                message="No hay canciones disponibles.",
                track=None,
            )


        self.session.resume()

        self.status = PlayerStatus.PLAYING


        return PlayerActionResult(
            success=True,
            action="start",
            message="Reproducción iniciada.",
            track=track,
        )


    # ========================================================
    # PAUSAR
    # ========================================================

    def pause(
        self
    ) -> PlayerActionResult:

        if not self.is_playing:

            return PlayerActionResult(
                success=False,
                action="pause",
                message="No hay música reproduciéndose.",
                track=self.current_track,
            )


        self.session.pause()

        self.status = PlayerStatus.PAUSED


        return PlayerActionResult(
            success=True,
            action="pause",
            message="Reproducción pausada.",
            track=self.current_track,
        )


    # ========================================================
    # CONTINUAR
    # ========================================================

    def resume(
        self
    ) -> PlayerActionResult:

        if not self.is_paused:

            return PlayerActionResult(
                success=False,
                action="resume",
                message="La música no está pausada.",
                track=self.current_track,
            )


        self.session.resume()

        self.status = PlayerStatus.PLAYING


        return PlayerActionResult(
            success=True,
            action="resume",
            message="Reproducción continuada.",
            track=self.current_track,
        )


    # ========================================================
    # SIGUIENTE CANCIÓN
    # ========================================================

    def skip(
        self
    ) -> PlayerActionResult:
        """
        Avanza a la siguiente canción.
        """

        next_track = self.session.move_to_next()


        if next_track is None:

            self.status = PlayerStatus.IDLE

            return PlayerActionResult(
                success=True,
                action="skip",
                message=(
                    "Se terminó la cola musical."
                ),
                track=None,
            )


        self.status = PlayerStatus.PLAYING


        return PlayerActionResult(
            success=True,
            action="skip",
            message="Canción saltada.",
            track=next_track,
        )


    # ========================================================
    # STOP
    # ========================================================

    def stop(
        self,
        clear_queue: bool = True
    ) -> PlayerActionResult:
        """
        Detiene el reproductor lógico.
        """

        previous_track = (
            self.current_track
        )


        self.session.reset(
            clear_queue=clear_queue
        )


        self.status = PlayerStatus.STOPPED


        return PlayerActionResult(
            success=True,
            action="stop",
            message="Reproductor detenido.",
            track=previous_track,
        )


    # ========================================================
    # VOLUMEN
    # ========================================================

    def set_volume(
        self,
        volume: int
    ) -> PlayerActionResult:

        final_volume = (
            self.session.set_volume(
                volume
            )
        )


        return PlayerActionResult(
            success=True,
            action="volume",
            message=(
                f"Volumen establecido "
                f"en {final_volume}%."
            ),
            track=self.current_track,
        )


    # ========================================================
    # LOOP
    # ========================================================

    def toggle_loop(
        self
    ) -> bool:

        return self.session.toggle_loop()


    # ========================================================
    # AUTOPLAY
    # ========================================================

    def toggle_autoplay(
        self
    ) -> bool:

        return self.session.toggle_autoplay()


    # ========================================================
    # RESUMEN
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:

        return {

            "guild_id":
                self.guild_id,

            "status":
                self.status.value,

            "current_track":
                (
                    self.current_track.title
                    if self.current_track
                    else None
                ),

            "queue_size":
                self.session.queue.size(),

            "volume":
                self.session.state.volume,

            "paused":
                self.session.state.paused,

            "loop":
                self.session.state.loop_enabled,

            "autoplay":
                self.session.state.autoplay_enabled,
        }


# ============================================================
# MANAGER DE REPRODUCTORES
# ============================================================

class MusicPlayerManager:
    """
    Mantiene un reproductor diferente
    para cada servidor.
    """

    def __init__(
        self
    ) -> None:

        self._players: dict[
            int,
            GuildMusicPlayer
        ] = {}


    # ========================================================
    # OBTENER PLAYER
    # ========================================================

    def get_player(
        self,
        guild_id: int
    ) -> GuildMusicPlayer:

        if guild_id not in self._players:

            self._players[
                guild_id
            ] = GuildMusicPlayer(
                guild_id
            )


        return self._players[
            guild_id
        ]


    # ========================================================
    # ELIMINAR PLAYER
    # ========================================================

    def remove_player(
        self,
        guild_id: int
    ) -> bool:

        if guild_id not in self._players:
            return False


        del self._players[
            guild_id
        ]

        return True


    # ========================================================
    # CANTIDAD
    # ========================================================

    def active_players(
        self
    ) -> int:

        return len(
            self._players
        )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

music_player_manager = MusicPlayerManager()