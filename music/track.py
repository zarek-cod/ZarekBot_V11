"""
CTX V11
Modelo de una canción dentro del sistema musical.

Este archivo NO reproduce audio.
Solamente representa una canción y conserva
información importante sobre quién la solicitó.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


# ============================================================
# TRACK / CANCIÓN
# ============================================================

@dataclass
class Track:
    """
    Representa una canción dentro de CTX Music.
    """

    # --------------------------------------------------------
    # INFORMACIÓN DE LA CANCIÓN
    # --------------------------------------------------------

    title: str

    query: str

    url: str | None = None

    stream_url: str | None = None

    duration: int | None = None

    thumbnail: str | None = None


    # --------------------------------------------------------
    # QUIÉN LA SOLICITÓ
    # --------------------------------------------------------

    requester_id: int = 0

    requester_name: str = "Desconocido"


    # --------------------------------------------------------
    # SERVIDOR
    # --------------------------------------------------------

    guild_id: int = 0

    voice_channel_id: int | None = None


    # --------------------------------------------------------
    # ORIGEN
    # --------------------------------------------------------

    source: str = "unknown"


    # --------------------------------------------------------
    # FECHA
    # --------------------------------------------------------

    requested_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


    # ========================================================
    # DURACIÓN FORMATEADA
    # ========================================================

    @property
    def formatted_duration(self) -> str:
        """
        Convierte segundos:

            245

        en:

            04:05
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
    # ¿QUIÉN ES EL DUEÑO DE ESTA CANCIÓN?
    # ========================================================

    def was_requested_by(
        self,
        user_id: int
    ) -> bool:
        """
        Comprueba si un usuario fue quien agregó
        esta canción.
        """

        return (
            self.requester_id
            == user_id
        )


    # ========================================================
    # INFORMACIÓN SEGURA
    # ========================================================

    def to_safe_dict(self) -> dict:
        """
        Información útil para logs y depuración.
        """

        return {

            "title":
                self.title,

            "duration":
                self.formatted_duration,

            "requester":
                self.requester_name,

            "requester_id":
                self.requester_id,

            "guild_id":
                self.guild_id,

            "source":
                self.source,

        }