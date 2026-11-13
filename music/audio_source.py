"""
CTX V11
Modelo de fuente de audio.

Este módulo representa el resultado de una búsqueda musical
antes de convertirlo en una canción de la cola.

NO busca música.
NO descarga música.
NO reproduce audio.
"""

from dataclasses import dataclass
from enum import Enum


# ============================================================
# TIPOS DE FUENTE
# ============================================================

class AudioSourceType(str, Enum):
    """
    Fuentes que CTX podrá reconocer.
    """

    YOUTUBE = "youtube"

    SPOTIFY = "spotify"

    DIRECT = "direct"

    SEARCH = "search"

    UNKNOWN = "unknown"


# ============================================================
# FUENTE DE AUDIO RESUELTA
# ============================================================

@dataclass
class ResolvedAudioSource:
    """
    Información obtenida después de resolver
    una búsqueda o enlace musical.
    """

    # --------------------------------------------------------
    # IDENTIDAD
    # --------------------------------------------------------

    title: str

    source_type: AudioSourceType


    # --------------------------------------------------------
    # INFORMACIÓN OPCIONAL
    # --------------------------------------------------------

    artist: str | None = None

    webpage_url: str | None = None

    thumbnail: str | None = None

    duration: int | None = None


    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    stream_url: str | None = None


    # --------------------------------------------------------
    # IDENTIFICADOR DEL PROVEEDOR
    # --------------------------------------------------------

    source_id: str | None = None


    # ========================================================
    # DURACIÓN
    # ========================================================

    @property
    def formatted_duration(
        self
    ) -> str:
        """
        Convierte segundos a formato legible.

        Ejemplos:

        245 -> 04:05

        3700 -> 01:01:40
        """

        if self.duration is None:
            return "Desconocida"

        if self.duration < 0:
            return "Desconocida"


        hours, remainder = divmod(
            self.duration,
            3600
        )

        minutes, seconds = divmod(
            remainder,
            60
        )


        if hours > 0:

            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )


        return (
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )


    # ========================================================
    # COMPROBACIONES
    # ========================================================

    @property
    def has_stream(
        self
    ) -> bool:
        """
        Indica si ya existe una fuente
        preparada para reproducción.
        """

        return bool(
            self.stream_url
        )


    @property
    def has_thumbnail(
        self
    ) -> bool:

        return bool(
            self.thumbnail
        )


    # ========================================================
    # NOMBRE COMPLETO
    # ========================================================

    @property
    def display_title(
        self
    ) -> str:
        """
        Ejemplo:

        Blinding Lights — The Weeknd
        """

        if self.artist:

            return (
                f"{self.title} — "
                f"{self.artist}"
            )


        return self.title


    # ========================================================
    # VALIDACIÓN
    # ========================================================

    def is_valid(
        self
    ) -> bool:
        """
        Comprueba los datos mínimos necesarios.
        """

        if not self.title.strip():
            return False


        if (
            self.duration is not None
            and self.duration < 0
        ):
            return False


        return True


    # ========================================================
    # INFORMACIÓN SEGURA
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:
        """
        Información que sí podemos mostrar
        en consola o logs.

        No muestra directamente stream_url.
        """

        return {

            "title":
                self.title,

            "artist":
                self.artist,

            "display_title":
                self.display_title,

            "source":
                self.source_type.value,

            "duration":
                self.formatted_duration,

            "has_stream":
                self.has_stream,

            "has_thumbnail":
                self.has_thumbnail,

            "source_id":
                self.source_id,
        }