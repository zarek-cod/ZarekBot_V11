"""
CTX V11
Prueba conjunta de todos los comandos musicales.

Comprueba simultáneamente:

PLAY
PAUSE
RESUME
SKIP
STOP
VOLUME
QUEUE
LOOP
AUTOPLAY

NO:
- conecta a Discord
- usa token
- entra a voz
- reproduce música
"""

import asyncio

import discord

from discord.ext import commands


# ============================================================
# EXTENSIONES MUSICALES
# ============================================================

MUSIC_EXTENSIONS = [

    "commands.music.play",

    "commands.music.pause",

    "commands.music.resume",

    "commands.music.skip",

    "commands.music.stop",

    "commands.music.volume",

    "commands.music.queue",

    "commands.music.loop",

    "commands.music.autoplay",
]


# ============================================================
# PREFIX COMMANDS
# ============================================================

PREFIX_COMMANDS = [

    "ctx_play",

    "ctx_pause",

    "ctx_resume",

    "ctx_skip",

    "ctx_stop",

    "ctx_volume",

    "ctx_queue",

    "ctx_loop",

    "ctx_autoplay",
]


# ============================================================
# SLASH COMMANDS
# ============================================================

SLASH_COMMANDS = [

    "play",

    "pause",

    "resume",

    "skip",

    "stop",

    "volume",

    "queue",

    "loop",

    "autoplay",
]


# ============================================================
# COGS
# ============================================================

COGS = [

    "MusicPlayCommands",

    "MusicPauseCommands",

    "MusicResumeCommands",

    "MusicSkipCommands",

    "MusicStopCommands",

    "MusicVolumeCommands",

    "MusicQueueCommands",

    "MusicLoopCommands",

    "MusicAutoplayCommands",
]


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
    # CARGAR TODAS LAS EXTENSIONES
    # ========================================================

    loaded_extensions = []


    for extension in MUSIC_EXTENSIONS:

        await bot.load_extension(
            extension
        )

        loaded_extensions.append(
            extension
        )


    # ========================================================
    # COMPROBAR PREFIX
    # ========================================================

    prefix_status = {

        command_name:
            bot.get_command(
                command_name
            ) is not None

        for command_name
        in PREFIX_COMMANDS
    }


    # ========================================================
    # COMPROBAR SLASH
    # ========================================================

    slash_status = {

        command_name:
            bot.tree.get_command(
                command_name
            ) is not None

        for command_name
        in SLASH_COMMANDS
    }


    # ========================================================
    # COMPROBAR COGS
    # ========================================================

    cog_status = {

        cog_name:
            bot.get_cog(
                cog_name
            ) is not None

        for cog_name
        in COGS
    }


    # ========================================================
    # ESTADOS GENERALES
    # ========================================================

    all_extensions_loaded = (
        len(loaded_extensions)
        == len(MUSIC_EXTENSIONS)
    )


    all_prefix_loaded = (
        all(
            prefix_status.values()
        )
    )


    all_slash_loaded = (
        all(
            slash_status.values()
        )
    )


    all_cogs_loaded = (
        all(
            cog_status.values()
        )
    )


    # ========================================================
    # RESULTADO
    # ========================================================

    result = {

        "extensions_loaded":
            len(loaded_extensions),

        "expected_extensions":
            len(MUSIC_EXTENSIONS),

        "all_extensions_loaded":
            all_extensions_loaded,

        "all_prefix_loaded":
            all_prefix_loaded,

        "all_slash_loaded":
            all_slash_loaded,

        "all_cogs_loaded":
            all_cogs_loaded,

        "prefix_commands":
            prefix_status,

        "slash_commands":
            slash_status,

        "cogs":
            cog_status,

        "ready_for_main":
            (
                all_extensions_loaded
                and all_prefix_loaded
                and all_slash_loaded
                and all_cogs_loaded
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