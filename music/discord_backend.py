"""
CTX V11
Backend real de reproducción para Discord Voice.

Conecta CTX Music con:

- discord.py
- Discord Voice
- FFmpeg
- pausa
- reanudación
- stop
- volumen
- eventos de reproducción

Incluye diagnóstico detallado para detectar
problemas reales de audio en Discord.
"""

from __future__ import annotations

import asyncio

import discord

from music.ffmpeg import require_ffmpeg

from music.playback_backend import (
    PlaybackBackend,
    PlaybackResult,
    PlaybackState,
)

from music.playback_events import (
    emit_playback_error,
    emit_track_finished,
    emit_track_stopped,
)

from music.track import Track


# ============================================================
# BACKEND DISCORD + FFMPEG
# ============================================================

class DiscordPlaybackBackend(
    PlaybackBackend
):
    """
    Backend real de CTX Music para Discord.
    """

    backend_name = "discord_ffmpeg"


    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        guild_id: int,
        client: discord.Client,
    ) -> None:

        super().__init__(
            guild_id
        )


        self.client = client


        self.voice_client: (
            discord.VoiceClient | None
        ) = None


        self.audio_source: (
            discord.PCMVolumeTransformer | None
        ) = None


        # Cada reproducción obtiene
        # una generación diferente.
        self._playback_generation = 0


        # Generaciones detenidas manualmente.
        self._manual_stop_generations: set[int] = set()


    # ========================================================
    # SERVIDOR
    # ========================================================

    def _get_guild(
        self
    ) -> discord.Guild | None:

        return self.client.get_guild(
            self.guild_id
        )


    # ========================================================
    # VOICE CLIENT EXISTENTE
    # ========================================================

    def _get_existing_voice_client(
        self
    ) -> discord.VoiceClient | None:
        """
        Busca una conexión de voz existente.

        Esto es importante porque el sistema
        antiguo de CTX también puede conectar
        al bot mediante !ctx_voz.
        """

        guild = self._get_guild()


        if guild is None:

            return None


        voice_client = guild.voice_client


        if (
            voice_client is not None
            and voice_client.is_connected()
        ):

            return voice_client


        return None


    # ========================================================
    # ¿VOICE ESTÁ CONECTADO?
    # ========================================================

    def _voice_is_connected(
        self
    ) -> bool:

        return (
            self.voice_client is not None
            and self.voice_client.is_connected()
        )


    # ========================================================
    # CONECTAR
    # ========================================================

    async def connect(
        self,
        channel_id: int,
    ) -> PlaybackResult:

        guild = self._get_guild()


        if guild is None:

            return PlaybackResult(
                success=False,
                action="connect",
                message=(
                    "No se encontró el servidor."
                ),
            )


        channel = guild.get_channel(
            channel_id
        )


        if channel is None:

            return PlaybackResult(
                success=False,
                action="connect",
                message=(
                    "No se encontró el canal de voz."
                ),
            )


        if not isinstance(
            channel,
            (
                discord.VoiceChannel,
                discord.StageChannel,
            ),
        ):

            return PlaybackResult(
                success=False,
                action="connect",
                message=(
                    "El canal indicado no es de voz."
                ),
            )


        # ====================================================
        # REUTILIZAR CONEXIÓN EXISTENTE
        # ====================================================

        existing_voice = (
            self._get_existing_voice_client()
        )


        if existing_voice is not None:

            self.voice_client = (
                existing_voice
            )


        # ====================================================
        # YA ESTÁ CONECTADO
        # ====================================================

        if self._voice_is_connected():

            if (
                self.voice_client.channel
                and self.voice_client.channel.id
                == channel.id
            ):

                self.state = (
                    PlaybackState.CONNECTED
                )


                print(
                    "🎧 [CTX MUSIC] "
                    "Usando conexión de voz existente:",
                    channel.name,
                )


                return PlaybackResult(
                    success=True,
                    action="connect",
                    message=(
                        "CTX ya está conectado "
                        "a ese canal."
                    ),
                )


            # =================================================
            # MOVER AL NUEVO CANAL
            # =================================================

            await self.voice_client.move_to(
                channel
            )


            self.state = (
                PlaybackState.CONNECTED
            )


            print(
                "🎧 [CTX MUSIC] Movido a:",
                channel.name,
            )


            return PlaybackResult(
                success=True,
                action="connect",
                message=(
                    "CTX se movió al nuevo "
                    "canal de voz."
                ),
            )


        # ====================================================
        # CONEXIÓN NUEVA
        # ====================================================

        print(
            "🎧 [CTX MUSIC] Conectando a:",
            channel.name,
        )


        self.voice_client = (
            await channel.connect()
        )


        self.state = (
            PlaybackState.CONNECTED
        )


        print(
            "✅ [CTX MUSIC] Voice conectado:",
            self._voice_is_connected(),
        )


        return PlaybackResult(
            success=True,
            action="connect",
            message=(
                "CTX se conectó al canal de voz."
            ),
        )


    # ========================================================
    # MARCAR STOP MANUAL
    # ========================================================

    def _mark_manual_stop(
        self
    ) -> None:

        if self._playback_generation <= 0:

            return


        self._manual_stop_generations.add(
            self._playback_generation
        )


    # ========================================================
    # DESCONECTAR
    # ========================================================

    async def disconnect(
        self
    ) -> PlaybackResult:

        if not self._voice_is_connected():

            self.voice_client = None

            self.current_track = None

            self.audio_source = None


            self.state = (
                PlaybackState.DISCONNECTED
            )


            return PlaybackResult(
                success=True,
                action="disconnect",
                message=(
                    "CTX ya estaba desconectado."
                ),
            )


        # ====================================================
        # DETENER AUDIO ANTES DE SALIR
        # ====================================================

        if (
            self.voice_client.is_playing()
            or self.voice_client.is_paused()
        ):

            self._mark_manual_stop()

            self.voice_client.stop()


        await self.voice_client.disconnect(
            force=True
        )


        self.voice_client = None

        self.current_track = None

        self.audio_source = None


        self.state = (
            PlaybackState.DISCONNECTED
        )


        print(
            "🔌 [CTX MUSIC] "
            "Desconectado del canal de voz."
        )


        return PlaybackResult(
            success=True,
            action="disconnect",
            message=(
                "CTX salió del canal de voz."
            ),
        )


    # ========================================================
    # REPRODUCIR
    # ========================================================

    async def play(
        self,
        track: Track,
    ) -> PlaybackResult:

        # ====================================================
        # COMPROBAR VOZ
        # ====================================================

        if not self._voice_is_connected():

            # Intentamos recuperar una conexión
            # creada por otra parte del bot.

            existing_voice = (
                self._get_existing_voice_client()
            )


            if existing_voice is not None:

                self.voice_client = (
                    existing_voice
                )


        if not self._voice_is_connected():

            return PlaybackResult(
                success=False,
                action="play",
                message=(
                    "CTX no está conectado "
                    "a un canal de voz."
                ),
            )


        # ====================================================
        # COMPROBAR STREAM
        # ====================================================

        if not track.stream_url:

            return PlaybackResult(
                success=False,
                action="play",
                message=(
                    "La canción no tiene una "
                    "fuente de audio reproducible."
                ),
            )


        # ====================================================
        # NO REEMPLAZAR AUDIO DIRECTAMENTE
        # ====================================================

        if (
            self.voice_client.is_playing()
            or self.voice_client.is_paused()
        ):

            return PlaybackResult(
                success=False,
                action="play",
                message=(
                    "Ya existe una canción activa. "
                    "Debe detenerse o saltarse primero."
                ),
            )


        # ====================================================
        # FFMPEG
        # ====================================================

        ffmpeg_executable = (
            require_ffmpeg()
        )


        print()
        print(
            "=============================================="
        )

        print(
            "🎵 [CTX MUSIC] PREPARANDO AUDIO"
        )

        print(
            "Guild:",
            self.guild_id,
        )

        print(
            "Track:",
            track.title,
        )

        print(
            "Voice connected:",
            self._voice_is_connected(),
        )

        print(
            "Voice channel:",
            (
                self.voice_client.channel.name
                if (
                    self.voice_client
                    and self.voice_client.channel
                )
                else "None"
            ),
        )

        print(
            "FFmpeg:",
            ffmpeg_executable,
        )

        print(
            "Stream disponible:",
            bool(
                track.stream_url
            ),
        )

        print(
            "Volumen:",
            self.volume,
        )

        print(
            "=============================================="
        )

        print()


        # ====================================================
        # FUENTE FFMPEG
        # ====================================================

        try:

            ffmpeg_audio = (
                discord.FFmpegPCMAudio(

                    source=track.stream_url,

                    executable=ffmpeg_executable,

                    before_options=(
                        "-reconnect 1 "
                        "-reconnect_streamed 1 "
                        "-reconnect_delay_max 5"
                    ),

                    options=(
                        "-vn "
                        "-loglevel warning"
                    ),
                )
            )


        except Exception as error:

            print()
            print(
                "❌ [CTX MUSIC] "
                "NO SE PUDO CREAR FFMPEG"
            )

            print(
                "Tipo:",
                type(error).__name__,
            )

            print(
                "Error:",
                repr(error),
            )

            print()


            return PlaybackResult(
                success=False,
                action="play",
                message=(
                    "CTX no pudo iniciar FFmpeg."
                ),
            )


        # ====================================================
        # VOLUMEN
        # ====================================================

        try:

            self.audio_source = (
                discord.PCMVolumeTransformer(

                    ffmpeg_audio,

                    volume=(
                        self.volume / 100
                    ),
                )
            )


        except Exception as error:

            print(
                "❌ [CTX MUSIC] "
                "Error creando PCMVolumeTransformer:"
            )

            print(
                type(error).__name__,
                repr(error),
            )


            try:

                ffmpeg_audio.cleanup()

            except Exception:

                pass


            return PlaybackResult(
                success=False,
                action="play",
                message=(
                    "CTX no pudo preparar "
                    "la fuente de audio."
                ),
            )


        # ====================================================
        # NUEVA GENERACIÓN
        # ====================================================

        self._playback_generation += 1


        generation = (
            self._playback_generation
        )


        # Guardamos la canción exacta
        # de esta reproducción.

        played_track = track


        self.current_track = track


        # ====================================================
        # CALLBACK
        # ====================================================

        def after_callback(
            error: Exception | None
        ) -> None:

            self._after_playback(
                error=error,
                generation=generation,
                track=played_track,
            )


        # ====================================================
        # REPRODUCCIÓN REAL
        # ====================================================

        print(
            "▶️ [CTX MUSIC] "
            "Enviando audio a Discord..."
        )


        try:

            self.voice_client.play(
                self.audio_source,
                after=after_callback,
            )


        except Exception as error:

            print()
            print(
                "❌ [CTX MUSIC] "
                "voice_client.play FALLÓ"
            )

            print(
                "Tipo:",
                type(error).__name__,
            )

            print(
                "Error:",
                repr(error),
            )

            print()


            self.current_track = None


            if self.audio_source is not None:

                try:

                    self.audio_source.cleanup()

                except Exception:

                    pass


            self.audio_source = None


            self.state = (
                PlaybackState.ERROR
            )


            return PlaybackResult(
                success=False,
                action="play",
                message=(
                    "Discord no pudo iniciar "
                    "la reproducción."
                ),
            )


        # ====================================================
        # COMPROBAR ESTADO INMEDIATO
        # ====================================================

        print(
            "Discord is_playing:",
            self.voice_client.is_playing(),
        )

        print(
            "Discord is_paused:",
            self.voice_client.is_paused(),
        )


        # Pequeña espera para comprobar que
        # el hilo de audio no muere inmediatamente.

        await asyncio.sleep(
            0.35
        )


        print(
            "Discord is_playing después de 350ms:",
            self.voice_client.is_playing(),
        )

        print(
            "Discord is_paused después de 350ms:",
            self.voice_client.is_paused(),
        )

        print()


        # ====================================================
        # ESTADO
        # ====================================================

        if self.voice_client.is_playing():

            self.state = (
                PlaybackState.PLAYING
            )


        else:

            print(
                "⚠️ [CTX MUSIC] "
                "Discord dejó de reproducir "
                "demasiado rápido."
            )


        return PlaybackResult(
            success=True,
            action="play",
            message=(
                f"Reproduciendo: "
                f"{track.title}"
            ),
        )


    # ========================================================
    # CALLBACK DE FINALIZACIÓN
    # ========================================================

    def _after_playback(
        self,
        error: Exception | None,
        generation: int,
        track: Track | None,
    ) -> None:

        # ====================================================
        # ¿FUE STOP MANUAL?
        # ====================================================

        manual_stop = (
            generation
            in self._manual_stop_generations
        )


        self._manual_stop_generations.discard(
            generation
        )


        # ====================================================
        # ERROR REAL
        # ====================================================

        if error is not None:

            print()
            print(
                "=============================================="
            )

            print(
                "❌ [CTX MUSIC] "
                "ERROR REAL DE REPRODUCCIÓN"
            )

            print(
                "Guild:",
                self.guild_id,
            )

            print(
                "Track:",
                (
                    track.title
                    if track is not None
                    else "None"
                ),
            )

            print(
                "Error type:",
                type(error).__name__,
            )

            print(
                "Error:",
                repr(error),
            )

            print(
                "Voice connected:",
                self._voice_is_connected(),
            )

            print(
                "Generation:",
                generation,
            )

            print(
                "Current generation:",
                self._playback_generation,
            )

            print(
                "=============================================="
            )

            print()


            emit_playback_error(
                guild_id=self.guild_id,
                track=track,
                error=error,
            )


            if (
                generation
                == self._playback_generation
            ):

                self.current_track = None

                self.audio_source = None


                if self._voice_is_connected():

                    self.state = (
                        PlaybackState.ERROR
                    )

                else:

                    self.state = (
                        PlaybackState.DISCONNECTED
                    )


            return


        # ====================================================
        # STOP MANUAL
        # ====================================================

        if manual_stop:

            print(
                "⏹️ [CTX MUSIC] "
                "Reproducción detenida manualmente:",
                (
                    track.title
                    if track
                    else "Desconocida"
                ),
            )


            emit_track_stopped(
                guild_id=self.guild_id,
                track=track,
            )


            if (
                generation
                == self._playback_generation
            ):

                self.current_track = None

                self.audio_source = None


                if self._voice_is_connected():

                    self.state = (
                        PlaybackState.STOPPED
                    )

                else:

                    self.state = (
                        PlaybackState.DISCONNECTED
                    )


            return


        # ====================================================
        # FINALIZACIÓN NATURAL
        # ====================================================

        print()
        print(
            "✅ [CTX MUSIC] "
            "Canción finalizada:"
        )

        print(
            (
                track.title
                if track
                else "Desconocida"
            )
        )

        print()


        emit_track_finished(
            guild_id=self.guild_id,
            track=track,
        )


        if (
            generation
            == self._playback_generation
        ):

            self.current_track = None

            self.audio_source = None


            if self._voice_is_connected():

                self.state = (
                    PlaybackState.CONNECTED
                )

            else:

                self.state = (
                    PlaybackState.DISCONNECTED
                )


    # ========================================================
    # PAUSAR
    # ========================================================

    async def pause(
        self
    ) -> PlaybackResult:

        if self.voice_client is None:

            return PlaybackResult(
                success=False,
                action="pause",
                message=(
                    "CTX no está conectado."
                ),
            )


        if not self.voice_client.is_playing():

            return PlaybackResult(
                success=False,
                action="pause",
                message=(
                    "No hay música reproduciéndose."
                ),
            )


        self.voice_client.pause()


        self.state = (
            PlaybackState.PAUSED
        )


        return PlaybackResult(
            success=True,
            action="pause",
            message=(
                "Música pausada."
            ),
        )


    # ========================================================
    # CONTINUAR
    # ========================================================

    async def resume(
        self
    ) -> PlaybackResult:

        if self.voice_client is None:

            return PlaybackResult(
                success=False,
                action="resume",
                message=(
                    "CTX no está conectado."
                ),
            )


        if not self.voice_client.is_paused():

            return PlaybackResult(
                success=False,
                action="resume",
                message=(
                    "La música no está pausada."
                ),
            )


        self.voice_client.resume()


        self.state = (
            PlaybackState.PLAYING
        )


        return PlaybackResult(
            success=True,
            action="resume",
            message=(
                "Música reanudada."
            ),
        )


    # ========================================================
    # STOP
    # ========================================================

    async def stop(
        self
    ) -> PlaybackResult:

        previous_track = (
            self.current_track
        )


        if self.voice_client is None:

            self.current_track = None

            self.audio_source = None


            self.state = (
                PlaybackState.STOPPED
            )


            return PlaybackResult(
                success=True,
                action="stop",
                message=(
                    "No había reproducción activa."
                ),
            )


        if (
            self.voice_client.is_playing()
            or self.voice_client.is_paused()
        ):

            self._mark_manual_stop()

            self.voice_client.stop()


        elif previous_track is not None:

            emit_track_stopped(
                guild_id=self.guild_id,
                track=previous_track,
            )


            self.current_track = None

            self.audio_source = None


        self.state = (
            PlaybackState.STOPPED
        )


        return PlaybackResult(
            success=True,
            action="stop",
            message=(
                "Música detenida."
            ),
        )


    # ========================================================
    # VOLUMEN
    # ========================================================

    async def set_volume(
        self,
        volume: int,
    ) -> PlaybackResult:

        final_volume = (
            self.normalize_volume(
                volume
            )
        )


        self.volume = (
            final_volume
        )


        if self.audio_source is not None:

            self.audio_source.volume = (
                final_volume / 100
            )


        return PlaybackResult(
            success=True,
            action="volume",
            message=(
                f"Volumen establecido "
                f"en {final_volume}%."
            ),
        )


    # ========================================================
    # RESUMEN SEGURO
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:

        data = (
            super().to_safe_dict()
        )


        data.update({

            "discord_voice_client":
                self.voice_client is not None,

            "voice_connected":
                self._voice_is_connected(),

            "audio_source_loaded":
                self.audio_source is not None,

            "playback_generation":
                self._playback_generation,

            "pending_manual_stops":
                len(
                    self._manual_stop_generations
                ),
        })


        return data


# ============================================================
# RESUMEN DEL BACKEND
# ============================================================

def get_discord_backend_summary() -> dict:

    return {

        "backend_name":
            DiscordPlaybackBackend.backend_name,

        "discord_voice":
            True,

        "ffmpeg":
            True,

        "pause":
            True,

        "resume":
            True,

        "stop":
            True,

        "volume":
            True,

        "playback_events":
            True,

        "finished_event":
            True,

        "stopped_event":
            True,

        "error_event":
            True,

        "generation_protection":
            True,

        "existing_voice_reuse":
            True,

        "audio_diagnostics":
            True,

        "real_audio_support":
            True,

        "automatic_next_track":
            False,
    }