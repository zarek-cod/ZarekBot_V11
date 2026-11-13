"""
CTX V11
Comandos Discord para PLAY.

Comandos disponibles:

    !ctx_play <canción>
    !ctx_p <canción>

    /play <canción>

Jerarquía musical:

    TODOS LOS MIEMBROS REALES -> permitido
    BOTS                       -> denegado

La autoridad real se obtiene desde:

    music.permissions

Este archivo NO contiene IDs ni reglas
hardcodeadas de jerarquía.
"""

from __future__ import annotations

import logging

import discord

from discord import app_commands
from discord.ext import commands

from music.permissions import (
    can_play,
    can_request_music,
)

from music.play_controller import (
    PlayRequestResult,
    play_music_request,
)


logger = logging.getLogger(__name__)


# ============================================================
# MENSAJES
# ============================================================

NO_MUSIC_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "utilizar el sistema musical de CTX."
)


# ============================================================
# PERMISOS
# ============================================================

def can_use_play_command(
    member: discord.Member,
) -> bool:
    """
    Permite PLAY a cualquier miembro real y
    mantiene fuera a las cuentas bot.

    Los controles globales siguen reservados
    a la jerarquía definida en music.permissions.
    """

    return (
        can_request_music(member)
        and can_play(member)
    )


# ============================================================
# CANAL DE VOZ
# ============================================================

def _get_voice_channel_id(
    member: discord.Member,
) -> int | None:
    """
    Devuelve el ID del canal de voz
    donde está actualmente el miembro.
    """

    voice_state = member.voice


    if voice_state is None:
        return None


    channel = voice_state.channel


    if channel is None:
        return None


    return channel.id


# ============================================================
# FORMATEAR RESULTADO
# ============================================================

def _format_play_result(
    result: PlayRequestResult,
    *,
    panel_url: str | None = None,
) -> str:
    """Build one compact confirmation; the principal UI lives in /player."""
    if not result.success:
        return f"No se pudo completar la solicitud: {result.message}"

    track = result.track
    if track is None:
        return "No pude obtener información de la canción."

    title = discord.utils.escape_markdown(track.title)
    if len(title) > 90:
        title = f"{title[:89].rstrip()}…"
    details = (
        f"`{track.formatted_duration}` · "
        f"solicitada por **{discord.utils.escape_markdown(track.requester_name)}**"
    )
    panel = f" · [Abrir panel]({panel_url})" if panel_url else ""
    if result.started:
        return f"▶ **{title}** · {details}{panel}"
    if result.queued:
        return f"＋ **{title}** · posición `{result.position}` · {details}{panel}"
    return f"{result.message}{panel}"


async def _sync_player_panel(
    *,
    guild_id: int,
    channel: discord.abc.Messageable,
    result: PlayRequestResult,
) -> str | None:
    """Create or update the single panel without coupling the music core to UI."""

    if not result.success:
        return None
    try:
        from commands.music.panel import panel_registry

        message, _ = await panel_registry.get_or_create(
            guild_id,
            channel,
            notice=result.message,
        )
        return message.jump_url
    except Exception:
        logger.exception("Could not synchronize CTX Music panel after /play")
        return None


# ============================================================
# EJECUCIÓN COMÚN
# ============================================================

async def _execute_play(
    *,
    guild_id: int,
    member: discord.Member,
    query: str,
    request_id: str | int | None = None,
) -> PlayRequestResult:
    """
    Núcleo compartido por:

        !ctx_play
        /play

    La comprobación de jerarquía se realiza
    ANTES de llamar esta función.
    """

    voice_channel_id = (
        _get_voice_channel_id(
            member
        )
    )


    # ========================================================
    # USUARIO FUERA DE VOZ
    # ========================================================

    if voice_channel_id is None:

        return PlayRequestResult(

            success=False,

            track=None,

            started=False,

            queued=False,

            position=None,

            connected=False,

            stream_ready=False,

            message=(
                "Debes entrar primero "
                "a un canal de voz."
            ),
        )

    existing_voice = member.guild.voice_client
    if (
        existing_voice is not None
        and existing_voice.is_connected()
        and existing_voice.channel is not None
        and existing_voice.channel.id != voice_channel_id
    ):
        return PlayRequestResult(
            success=False,
            track=None,
            started=False,
            queued=False,
            position=None,
            connected=True,
            stream_ready=False,
            message="Debes estar en el mismo canal de voz que CTX.",
        )


    # ========================================================
    # PLAY CONTROLLER
    # ========================================================

    return await play_music_request(

        guild_id=guild_id,

        voice_channel_id=voice_channel_id,

        query=query,

        requester_id=member.id,

        requester_name=member.display_name,
        request_id=request_id,
    )


