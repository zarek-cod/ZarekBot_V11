"""
CTX V11
Backend de reproducción simulado.

Se utiliza únicamente durante desarrollo
para probar CTX Music sin:

- entrar a Discord Voice
- ejecutar FFmpeg
- reproducir audio real

Permite comprobar:

- connect
- play
- pause
- resume
- stop
- volume
- cambio automático de canción
"""

from music.playback_backend import (
    PlaybackBackend,
    PlaybackResult,
    PlaybackState,
)

from music.track import Track


# ============================================================
# BACKEND SIMULADO
# ============================================================

class MockPlaybackBackend(
    PlaybackBackend
):
    """
    Backend falso utilizado exclusivamente
    para pruebas internas.
    """

    backend_name = "ctx_mock_backend"


    def __init__(
        self,
        guild_id: int
    ) -> None:

        super().__init__(
            guild_id
        )

        self.connected_channel_id: (
            int | None
        ) = None

        self.play_count = 0

        self.pause_count = 0

        self.resume_count = 0

        self.stop_count = 0


    # ========================================================
    # CONECTAR
    # ========================================================

    async def connect(
        self,
        channel_id: int
    ) -> PlaybackResult:

        self.connected_channel_id = (
            channel_id
        )

        self.state = (
            PlaybackState.CONNECTED
        )


        return PlaybackResult(
            success=True,
            action="connect",
            message=(
                f"Mock conectado al canal "
                f"{channel_id}."
            ),
        )


    # ========================================================
    # DESCONECTAR
    # ========================================================

    async def disconnect(
        self
    ) -> PlaybackResult:

        self.connected_channel_id = None

        self.current_track = None

        self.state = (
            PlaybackState.DISCONNECTED
        )


        return PlaybackResult(
            success=True,
            action="disconnect",
            message=(
                "Mock desconectado."
            ),
        )


    # ========================================================
    # REPRODUCIR
    # ========================================================

    async def play(
        self,
        track: Track
    ) -> PlaybackResult:

        self.current_track = (
            track
        )

        self.play_count += 1

        self.state = (
            PlaybackState.PLAYING
        )


        return PlaybackResult(
            success=True,
            action="play",
            message=(
                f"Mock reproduciendo: "
                f"{track.title}"
            ),
        )


    # ========================================================
    # PAUSAR
    # ========================================================

    async def pause(
        self
    ) -> PlaybackResult:

        if (
            self.state
            != PlaybackState.PLAYING
        ):

            return PlaybackResult(
                success=False,
                action="pause",
                message=(
                    "Mock no está reproduciendo."
                ),
            )


        self.pause_count += 1

        self.state = (
            PlaybackState.PAUSED
        )


        return PlaybackResult(
            success=True,
            action="pause",
            message=(
                "Mock pausado."
            ),
        )


    # ========================================================
    # CONTINUAR
    # ========================================================

    async def resume(
        self
    ) -> PlaybackResult:

        if (
            self.state
            != PlaybackState.PAUSED
        ):

            return PlaybackResult(
                success=False,
                action="resume",
                message=(
                    "Mock no está pausado."
                ),
            )


        self.resume_count += 1

        self.state = (
            PlaybackState.PLAYING
        )


        return PlaybackResult(
            success=True,
            action="resume",
            message=(
                "Mock reanudado."
            ),
        )


    # ========================================================
    # STOP
    # ========================================================

    async def stop(
        self
    ) -> PlaybackResult:

        self.stop_count += 1

        self.current_track = None

        self.state = (
            PlaybackState.STOPPED
        )


        return PlaybackResult(
            success=True,
            action="stop",
            message=(
                "Mock detenido."
            ),
        )


    # ========================================================
    # VOLUMEN
    # ========================================================

    async def set_volume(
        self,
        volume: int
    ) -> PlaybackResult:

        final_volume = (
            self.normalize_volume(
                volume
            )
        )


        self.volume = (
            final_volume
        )


        return PlaybackResult(
            success=True,
            action="volume",
            message=(
                f"Mock volumen: "
                f"{final_volume}%."
            ),
        )


    # ========================================================
    # RESUMEN
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:

        data = (
            super().to_safe_dict()
        )


        data.update({

            "channel_id":
                self.connected_channel_id,

            "play_count":
                self.play_count,

            "pause_count":
                self.pause_count,

            "resume_count":
                self.resume_count,

            "stop_count":
                self.stop_count,
        })


        return data


# ============================================================
# RESUMEN DEL SISTEMA
# ============================================================

def get_mock_backend_summary() -> dict:

    return {

        "backend_name":
            MockPlaybackBackend.backend_name,

        "real_discord":
            False,

        "real_ffmpeg":
            False,

        "real_audio":
            False,

        "development_only":
            True,

        "supports_play":
            True,

        "supports_pause":
            True,

        "supports_resume":
            True,

        "supports_stop":
            True,

        "supports_volume":
            True,
    }