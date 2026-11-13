"""
CTX V11
Estado interno del sistema musical.

Este módulo NO reproduce audio.

Su función es recordar el estado musical
independiente de cada servidor:

- volumen
- pausa
- loop
- autoplay
- conexión
"""


from dataclasses import dataclass


# ============================================================
# LÍMITES
# ============================================================

MIN_VOLUME = 0
MAX_VOLUME = 100
DEFAULT_VOLUME = 70


# ============================================================
# ESTADO MUSICAL DE UN SERVIDOR
# ============================================================

@dataclass
class GuildMusicState:
    """
    Estado musical independiente
    para un servidor de Discord.
    """

    guild_id: int

    volume: int = DEFAULT_VOLUME

    paused: bool = False

    loop_enabled: bool = False

    autoplay_enabled: bool = False

    connected: bool = False


    # ========================================================
    # VOLUMEN
    # ========================================================

    def set_volume(
        self,
        volume: int
    ) -> int:
        """
        Establece el volumen entre 0 y 100.

        Si llega un valor fuera del rango,
        se ajusta automáticamente.
        """

        volume = max(
            MIN_VOLUME,
            min(
                MAX_VOLUME,
                volume
            )
        )

        self.volume = volume

        return self.volume


    # ========================================================
    # PAUSA
    # ========================================================

    def pause(
        self
    ) -> None:

        self.paused = True


    # ========================================================
    # CONTINUAR
    # ========================================================

    def resume(
        self
    ) -> None:

        self.paused = False


    # ========================================================
    # LOOP
    # ========================================================

    def enable_loop(
        self
    ) -> None:

        self.loop_enabled = True


    def disable_loop(
        self
    ) -> None:

        self.loop_enabled = False


    def toggle_loop(
        self
    ) -> bool:
        """
        Cambia entre:

        True  -> activado
        False -> desactivado
        """

        self.loop_enabled = (
            not self.loop_enabled
        )

        return self.loop_enabled


    # ========================================================
    # AUTOPLAY
    # ========================================================

    def enable_autoplay(
        self
    ) -> None:

        self.autoplay_enabled = True


    def disable_autoplay(
        self
    ) -> None:

        self.autoplay_enabled = False


    def toggle_autoplay(
        self
    ) -> bool:

        self.autoplay_enabled = (
            not self.autoplay_enabled
        )

        return self.autoplay_enabled


    # ========================================================
    # CONEXIÓN DE VOZ
    # ========================================================

    def mark_connected(
        self
    ) -> None:

        self.connected = True


    def mark_disconnected(
        self
    ) -> None:

        self.connected = False

        self.paused = False


    # ========================================================
    # REINICIAR
    # ========================================================

    def reset(
        self
    ) -> None:
        """
        Restablece el reproductor del servidor
        sin eliminar el objeto.
        """

        self.volume = DEFAULT_VOLUME

        self.paused = False

        self.loop_enabled = False

        self.autoplay_enabled = False

        self.connected = False


    # ========================================================
    # RESUMEN
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:

        return {

            "guild_id":
                self.guild_id,

            "volume":
                self.volume,

            "paused":
                self.paused,

            "loop":
                self.loop_enabled,

            "autoplay":
                self.autoplay_enabled,

            "connected":
                self.connected,
        }


# ============================================================
# ADMINISTRADOR GLOBAL DE ESTADOS
# ============================================================

class MusicStateManager:
    """
    Guarda un estado musical diferente
    para cada servidor donde esté CTX.
    """

    def __init__(
        self
    ) -> None:

        self._states: dict[
            int,
            GuildMusicState
        ] = {}


    # ========================================================
    # OBTENER ESTADO
    # ========================================================

    def get_state(
        self,
        guild_id: int
    ) -> GuildMusicState:

        if guild_id not in self._states:

            self._states[
                guild_id
            ] = GuildMusicState(
                guild_id=guild_id
            )


        return self._states[
            guild_id
        ]


    # ========================================================
    # ELIMINAR ESTADO
    # ========================================================

    def remove_state(
        self,
        guild_id: int
    ) -> bool:

        if guild_id not in self._states:
            return False


        del self._states[
            guild_id
        ]

        return True


    # ========================================================
    # CANTIDAD DE SERVIDORES
    # ========================================================

    def active_states(
        self
    ) -> int:

        return len(
            self._states
        )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

music_state_manager = MusicStateManager()