"""
CTX V11
Comandos Discord para AUTOPLAY.

Comandos:

    !ctx_autoplay
    !ctx_auto

    /autoplay

Modos:

    on
    off
    toggle

IMPORTANTE:

AUTOPLAY actualmente controla el estado lógico.

La búsqueda automática de recomendaciones
todavía NO está conectada.

Utiliza:

    music.autoplay_controller
    music.permissions
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.autoplay_controller import (
    AutoplayResult,
    disable_autoplay,
    enable_autoplay,
    toggle_autoplay,
)

from music.permissions import (
    can_change_autoplay,
)


# ============================================================
# MENSAJE DE PERMISOS
# ============================================================

NO_AUTOPLAY_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "modificar AUTOPLAY."
)


# ============================================================
# MODOS
# ============================================================

VALID_AUTOPLAY_MODES = {
    "on",
    "off",
    "toggle",
}


# ============================================================
# PERMISO
# ============================================================

def can_use_autoplay_command(
    member: discord.Member,
) -> bool:
    """
    Comprueba el permiso AUTOPLAY
    usando music.permissions.
    """

    return can_change_autoplay(
        member
    )


# ============================================================
# EJECUTAR MODO
# ============================================================

async def execute_autoplay_mode(
    guild_id: int,
    mode: str,
) -> AutoplayResult:

    normalized_mode = (
        mode.strip().lower()
    )


    if normalized_mode == "on":

        return await enable_autoplay(
            guild_id
        )


    if normalized_mode == "off":

        return await disable_autoplay(
            guild_id
        )


    return await toggle_autoplay(
        guild_id
    )


# ============================================================
# FORMATEAR RESULTADO
# ============================================================

def _format_autoplay_result(
    result: AutoplayResult,
) -> str:

    if not result.success:

        return (
            "❌ **CTX MUSIC — AUTOPLAY**\n\n"
            f"{result.message}"
        )


    if result.enabled:

        return (
            "♾️ **CTX MUSIC — AUTOPLAY ACTIVADO**\n\n"
            "AUTOPLAY quedó habilitado.\n\n"
            "Cuando conectemos el sistema de "
            "recomendaciones, CTX podrá continuar "
            "con música relacionada al terminar la cola."
        )


    return (
        "⏹️ **CTX MUSIC — AUTOPLAY DESACTIVADO**\n\n"
        "CTX dejará de utilizar AUTOPLAY."
    )


# ============================================================
# COG
# ============================================================

class MusicAutoplayCommands(
    commands.Cog
):

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_autoplay
    # ========================================================

    @commands.command(
        name="ctx_autoplay",
        aliases=[
            "ctx_auto",
        ],
    )
    @commands.guild_only()
    async def ctx_autoplay(
        self,
        ctx: commands.Context,
        mode: str = "toggle",
    ) -> None:
        """
        Ejemplos:

            !ctx_autoplay
            !ctx_autoplay on
            !ctx_autoplay off

            !ctx_auto
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

        if not can_use_autoplay_command(
            ctx.author
        ):

            await ctx.send(
                NO_AUTOPLAY_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # NORMALIZAR
        # ====================================================

        normalized_mode = (
            mode.strip().lower()
        )


        # ====================================================
        # VALIDAR
        # ====================================================

        if normalized_mode not in VALID_AUTOPLAY_MODES:

            await ctx.send(
                "❌ **CTX MUSIC — AUTOPLAY**\n\n"
                "Modo inválido.\n\n"
                "Usa:\n"
                "`!ctx_autoplay on`\n"
                "`!ctx_autoplay off`\n"
                "`!ctx_autoplay toggle`\n"
                "o simplemente `!ctx_autoplay`."
            )

            return


        # ====================================================
        # EJECUTAR
        # ====================================================

        result = await execute_autoplay_mode(

            guild_id=ctx.guild.id,

            mode=normalized_mode,
        )


        # ====================================================
        # RESPONDER
        # ====================================================

        await ctx.send(
            _format_autoplay_result(
                result
            )
        )


    # ========================================================
    # /autoplay
    # ========================================================

    @app_commands.command(
        name="autoplay",
        description=(
            "Activa o desactiva AUTOPLAY "
            "de CTX Music."
        ),
    )
    @app_commands.describe(
        mode=(
            "Selecciona qué hacer con AUTOPLAY."
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
    async def slash_autoplay(
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

        if not can_use_autoplay_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_AUTOPLAY_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # EJECUTAR
        # ====================================================

        result = await execute_autoplay_mode(

            guild_id=interaction.guild_id,

            mode=mode.value,
        )


        # ====================================================
        # RESPONDER
        # ====================================================

        await interaction.response.send_message(
            _format_autoplay_result(
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
        MusicAutoplayCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_autoplay_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_autoplay",

        "prefix_alias":
            "!ctx_auto",

        "slash_command":
            "/autoplay",

        "supports_on":
            True,

        "supports_off":
            True,

        "supports_toggle":
            True,

        "uses_autoplay_controller":
            True,

        "autoplay_permission":
            True,

        # Estado lógico listo.
        "autoplay_state":
            True,

        # Recomendaciones reales aún pendientes.
        "automatic_recommendations":
            False,

        "hierarchy_connected":
            True,

        "loaded_in_bot":
            False,
    }