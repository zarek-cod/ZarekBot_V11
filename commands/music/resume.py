"""
CTX V11
Comandos Discord para RESUME.

Comandos:

    !ctx_resume
    /resume

Utiliza:

    music.resume_controller
    music.permissions

La jerarquía real permanece centralizada
en music.permissions.
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.permissions import (
    can_resume,
)

from music.resume_controller import (
    ResumeResult,
    resume_current_track,
)


# ============================================================
# MENSAJE DE PERMISOS
# ============================================================

NO_RESUME_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "reanudar la reproducción de CTX."
)


# ============================================================
# PERMISO
# ============================================================

def can_use_resume_command(
    member: discord.Member,
) -> bool:
    """
    Comprueba el permiso RESUME
    usando la jerarquía real.
    """

    return can_resume(
        member
    )


# ============================================================
# FORMATEAR RESULTADO
# ============================================================

def _format_resume_result(
    result: ResumeResult,
) -> str:

    # ========================================================
    # ERROR
    # ========================================================

    if not result.success:

        return (
            "❌ **CTX MUSIC — RESUME**\n\n"
            f"{result.message}"
        )


    # ========================================================
    # YA ESTABA REPRODUCIÉNDOSE
    # ========================================================

    if result.already_playing:

        return (
            "▶️ **CTX MUSIC — YA ESTÁ REPRODUCIENDO**\n\n"
            f"{result.message}"
        )


    # ========================================================
    # REANUDADA
    # ========================================================

    track_name = (
        result.track.title
        if result.track
        else "Canción actual"
    )


    return (
        "▶️ **CTX MUSIC — REANUDADO**\n\n"
        f"**{track_name}**\n\n"
        "La reproducción continuó correctamente."
    )


# ============================================================
# COG
# ============================================================

class MusicResumeCommands(
    commands.Cog
):
    """
    Comandos RESUME de CTX Music.
    """

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_resume
    # ========================================================

    @commands.command(
        name="ctx_resume",
        aliases=[
            "ctx_res",
        ],
    )
    @commands.guild_only()
    async def ctx_resume(
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

        if not can_use_resume_command(
            ctx.author
        ):

            await ctx.send(
                NO_RESUME_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # RESUME
        # ====================================================

        result = await resume_current_track(
            ctx.guild.id
        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await ctx.send(
            _format_resume_result(
                result
            )
        )


    # ========================================================
    # /resume
    # ========================================================

    @app_commands.command(
        name="resume",
        description=(
            "Continúa la canción "
            "que CTX tiene pausada."
        ),
    )
    async def slash_resume(
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

        if not can_use_resume_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_RESUME_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # RESUME
        # ====================================================

        result = await resume_current_track(
            interaction.guild_id
        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await interaction.response.send_message(
            _format_resume_result(
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
        MusicResumeCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_resume_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_resume",

        "prefix_alias":
            "!ctx_res",

        "slash_command":
            "/resume",

        "uses_resume_controller":
            True,

        "resume_permission":
            True,

        "hierarchy_connected":
            True,

        "loaded_in_bot":
            False,
    }