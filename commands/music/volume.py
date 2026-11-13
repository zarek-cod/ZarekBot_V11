"""
CTX V11
Comandos Discord para VOLUME.

Comandos:

    !ctx_volume <0-100>
    !ctx_vol <0-100>

    /volume <0-100>

Utiliza:

    music.volume_controller
    music.permissions

La jerarquía permanece centralizada
en music.permissions.
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.permissions import (
    can_change_volume,
)

from music.volume_controller import (
    VolumeResult,
    get_music_volume,
    set_music_volume,
)


# ============================================================
# MENSAJE DE PERMISOS
# ============================================================

NO_VOLUME_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "modificar el volumen de CTX."
)


# ============================================================
# PERMISO
# ============================================================

def can_use_volume_command(
    member: discord.Member,
) -> bool:
    """
    Comprueba el permiso real para
    modificar el volumen.
    """

    return can_change_volume(
        member
    )


# ============================================================
# FORMATEAR RESULTADO
# ============================================================

def _format_volume_result(
    result: VolumeResult,
) -> str:

    if not result.success:

        return (
            "❌ **CTX MUSIC — VOLUMEN**\n\n"
            f"{result.message}"
        )


    # --------------------------------------------------------
    # ICONO SEGÚN VOLUMEN
    # --------------------------------------------------------

    if result.final_volume == 0:

        icon = "🔇"

    elif result.final_volume <= 35:

        icon = "🔈"

    elif result.final_volume <= 70:

        icon = "🔉"

    else:

        icon = "🔊"


    return (
        f"{icon} **CTX MUSIC — VOLUMEN**\n\n"
        f"Volumen establecido en "
        f"**{result.final_volume}%**."
    )


# ============================================================
# COG
# ============================================================

class MusicVolumeCommands(
    commands.Cog
):
    """
    Comandos de volumen de CTX Music.
    """

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_volume
    # ========================================================

    @commands.command(
        name="ctx_volume",
        aliases=[
            "ctx_vol",
        ],
    )
    @commands.guild_only()
    async def ctx_volume(
        self,
        ctx: commands.Context,
        volume: int | None = None,
    ) -> None:
        """
        Ejemplos:

            !ctx_volume 80
            !ctx_vol 25

        Si no se indica número:
            muestra el volumen actual.
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

        if not can_use_volume_command(
            ctx.author
        ):

            await ctx.send(
                NO_VOLUME_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # CONSULTAR VOLUMEN
        # ====================================================

        if volume is None:

            current_volume = (
                get_music_volume(
                    ctx.guild.id
                )
            )


            await ctx.send(
                "🔊 **CTX MUSIC — VOLUMEN**\n\n"
                f"Volumen actual: "
                f"**{current_volume}%**"
            )

            return


        # ====================================================
        # CAMBIAR VOLUMEN
        # ====================================================

        result = await set_music_volume(

            guild_id=ctx.guild.id,

            volume=volume,
        )


        await ctx.send(
            _format_volume_result(
                result
            )
        )


    # ========================================================
    # /volume
    # ========================================================

    @app_commands.command(
        name="volume",
        description=(
            "Cambia el volumen de CTX Music."
        ),
    )
    @app_commands.describe(
        volume=(
            "Volumen entre 0 y 100"
        ),
    )
    async def slash_volume(
        self,
        interaction: discord.Interaction,
        volume: app_commands.Range[int, 0, 100],
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

        if not can_use_volume_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_VOLUME_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # CAMBIAR
        # ====================================================

        result = await set_music_volume(

            guild_id=interaction.guild_id,

            volume=int(
                volume
            ),
        )


        # ====================================================
        # RESPONDER
        # ====================================================

        await interaction.response.send_message(
            _format_volume_result(
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
        MusicVolumeCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_volume_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_volume",

        "prefix_alias":
            "!ctx_vol",

        "slash_command":
            "/volume",

        "minimum_volume":
            0,

        "maximum_volume":
            100,

        "uses_volume_controller":
            True,

        "volume_permission":
            True,

        "show_current_volume":
            True,

        "realtime_volume":
            True,

        "hierarchy_connected":
            True,

        "loaded_in_bot":
            False,
    }