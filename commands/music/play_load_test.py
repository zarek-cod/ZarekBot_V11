"""
CTX V11
Prueba local de carga del módulo PLAY.

Comprueba que Discord.py pueda registrar:

    !ctx_play
    !ctx_p
    /play

NO:
- conecta el bot a Discord
- usa el token
- entra a voz
- reproduce música
"""

import asyncio

import discord

from discord.ext import commands


# ============================================================
# PRUEBA
# ============================================================

async def run_test() -> dict:

    # ========================================================
    # INTENTS DE PRUEBA
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
        "commands.music.play"
    )


    # ========================================================
    # COMANDO PREFIX
    # ========================================================

    prefix_command = bot.get_command(
        "ctx_play"
    )


    prefix_alias = bot.get_command(
        "ctx_p"
    )


    # ========================================================
    # SLASH COMMAND
    # ========================================================

    slash_command = bot.tree.get_command(
        "play"
    )


    # ========================================================
    # COG
    # ========================================================

    cog = bot.get_cog(
        "MusicPlayCommands"
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    result = {

        "extension_loaded":
            "commands.music.play"
            in bot.extensions,

        "cog_loaded":
            cog is not None,

        "prefix_ctx_play":
            prefix_command is not None,

        "prefix_ctx_p":
            prefix_alias is not None,

        "slash_play":
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
                "commands.music.play"
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