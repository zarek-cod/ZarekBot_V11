"""
CTX V11
Prueba local de carga del módulo STOP.

Comprueba:

    !ctx_stop
    !ctx_st
    /stop

NO:
- conecta Discord
- usa token
- reproduce audio
- ejecuta FFmpeg
"""

import asyncio

import discord

from discord.ext import commands


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
    # CARGAR STOP
    # ========================================================

    await bot.load_extension(
        "commands.music.stop"
    )


    # ========================================================
    # PREFIX
    # ========================================================

    prefix_command = bot.get_command(
        "ctx_stop"
    )


    # ========================================================
    # ALIAS
    # ========================================================

    prefix_alias = bot.get_command(
        "ctx_st"
    )


    # ========================================================
    # SLASH
    # ========================================================

    slash_command = bot.tree.get_command(
        "stop"
    )


    # ========================================================
    # COG
    # ========================================================

    cog = bot.get_cog(
        "MusicStopCommands"
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    result = {

        "extension_loaded":
            "commands.music.stop"
            in bot.extensions,

        "cog_loaded":
            cog is not None,

        "prefix_ctx_stop":
            prefix_command is not None,

        "prefix_ctx_st":
            prefix_alias is not None,

        "slash_stop":
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
                "commands.music.stop"
                in bot.extensions
                and cog is not None
                and prefix_command is not None
                and prefix_alias is not None
                and slash_command is not None
            ),
    }


    await bot.close()


    return result


if __name__ == "__main__":

    print(
        asyncio.run(
            run_test()
        )
    )