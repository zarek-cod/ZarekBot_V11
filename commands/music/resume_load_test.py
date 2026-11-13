"""
CTX V11
Prueba local de carga del módulo RESUME.

Comprueba que Discord.py pueda registrar:

    !ctx_resume
    !ctx_res
    /resume

NO:
- conecta el bot a Discord
- usa token
- reproduce música
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
    # CARGAR EXTENSIÓN
    # ========================================================

    await bot.load_extension(
        "commands.music.resume"
    )


    # ========================================================
    # PREFIX PRINCIPAL
    # ========================================================

    prefix_command = bot.get_command(
        "ctx_resume"
    )


    # ========================================================
    # ALIAS
    # ========================================================

    prefix_alias = bot.get_command(
        "ctx_res"
    )


    # ========================================================
    # SLASH
    # ========================================================

    slash_command = bot.tree.get_command(
        "resume"
    )


    # ========================================================
    # COG
    # ========================================================

    cog = bot.get_cog(
        "MusicResumeCommands"
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    result = {

        "extension_loaded":
            "commands.music.resume"
            in bot.extensions,

        "cog_loaded":
            cog is not None,

        "prefix_ctx_resume":
            prefix_command is not None,

        "prefix_ctx_res":
            prefix_alias is not None,

        "slash_resume":
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
                "commands.music.resume"
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