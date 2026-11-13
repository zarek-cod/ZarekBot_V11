"""
CTX V11
Motor central de CTX Music.

Este módulo coordina:

- MusicSession
- GuildMusicPlayer
- DiscordPlaybackBackend
- PlaybackBackendManager

NO:
- busca canciones
- contiene comandos
- contiene interfaz
- contiene IA
"""

from dataclasses import dataclass

from music.player import (
    GuildMusicPlayer,
    music_player_manager,
)
from music.playback_backend import (
    PlaybackBackend,
    PlaybackResult,
)
from music.runtime import (
    get_guild_backend,
    is_music_runtime_initialized,
)
from music.session import (
    MusicSession,
    music_session_manager,
)
from music.track import Track


# ============================================================
# RESULTADO DEL MOTOR
# ============================================================

@dataclass(frozen=True)
class MusicEngineResult:

    success: bool

    action: str

    message: str

    track: Track | None = None


# ============================================================
# MOTOR DE UN SERVIDOR
# ============================================================

class GuildMusicEngine:
    """
    Motor musical completo de un servidor.
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

        self.player: GuildMusicPlayer = (
            music_player_manager.get_player(
                guild_id
            )
        )


    # ========================================================
    # OBTENER BACKEND REAL
    # ========================================================

    def get_backend(
        self
    ) -> PlaybackBackend:
        """
        Obtiene el backend Discord + FFmpeg.

        El runtime debe estar inicializado.
        """

        if not is_music_runtime_initialized():

            raise RuntimeError(
                "CTX Music todavía no ha sido "
                "inicializado con Discord."
            )

        return get_guild_backend(
            self.guild_id
        )


    # ========================================================
    # CONECTAR A VOZ
    # ========================================================

    async def connect(
        self,
        channel_id: int
    ) -> MusicEngineResult:

        backend = self.get_backend()

        result: PlaybackResult = (
            await backend.connect(
                channel_id
            )
        )

        if result.success:

            self.session.mark_connected()

        return MusicEngineResult(
            success=result.success,
            action="connect",
            message=result.message,
            track=self.session.current_track,
        )


    # ========================================================
    # DESCONECTAR
    # ========================================================

    async def disconnect(
        self
    ) -> MusicEngineResult:

        backend = self.get_backend()

        result = await backend.disconnect()

        if result.success:

            self.session.mark_disconnected()

        return MusicEngineResult(
            success=result.success,
            action="disconnect",
            message=result.message,
            track=None,
        )


    # ========================================================
    # REPRODUCIR CANCIÓN ACTUAL
    # ========================================================

    async def play_current(
        self
    ) -> MusicEngineResult:

        backend = self.get_backend()

        logical_result = (
            self.player.start()
        )


        if not logical_result.success:

            return MusicEngineResult(
                success=False,
                action="play",
                message=logical_result.message,
                track=logical_result.track,
            )


        track = logical_result.track


        if track is None:

            return MusicEngineResult(
                success=False,
                action="play",
                message="No hay canción disponible.",
                track=None,
            )


        backend_result = (
            await backend.play(
                track
            )
        )


        return MusicEngineResult(
            success=backend_result.success,
            action="play",
            message=backend_result.message,
            track=track,
        )


    # ========================================================
    # PAUSAR
    # ========================================================

    async def pause(
        self
    ) -> MusicEngineResult:

        backend = self.get_backend()

        backend_result = (
            await backend.pause()
        )


        if backend_result.success:

            self.player.pause()


        return MusicEngineResult(
            success=backend_result.success,
            action="pause",
            message=backend_result.message,
            track=self.session.current_track,
        )


    # ========================================================
    # CONTINUAR
    # ========================================================

    async def resume(
        self
    ) -> MusicEngineResult:

        backend = self.get_backend()

        backend_result = (
            await backend.resume()
        )


        if backend_result.success:

            self.player.resume()


        return MusicEngineResult(
            success=backend_result.success,
            action="resume",
            message=backend_result.message,
            track=self.session.current_track,
        )


    # ========================================================
    # DETENER
    # ========================================================

    async def stop(
        self,
        clear_queue: bool = True
    ) -> MusicEngineResult:

        backend = self.get_backend()

        previous_track = (
            self.session.current_track
        )


        backend_result = (
            await backend.stop()
        )


        if backend_result.success:

            self.player.stop(
                clear_queue=clear_queue
            )


        return MusicEngineResult(
            success=backend_result.success,
            action="stop",
            message=backend_result.message,
            track=previous_track,
        )


    # ========================================================
    # VOLUMEN
    # ========================================================

    async def set_volume(
        self,
        volume: int
    ) -> MusicEngineResult:

        backend = self.get_backend()

        logical_result = (
            self.player.set_volume(
                volume
            )
        )


        final_volume = (
            self.session.state.volume
        )


        backend_result = (
            await backend.set_volume(
                final_volume
            )
        )


        return MusicEngineResult(
            success=backend_result.success,
            action="volume",
            message=backend_result.message,
            track=self.session.current_track,
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

            "current_track":
                (
                    self.session.current_track.title
                    if self.session.current_track
                    else None
                ),

            "queue_size":
                self.session.queue.size(),

            "player_status":
                self.player.status.value,

            "volume":
                self.session.state.volume,

            "connected":
                self.session.state.connected,

            "runtime_ready":
                is_music_runtime_initialized(),
        }


# ============================================================
# MANAGER GLOBAL
# ============================================================

class MusicEngineManager:

    def __init__(
        self
    ) -> None:

        self._engines: dict[
            int,
            GuildMusicEngine
        ] = {}


    def get_engine(
        self,
        guild_id: int
    ) -> GuildMusicEngine:

        if guild_id not in self._engines:

            self._engines[
                guild_id
            ] = GuildMusicEngine(
                guild_id
            )

        return self._engines[
            guild_id
        ]


    def has_engine(
        self,
        guild_id: int
    ) -> bool:

        return (
            guild_id
            in self._engines
        )


    def remove_engine(
        self,
        guild_id: int
    ) -> bool:

        if guild_id not in self._engines:
            return False

        del self._engines[
            guild_id
        ]

        return True


    def active_engines(
        self
    ) -> int:

        return len(
            self._engines
        )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

music_engine_manager = MusicEngineManager()


# ============================================================
# RESUMEN DEL SISTEMA
# ============================================================

def get_music_engine_summary() -> dict:

    return {

        "engine_available":
            True,

        "active_engines":
            music_engine_manager.active_engines(),

        "discord_runtime_ready":
            is_music_runtime_initialized(),

        "commands_connected":
            False,

        "search_provider_connected":
            False,

        "ui_connected":
            False,
    }