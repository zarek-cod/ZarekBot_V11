"""
CTX V11
Prueba local de carga del módulo AUTOPLAY.

Comprueba:

    !ctx_autoplay
    !ctx_auto
    /autoplay

NO:
- conecta Discord
- utiliza token
- reproduce audio
- busca recomendaciones
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
        "commands.music.autoplay"
    )


    # ========================================================
    # PREFIX PRINCIPAL
    # ========================================================

    prefix_command = bot.get_command(
        "ctx_autoplay"
    )


    # ========================================================
    # ALIAS
    # ========================================================

    prefix_alias = bot.get_command(
        "ctx_auto"
    )


    # ========================================================
    # SLASH
    # ========================================================

    slash_command = bot.tree.get_command(
        "autoplay"
    )


    # ========================================================
    # COG
    # ========================================================

    cog = bot.get_cog(
        "MusicAutoplayCommands"
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    result = {

        "extension_loaded":
            "commands.music.autoplay"
            in bot.extensions,

        "cog_loaded":
            cog is not None,

        "prefix_ctx_autoplay":
            prefix_command is not None,

        "prefix_ctx_auto":
            prefix_alias is not None,

        "slash_autoplay":
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
                "commands.music.autoplay"
                in bot.extensions
                and cog is not None
                and prefix_command is not None
                and prefix_alias is not None
                and slash_command is not None
            ),
    }


    # ========================================================
    # CERRAR BOT LOCAL
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