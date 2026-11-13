"""
CTX V11
Comandos Discord para SKIP.

Comandos:

    !ctx_skip
    /skip

Utiliza:

    music.skip_controller
    music.permissions

SKIP ya incluye internamente:

- detener canción actual
- tomar siguiente canción
- refrescar stream de YouTube
- comenzar siguiente canción
- protección contra eventos atrasados
- protección contra SKIP simultáneo

La jerarquía real permanece centralizada
en music.permissions.
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.permissions import (
    can_skip,
)

from music.skip_controller import (
    SkipResult,
    skip_current_track,
)


# ============================================================
# MENSAJE DE PERMISOS
# ============================================================

NO_SKIP_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "saltar canciones en CTX."
)


# ============================================================
# PERMISO
# ============================================================

def can_use_skip_command(
    member: discord.Member,
) -> bool:
    """
    Comprueba el permiso SKIP
    usando music.permissions.
    """

    return can_skip(
        member
    )


# ============================================================
# FORMATEAR RESULTADO
# ============================================================

def _format_skip_result(
    result: SkipResult,
) -> str:
    """
    Convierte SkipResult en una respuesta
    para Discord.

    Más adelante será reemplazada por
    la interfaz visual completa.
    """

    # ========================================================
    # ERROR
    # ========================================================

    if not result.success:

        return (
            "❌ **CTX MUSIC — SKIP**\n\n"
            f"{result.message}"
        )


    # ========================================================
    # NO QUEDAN MÁS CANCIONES
    # ========================================================

    if result.next_track is None:

        skipped_name = (
            result.skipped_track.title
            if result.skipped_track
            else "Canción actual"
        )


        return (
            "⏭️ **CTX MUSIC — SKIP**\n\n"
            f"Se saltó **{skipped_name}**.\n\n"
            "📭 No quedan más canciones "
            "en la cola."
        )


    # ========================================================
    # SIGUIENTE CANCIÓN
    # ========================================================

    skipped_name = (
        result.skipped_track.title
        if result.skipped_track
        else "Canción anterior"
    )


    next_name = (
        result.next_track.title
    )


    refresh_text = (
        "✅ Stream actualizado"
        if result.stream_refreshed
        else "✅ Stream listo"
    )


    return (
        "⏭️ **CTX MUSIC — CANCIÓN SALTADA**\n\n"
        f"⏹️ Anterior: **{skipped_name}**\n"
        f"▶️ Ahora: **{next_name}**\n\n"
        f"{refresh_text}"
    )


# ============================================================
# COG
# ============================================================

class MusicSkipCommands(
    commands.Cog
):
    """
    Comandos SKIP de CTX Music.
    """

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_skip
    # ========================================================

    @commands.command(
        name="ctx_skip",
        aliases=[
            "ctx_s",
        ],
    )
    @commands.guild_only()
    async def ctx_skip(
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

        if not can_use_skip_command(
            ctx.author
        ):

            await ctx.send(
                NO_SKIP_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # SKIP
        # ====================================================

        async with ctx.typing():

            result = await skip_current_track(
                ctx.guild.id
            )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await ctx.send(
            _format_skip_result(
                result
            )
        )


    # ========================================================
    # /skip
    # ========================================================

    @app_commands.command(
        name="skip",
        description=(
            "Salta la canción actual "
            "y reproduce la siguiente."
        ),
    )
    async def slash_skip(
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

        if not can_use_skip_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_SKIP_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # DEFER
        # ====================================================
        #
        # La siguiente canción puede necesitar
        # refrescar su stream de YouTube.
        #

        await interaction.response.defer(
            thinking=True
        )


        # ====================================================
        # SKIP
        # ====================================================

        result = await skip_current_track(
            interaction.guild_id
        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await interaction.followup.send(
            _format_skip_result(
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
        MusicSkipCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_skip_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_skip",

        "prefix_alias":
            "!ctx_s",

        "slash_command":
            "/skip",

        "uses_skip_controller":
            True,

        "skip_permission":
            True,

        "refresh_before_next_play":
            True,

        "automatic_next_start":
            True,

        "stale_event_protection":
            True,

        "hierarchy_connected":
            True,

        "loaded_in_bot":
            False,
    }