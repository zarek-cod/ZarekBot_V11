"""
CTX V11
Comandos Discord para QUEUE.

Comandos:

    !ctx_queue
    !ctx_q
    /queue

Muestra:

- canción reproduciéndose
- canciones pendientes
- posición
- duración
- usuario que la solicitó

Todavía NO:
- elimina canciones
- limpia la cola
- reordena canciones

Esas acciones tendrán sus propios permisos.
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.permissions import (
    is_real_music_member,
)

from music.queue_controller import (
    QueueSnapshot,
    get_queue_snapshot,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

MAX_VISIBLE_TRACKS = 10


# ============================================================
# ACCESO
# ============================================================

NO_QUEUE_PERMISSION_MESSAGE = (
    "⛔ **CTX MUSIC — ACCESO DENEGADO**\n\n"
    "No tienes autoridad suficiente para "
    "administrar el sistema musical de CTX."
)


def can_use_queue_command(
    member: discord.Member,
) -> bool:
    """
    La visualización administrativa de la cola
    utiliza el permiso general de gestión musical.

    La jerarquía continúa centralizada en:

        music.permissions
    """

    return is_real_music_member(
        member
    )


# ============================================================
# DURACIÓN
# ============================================================

def _get_track_duration(
    track,
) -> str:

    try:

        return track.formatted_duration

    except Exception:

        return "Desconocida"


# ============================================================
# REQUESTER
# ============================================================

def _get_requester_name(
    track,
) -> str:

    requester = getattr(
        track,
        "requester_name",
        None,
    )


    if requester:

        return str(
            requester
        )


    return "Desconocido"


# ============================================================
# FORMATEAR COLA
# ============================================================

def format_queue_snapshot(
    snapshot: QueueSnapshot,
) -> str:
    """
    Convierte QueueSnapshot en un mensaje
    legible para Discord.

    Más adelante esto se reemplazará
    por el panel visual con botones.
    """

    lines: list[str] = []


    # ========================================================
    # CABECERA
    # ========================================================

    lines.append(
        "🎶 **CTX MUSIC — COLA MUSICAL**"
    )

    lines.append("")


    # ========================================================
    # SONANDO AHORA
    # ========================================================

    current = (
        snapshot.current_track
    )


    if current is not None:

        lines.append(
            "🎵 **SONANDO AHORA**"
        )

        lines.append(
            f"**{current.title}**"
        )

        lines.append(
            f"⏱️ `{_get_track_duration(current)}` "
            f"• 👤 `{_get_requester_name(current)}`"
        )


    else:

        lines.append(
            "🎵 **SONANDO AHORA**"
        )

        lines.append(
            "No hay ninguna canción reproduciéndose."
        )


    lines.append("")


    # ========================================================
    # COLA VACÍA
    # ========================================================

    if snapshot.pending_count == 0:

        lines.append(
            "📭 **COLA VACÍA**"
        )

        lines.append(
            "No hay canciones esperando."
        )


        return "\n".join(
            lines
        )


    # ========================================================
    # CANCIONES PENDIENTES
    # ========================================================

    lines.append(
        f"📜 **SIGUIENTES — "
        f"{snapshot.pending_count} pendiente(s)**"
    )

    lines.append("")


    visible_tracks = (
        snapshot.pending_tracks[
            :MAX_VISIBLE_TRACKS
        ]
    )


    for item in visible_tracks:

        track = (
            item.track
        )


        lines.append(
            f"**{item.position}.** "
            f"{track.title}"
        )

        lines.append(
            f"   ⏱️ `{_get_track_duration(track)}` "
            f"• 👤 `{_get_requester_name(track)}`"
        )


    # ========================================================
    # MÁS CANCIONES OCULTAS
    # ========================================================

    hidden_count = (
        snapshot.pending_count
        - len(visible_tracks)
    )


    if hidden_count > 0:

        lines.append("")

        lines.append(
            f"➕ Y **{hidden_count}** canción(es) más..."
        )


    # ========================================================
    # RESUMEN
    # ========================================================

    lines.append("")

    lines.append(
        f"📊 Total: **{snapshot.total_count}** "
        f"canción(es)"
    )


    return "\n".join(
        lines
    )


# ============================================================
# COG
# ============================================================

class MusicQueueCommands(
    commands.Cog
):
    """
    Comandos QUEUE de CTX Music.
    """

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    # ========================================================
    # !ctx_queue
    # ========================================================

    @commands.command(
        name="ctx_queue",
        aliases=[
            "ctx_q",
        ],
    )
    @commands.guild_only()
    async def ctx_queue(
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

        if not can_use_queue_command(
            ctx.author
        ):

            await ctx.send(
                NO_QUEUE_PERMISSION_MESSAGE
            )

            return


        # ====================================================
        # OBTENER COLA
        # ====================================================

        snapshot = (
            get_queue_snapshot(
                ctx.guild.id
            )
        )


        # ====================================================
        # RESPONDER
        # ====================================================

        await ctx.send(
            format_queue_snapshot(
                snapshot
            )
        )


    # ========================================================
    # /queue
    # ========================================================

    @app_commands.command(
        name="queue",
        description=(
            "Muestra la cola musical actual de CTX."
        ),
    )
    async def slash_queue(
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

        if not can_use_queue_command(
            interaction.user
        ):

            await interaction.response.send_message(

                NO_QUEUE_PERMISSION_MESSAGE,

                ephemeral=True,
            )

            return


        # ====================================================
        # OBTENER COLA
        # ====================================================

        snapshot = (
            get_queue_snapshot(
                interaction.guild_id
            )
        )


        # ====================================================
        # RESPUESTA
        # ====================================================

        await interaction.response.send_message(
            format_queue_snapshot(
                snapshot
            )
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot,
) -> None:

    await bot.add_cog(
        MusicQueueCommands(
            bot
        )
    )


# ============================================================
# RESUMEN
# ============================================================

def get_queue_command_summary() -> dict:

    return {

        "prefix_command":
            "!ctx_queue",

        "prefix_alias":
            "!ctx_q",

        "slash_command":
            "/queue",

        "uses_queue_controller":
            True,

        "available_to_real_members":
            True,

        "shows_current_track":
            True,

        "shows_pending_tracks":
            True,

        "max_visible_tracks":
            MAX_VISIBLE_TRACKS,

        "remove_track_command":
            False,

        "clear_queue_command":
            False,

        "reorder_queue_command":
            False,

        "hierarchy_connected":
            True,

        "loaded_in_bot":
            False,
    }
