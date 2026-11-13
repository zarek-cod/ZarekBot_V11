"""
CTX V11
Comandos Discord para LOOP.

Comandos:

    !ctx_loop
    !ctx_repeat
    /loop

Modos:

    on
    off
    toggle

La jerarquía real permanece centralizada
en music.permissions.
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.loop_controller import (
    LoopResult,
    disable_loop,
    enable_loop,
    toggle_loop,
)

from music.permissions import (
    can_change_loop,
)


# ============================================================
# MENSAJE DE PERMISOS
# ============================================================

NO_LOOP_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "modificar el modo LOOP de CTX."
)


# ============================================================
# MODOS
# ============================================================

VALID_LOOP_MODES = {
    "on",
    "off",
    "toggle",
}


# ============================================================
# PERMISO
# ============================================================

def can_use_loop_command(
    member: discord.Member,
) -> bool:
    """
    Comprueba el permiso LOOP usando
    la jerarquía real de CTX.
    """

    return can_change_loop(
        member
    )


# ============================================================
# EJECUTAR LOOP
# ============================================================

async def execute_loop_mode(
    guild_id: int,
    mode: str,
) -> LoopResult:

    normalized_mode = (
        mode.strip().lower()
    )


    if normalized_mode == "on":

        return await enable_loop(
            guild_id
        )


    if normalized_mode == "off":

        return await disable_loop(
            guild_id
        )


    return await toggle_loop(
        guild_id
    )


# ============================================================
# FORMATEAR RESULTADO
# ============================================================

def _format_loop_result(
    result: LoopResult,
) -> str:

    if not result.success:

        return (
            "❌ **CTX MUSIC — LOOP**\n\n"
            f"{result.message}"
        )


    if result.enabled:

        return (
            "🔁 **CTX MUSIC — LOOP ACTIVADO**\n\n"
            "La canción actual volverá a reproducirse "
            "cuando termine."
        )


    return (
        "➡️ **CTX MUSIC — LOOP DESACTIVADO**\n\n"
        "Cuando termine la canción actual, "
        "CTX continuará con la siguiente."
    )


# ============================================================
# COG
# ============================================================

class MusicLoopCommands(
    commands.Cog
):

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_loop
    # ========================================================

    @commands.command(
        name="ctx_loop",
        aliases=[
            "ctx_repeat",
        ],
    )
    @commands.guild_only()
    async def ctx_loop(
        self,
        ctx: commands.Context,
        mode: str = "toggle",
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
        # USUARIO
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

        if not can_use_loop_command(
            ctx.author
        ):

            await ctx.send(
                NO_LOOP_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # NORMALIZAR MODO
        # ====================================================

        normalized_mode = (
            mode.strip().lower()
        )


        # ====================================================
        # VALIDAR MODO
        # ====================================================

        if normalized_mode not in VALID_LOOP_MODES:

            await ctx.send(
                "❌ **CTX MUSIC — LOOP**\n\n"
                "Modo inválido.\n\n"
                "Usa:\n"
                "`!ctx_loop on`\n"
                "`!ctx_loop off`\n"
                "`!ctx_loop toggle`\n"
                "o simplemente `!ctx_loop`."
            )

            return


        # ====================================================
        # EJECUTAR
        # ====================================================

        result = await execute_loop_mode(

            guild_id=ctx.guild.id,

            mode=normalized_mode,
        )


        # ====================================================
        # RESPONDER
        # ====================================================

        await ctx.send(
            _format_loop_result(
                result
            )
        )


    # ========================================================
    # /loop
    # ========================================================

    @app_commands.command(
        name="loop",
        description=(
            "Activa o desactiva la repetición "
            "de la canción actual."
        ),
    )
    @app_commands.describe(
        mode=(
            "Selecciona qué hacer con LOOP."
        ),
    )
    @app_commands.choices(
        mode=[

            app_commands.Choice(
                name="Activar",
                value="on",
            ),

            app_commands.Choice(
                name="Desactivar",
                value="off",
            ),

            app_commands.Choice(
                name="Alternar",
                value="toggle",
            ),
        ]
    )
    async def slash_loop(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
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
        # USUARIO
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

        if not can_use_loop_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_LOOP_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # EJECUTAR
        # ====================================================

        result = await execute_loop_mode(

            guild_id=interaction.guild_id,

            mode=mode.value,
        )


        # ====================================================
        # RESPONDER
        # ====================================================

        await interaction.response.send_message(
            _format_loop_result(
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
        MusicLoopCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_loop_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_loop",

        "prefix_alias":
            "!ctx_repeat",

        "slash_command":
            "/loop",

        "supports_on":
            True,

        "supports_off":
            True,

        "supports_toggle":
            True,

        "uses_loop_controller":
            True,

        "loop_permission":
            True,

        "real_track_repeat":
            True,

        "hierarchy_connected":
            True,

        "loaded_in_bot":
            False,
    }