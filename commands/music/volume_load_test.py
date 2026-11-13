"""
CTX V11
Prueba local de carga del módulo VOLUME.

Comprueba:

    !ctx_volume
    !ctx_vol
    /volume

NO:
- conecta el bot a Discord
- utiliza token
- entra a voz
- reproduce audio
"""

import asyncio

import discord

from discord.ext import commands


# ============================================================
# PRUEBA
# ============================================================

async def run_test() -> dict:

    # ========================================================
    # INTENTS
    # ========================================================

    intents = discord.Intents.none()

    intents.guilds = True
    intents.message_content = True


    # ========================================================
    # BOT LOCAL
    # ========================================================

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
    )


    # ========================================================
    # CARGAR EXTENSIÓN
    # ========================================================

    await bot.load_extension(
        "commands.music.volume"
    )


    # ========================================================
    # PREFIX PRINCIPAL
    # ========================================================

    prefix_command = bot.get_command(
        "ctx_volume"
    )


    # ========================================================
    # ALIAS
    # ========================================================

    prefix_alias = bot.get_command(
        "ctx_vol"
    )


    # ========================================================
    # SLASH
    # ========================================================

    slash_command = bot.tree.get_command(
        "volume"
    )


    # ========================================================
    # COG
    # ========================================================

    cog = bot.get_cog(
        "MusicVolumeCommands"
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    result = {

        "extension_loaded":
            "commands.music.volume"
            in bot.extensions,

        "cog_loaded":
            cog is not None,

        "prefix_ctx_volume":
            prefix_command is not None,

        "prefix_ctx_vol":
            prefix_alias is not None,

        "slash_volume":
            slash_command is not None,

        "prefix_name":
            (
                prefix_command.name
                if prefix_command
                else None
            ),

        "slash_name":
            (
                slash_command.name
                if slash_command
                else None
            ),

        "ready_for_main":
            (
                "commands.music.volume"
                in bot.extensions
                and cog is not None
                and prefix_command is not None
                and prefix_alias is not None
                and slash_command is not None
            ),
    }


    # ========================================================
    # CERRAR BOT
    # ========================================================

    await bot.close()


    return result


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    print(
        asyncio.run(
            run_test()
        )
    )