"""
CTX V11
Comandos Discord para PAUSE.

Comandos:

    !ctx_pause
    /pause

Utiliza:

    music.pause_controller
    music.permissions

La jerarquía NO está escrita aquí.
Los permisos reales se obtienen desde
music.permissions.
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.pause_controller import (
    PauseResult,
    pause_current_track,
)

from music.permissions import (
    can_pause,
)


# ============================================================
# MENSAJE DE ACCESO DENEGADO
# ============================================================

NO_PAUSE_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "pausar la reproducción de CTX."
)


# ============================================================
# PERMISO
# ============================================================

def can_use_pause_command(
    member: discord.Member,
) -> bool:
    """
    Comprueba el permiso PAUSE real
    de la jerarquía musical.
    """

    return can_pause(
        member
    )


# ============================================================
# FORMATEAR RESULTADO
# ============================================================

def _format_pause_result(
    result: PauseResult,
) -> str:

    # ========================================================
    # ERROR
    # ========================================================

    if not result.success:

        return (
            "❌ **CTX MUSIC — PAUSE**\n\n"
            f"{result.message}"
        )


    # ========================================================
    # YA ESTABA PAUSADA
    # ========================================================

    if result.already_paused:

        return (
            "⏸️ **CTX MUSIC — YA ESTÁ PAUSADA**\n\n"
            f"{result.message}"
        )


    # ========================================================
    # PAUSADA CORRECTAMENTE
    # ========================================================

    track_name = (
        result.track.title
        if result.track
        else "Canción actual"
    )


    return (
        "⏸️ **CTX MUSIC — PAUSADO**\n\n"
        f"**{track_name}**\n\n"
        "La reproducción fue pausada correctamente."
    )


# ============================================================
# COG
# ============================================================

class MusicPauseCommands(
    commands.Cog
):
    """
    Comandos PAUSE de CTX Music.
    """

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_pause
    # ========================================================

    @commands.command(
        name="ctx_pause",
        aliases=[
            "ctx_pa",
        ],
    )
    @commands.guild_only()
    async def ctx_pause(
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

        if not can_use_pause_command(
            ctx.author
        ):

            await ctx.send(
                NO_PAUSE_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # PAUSAR
        # ====================================================

        result = await pause_current_track(
            ctx.guild.id
        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await ctx.send(
            _format_pause_result(
                result
            )
        )


    # ========================================================
    # /pause
    # ========================================================

    @app_commands.command(
        name="pause",
        description=(
            "Pausa la canción que "
            "CTX está reproduciendo."
        ),
    )
    async def slash_pause(
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

        if not can_use_pause_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_PAUSE_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # PAUSAR
        # ====================================================

        result = await pause_current_track(
            interaction.guild_id
        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await interaction.response.send_message(
            _format_pause_result(
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
        MusicPauseCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_pause_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_pause",

        "prefix_alias":
            "!ctx_pa",

        "slash_command":
            "/pause",

        "uses_pause_controller":
            True,

        "pause_permission":
            True,

        "hierarchy_connected":
            True,

        "loaded_in_bot":
            False,
    }