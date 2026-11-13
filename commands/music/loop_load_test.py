"""
CTX V11
Prueba local de carga del módulo LOOP.

Comprueba:

    !ctx_loop
    !ctx_repeat
    /loop

NO:
- conecta Discord
- usa token
- reproduce audio
- entra a voz
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
    # CARGAR EXTENSIÓN LOOP
    # ========================================================

    await bot.load_extension(
        "commands.music.loop"
    )


    # ========================================================
    # COMANDO PRINCIPAL
    # ========================================================

    prefix_command = bot.get_command(
        "ctx_loop"
    )


    # ========================================================
    # ALIAS
    # ========================================================

    prefix_alias = bot.get_command(
        "ctx_repeat"
    )


    # ========================================================
    # SLASH COMMAND
    # ========================================================

    slash_command = bot.tree.get_command(
        "loop"
    )


    # ========================================================
    # COG
    # ========================================================

    cog = bot.get_cog(
        "MusicLoopCommands"
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    result = {

        "extension_loaded":
            "commands.music.loop"
            in bot.extensions,

        "cog_loaded":
            cog is not None,

        "prefix_ctx_loop":
            prefix_command is not None,

        "prefix_ctx_repeat":
            prefix_alias is not None,

        "slash_loop":
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
                "commands.music.loop"
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