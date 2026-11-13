"""
CTX V11
Interfaz base del motor de reproducción.

Este módulo define CÓMO debe comportarse cualquier
motor capaz de reproducir audio para CTX.

TODAVÍA NO:
- conecta a Discord Voice
- reproduce audio real
- busca canciones
- contiene comandos
- contiene interfaz gráfica

Más adelante tendremos una implementación real
que utilizará discord.py + FFmpeg.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from music.track import Track


# ============================================================
# ESTADO DEL BACKEND
# ============================================================

class PlaybackState(str, Enum):

    DISCONNECTED = "disconnected"

    CONNECTED = "connected"

    PLAYING = "playing"

    PAUSED = "paused"

    STOPPED = "stopped"

    ERROR = "error"


# ============================================================
# RESULTADO DE OPERACIÓN
# ============================================================

@dataclass(frozen=True)
class PlaybackResult:
    """
    Resultado estándar producido por un backend.
    """

    success: bool

    action: str

    message: str


# ============================================================
# BACKEND BASE
# ============================================================

class PlaybackBackend(ABC):
    """
    Contrato que deberá cumplir cualquier motor
    real de reproducción de CTX Music.
    """

    backend_name: str = "unknown"


    def __init__(
        self,
        guild_id: int
    ) -> None:

        self.guild_id = guild_id

        self.state = PlaybackState.DISCONNECTED

        self.current_track: Track | None = None

        self.volume: int = 70


    # ========================================================
    # CONECTAR
    # ========================================================

    @abstractmethod
    async def connect(
        self,
        channel_id: int
    ) -> PlaybackResult:
        """
        Conecta el backend al canal de voz.
        """

        raise NotImplementedError


    # ========================================================
    # DESCONECTAR
    # ========================================================

    @abstractmethod
    async def disconnect(
        self
    ) -> PlaybackResult:
        """
        Desconecta el backend.
        """

        raise NotImplementedError


    # ========================================================
    # REPRODUCIR
    # ========================================================

    @abstractmethod
    async def play(
        self,
        track: Track
    ) -> PlaybackResult:
        """
        Reproduce una canción.
        """

        raise NotImplementedError


    # ========================================================
    # PAUSAR
    # ========================================================

    @abstractmethod
    async def pause(
        self
    ) -> PlaybackResult:
        """
        Pausa la reproducción.
        """

        raise NotImplementedError


    # ========================================================
    # CONTINUAR
    # ========================================================

    @abstractmethod
    async def resume(
        self
    ) -> PlaybackResult:
        """
        Continúa una reproducción pausada.
        """

        raise NotImplementedError


    # ========================================================
    # DETENER
    # ========================================================

    @abstractmethod
    async def stop(
        self
    ) -> PlaybackResult:
        """
        Detiene la reproducción actual.
        """

        raise NotImplementedError


    # ========================================================
    # VOLUMEN
    # ========================================================

    @abstractmethod
    async def set_volume(
        self,
        volume: int
    ) -> PlaybackResult:
        """
        Cambia el volumen del backend.
        """

        raise NotImplementedError


    # ========================================================
    # COMPROBACIONES
    # ========================================================

    @property
    def is_connected(
        self
    ) -> bool:

        return self.state != PlaybackState.DISCONNECTED


    @property
    def is_playing(
        self
    ) -> bool:

        return self.state == PlaybackState.PLAYING


    @property
    def is_paused(
        self
    ) -> bool:

        return self.state == PlaybackState.PAUSED


    # ========================================================
    # VOLUMEN SEGURO
    # ========================================================

    @staticmethod
    def normalize_volume(
        volume: int
    ) -> int:
        """
        Garantiza un volumen entre 0 y 100.
        """

        return max(
            0,
            min(
                100,
                volume
            )
        )


    # ========================================================
    # RESUMEN
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:

        return {

            "backend":
                self.backend_name,

            "guild_id":
                self.guild_id,

            "state":
                self.state.value,

            "connected":
                self.is_connected,

            "playing":
                self.is_playing,

            "paused":
                self.is_paused,

            "volume":
                self.volume,

            "current_track":
                (
                    self.current_track.title
                    if self.current_track
                    else None
                ),
        }


# ============================================================
# INFORMACIÓN DEL SISTEMA
# ============================================================

def get_playback_backend_summary() -> dict:
    """
    Información de la arquitectura actual.

    Todavía no existe un backend real conectado.
    """

    return {

        "backend_interface":
            True,

        "discord_voice_backend":
            False,

        "ffmpeg_backend":
            False,

        "real_audio":
            False,

        "ready_for_implementation":
            True,
    }