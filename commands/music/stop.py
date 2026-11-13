"""
CTX V11
Comandos Discord para STOP.

Comandos:

    !ctx_stop
    /stop

STOP realiza:

- detener canción actual
- limpiar canciones pendientes
- sincronizar Session
- sincronizar Player
- sincronizar Backend

Los permisos se obtienen desde:

    music.permissions
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.permissions import (
    can_stop,
)

from music.stop_controller import (
    StopResult,
    stop_music,
)


# ============================================================
# MENSAJE DE PERMISOS
# ============================================================

NO_STOP_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "detener la reproducción de CTX."
)


# ============================================================
# PERMISO
# ============================================================

def can_use_stop_command(
    member: discord.Member,
) -> bool:
    """
    Comprueba el permiso STOP
    usando la jerarquía real.
    """

    return can_stop(
        member
    )


# ============================================================
# FORMATEAR RESULTADO
# ============================================================

def _format_stop_result(
    result: StopResult,
) -> str:

    # ========================================================
    # ERROR
    # ========================================================

    if not result.success:

        return (
            "❌ **CTX MUSIC — STOP**\n\n"
            f"{result.message}"
        )


    # ========================================================
    # CANCIÓN DETENIDA
    # ========================================================

    if result.stopped_track is not None:

        track_name = (
            result.stopped_track.title
        )

    else:

        track_name = (
            "No había una canción activa"
        )


    # ========================================================
    # COLA
    # ========================================================

    queue_text = (
        "🗑️ La cola fue limpiada."
        if result.queue_cleared
        else
        "📜 La cola fue conservada."
    )


    return (
        "⏹️ **CTX MUSIC — DETENIDO**\n\n"
        f"🎵 **{track_name}**\n\n"
        f"{queue_text}"
    )


# ============================================================
# COG
# ============================================================

class MusicStopCommands(
    commands.Cog
):
    """
    Comandos STOP de CTX Music.
    """

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_stop
    # ========================================================

    @commands.command(
        name="ctx_stop",
        aliases=[
            "ctx_st",
        ],
    )
    @commands.guild_only()
    async def ctx_stop(
        self,
        ctx: commands.Context,
    ) -> None:

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

        if not can_use_stop_command(
            ctx.author
        ):

            await ctx.send(
                NO_STOP_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # STOP
        # ====================================================

        result = await stop_music(
            guild_id=ctx.guild.id,
            clear_queue=True,
        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await ctx.send(
            _format_stop_result(
                result
            )
        )


    # ========================================================
    # /stop
    # ========================================================

    @app_commands.command(
        name="stop",
        description=(
            "Detiene CTX Music "
            "y limpia la cola."
        ),
    )
    async def slash_stop(
        self,
        interaction: discord.Interaction,
    ) -> None:

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

        if not can_use_stop_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_STOP_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # STOP
        # ====================================================

        result = await stop_music(

            guild_id=interaction.guild_id,

            clear_queue=True,
        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await interaction.response.send_message(
            _format_stop_result(
                result
            )
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot,
) -> None:

    await bot.add_cog(
        MusicStopCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_stop_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_stop",

        "prefix_alias":
            "!ctx_st",

        "slash_command":
            "/stop",

        "uses_stop_controller":
            True,

        "stop_permission":
            True,

        "clears_queue":
            True,

        "hierarchy_connected":
            True,

        "loaded_in_bot":
            False,
    }