# ============================================================
# COG
# ============================================================

class MusicPlayCommands(
    commands.Cog
):
    """
    Comandos PLAY de CTX Music.
    """

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_play
    # ========================================================

    @commands.command(
        name="ctx_play",
        aliases=[
            "ctx_p",
        ],
    )
    @commands.guild_only()
    async def ctx_play(
        self,
        ctx: commands.Context,
        *,
        query: str,
    ) -> None:
        """
        Ejemplos:

            !ctx_play Blinding Lights

            !ctx_play Bad Bunny Monaco

            !ctx_play https://youtube.com/...
        """

        # ====================================================
        # SERVIDOR
        # ====================================================

        if ctx.guild is None:

            await ctx.send(
                "❌ Este comando solamente "
                "puede utilizarse en un servidor."
            )

            return


        # ====================================================
        # MIEMBRO
        # ====================================================

        if not isinstance(
            ctx.author,
            discord.Member,
        ):

            await ctx.send(
                "❌ No pude identificar "
                "tu usuario dentro del servidor."
            )

            return


        # ====================================================
        # JERARQUÍA
        # ====================================================

        if not can_use_play_command(
            ctx.author
        ):

            await ctx.send(
                NO_MUSIC_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # EJECUTAR
        # ====================================================

        async with ctx.typing():

            result = await _execute_play(

                guild_id=ctx.guild.id,

                member=ctx.author,

                query=query,
                request_id=ctx.message.id,
            )


        # ====================================================
        # RESPONDER
        # ====================================================

        panel_url = await _sync_player_panel(
            guild_id=ctx.guild.id,
            channel=ctx.channel,
            result=result,
        )
        await ctx.send(
            _format_play_result(result, panel_url=panel_url),
            delete_after=15 if result.success else None,
        )


    # ========================================================
    # /play
    # ========================================================

    @app_commands.command(
        name="play",
        description=(
            "Busca una canción y la reproduce "
            "o la agrega a la cola."
        ),
    )
    @app_commands.describe(
        query=(
            "Nombre de la canción "
            "o enlace de YouTube"
        ),
    )
    async def slash_play(
        self,
        interaction: discord.Interaction,
        query: str,
    ) -> None:
        """
        Ejemplo:

            /play query:Blinding Lights
        """

        # ====================================================
        # SERVIDOR
        # ====================================================

        if (
            interaction.guild is None
            or interaction.guild_id is None
        ):

            await interaction.response.send_message(

                "❌ Este comando solamente "
                "puede utilizarse en un servidor.",

                ephemeral=True,
            )

            return


        # ====================================================
        # MIEMBRO
        # ====================================================

        if not isinstance(
            interaction.user,
            discord.Member,
        ):

            await interaction.response.send_message(

                "❌ No pude identificar "
                "tu usuario dentro del servidor.",

                ephemeral=True,
            )

            return


        # ====================================================
        # JERARQUÍA
        # ====================================================

        if not can_use_play_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_MUSIC_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # DEFER
        # ====================================================
        #
        # YouTube puede tardar varios segundos.
        #

        await interaction.response.defer(
            thinking=True,
            ephemeral=True,
        )


        # ====================================================
        # EJECUTAR
        # ====================================================

        result = await _execute_play(

            guild_id=interaction.guild_id,

            member=interaction.user,

            query=query,
            request_id=interaction.id,
        )


        # ====================================================
        # RESPONDER
        # ====================================================

        panel_url = None
        if interaction.channel is not None:
            panel_url = await _sync_player_panel(
                guild_id=interaction.guild_id,
                channel=interaction.channel,
                result=result,
            )
        await interaction.followup.send(
            _format_play_result(result, panel_url=panel_url),
            ephemeral=True,
        )


# ============================================================
# SETUP DE EXTENSIÓN
# ============================================================

async def setup(
    bot: commands.Bot,
) -> None:

    await bot.add_cog(
        MusicPlayCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_play_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_play",

        "prefix_alias":
            "!ctx_p",

        "slash_command":
            "/play",

        "uses_play_controller":
            True,

        "youtube_search":
            True,

        "youtube_urls":
            True,

        "direct_audio_urls":
            True,

        "auto_join":
            True,

        "queue_support":
            True,

        "request_music_permission":
            True,

        "play_permission":
            True,

        "hierarchy_connected":
            True,

        # Seguimos sin cargarlo en main.py.
        "loaded_in_bot":
            False,
    }
