"""
CTX V11
Panel visual interactivo de CTX Music.

Comandos:
    /player
    !ctx_player
    !ctx_panel

Este módulo NO reemplaza los comandos existentes.
Solo muestra un panel visual y reutiliza los controladores
que ya funcionan en CTX Music.
"""

from __future__ import annotations

import discord

from discord import app_commands
from discord.ext import commands

from music.autoplay_controller import toggle_autoplay
from music.loop_controller import toggle_loop
from music.pause_controller import pause_current_track
from music.permissions import can_manage_music
from music.resume_controller import resume_current_track
from music.session import music_session_manager
from music.skip_controller import skip_current_track
from music.stop_controller import stop_music
from music.volume_controller import (
    get_music_volume,
    set_music_volume,
)

PANEL_COLOR = discord.Color.from_rgb(180, 20, 45)
MAX_QUEUE_PREVIEW = 5


def _status_text(guild_id: int) -> tuple[str, str]:
    session = music_session_manager.get_session(guild_id)

    if session.current_track is None:
        return "⏹️", "EN ESPERA"

    if session.state.paused:
        return "⏸️", "PAUSADO"

    return "▶️", "REPRODUCIENDO"


def _on_off(value: bool) -> str:
    return "🟢 ON" if value else "⚫ OFF"


def _safe_track_url(track) -> str | None:
    value = getattr(track, "url", None)
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    return None


def _safe_thumbnail(track) -> str | None:
    value = getattr(track, "thumbnail", None)
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    return None


def _queue_preview(guild_id: int) -> str:
    session = music_session_manager.get_session(guild_id)
    tracks = session.queue.get_all()

    if not tracks:
        return "📭 No hay canciones esperando."

    lines: list[str] = []

    for index, track in enumerate(
        tracks[:MAX_QUEUE_PREVIEW],
        start=1,
    ):
        lines.append(
            f"`{index:02d}.` **{track.title}** • `{track.formatted_duration}`"
        )

    hidden = len(tracks) - len(lines)

    if hidden > 0:
        lines.append(
            f"➕ **{hidden}** canción(es) más..."
        )

    return "\n".join(lines)


def build_player_embed(
    guild_id: int,
    *,
    notice: str | None = None,
) -> discord.Embed:

    session = music_session_manager.get_session(guild_id)
    track = session.current_track

    status_icon, status_name = _status_text(guild_id)

    embed = discord.Embed(
        title=f"🎵 CTX MUSIC • {status_name}",
        color=PANEL_COLOR,
    )

    if track is None:
        embed.description = (
            "No hay ninguna canción reproduciéndose.\n\n"
            "Usa `/play` para iniciar CTX Music."
        )

    else:
        track_url = _safe_track_url(track)

        if track_url:
            embed.description = (
                f"### [{track.title}]({track_url})"
            )
        else:
            embed.description = (
                f"### {track.title}"
            )

        thumbnail = _safe_thumbnail(track)

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        embed.add_field(
            name="⏱️ Duración",
            value=f"`{track.formatted_duration}`",
            inline=True,
        )

        embed.add_field(
            name="👤 Solicitada por",
            value=f"`{track.requester_name}`",
            inline=True,
        )

        embed.add_field(
            name="📡 Estado",
            value=f"{status_icon} **{status_name}**",
            inline=True,
        )

    embed.add_field(
        name="🔊 Volumen",
        value=f"`{session.state.volume}%`",
        inline=True,
    )

    embed.add_field(
        name="🔁 Loop",
        value=_on_off(session.state.loop_enabled),
        inline=True,
    )

    embed.add_field(
        name="♾️ Autoplay",
        value=_on_off(session.state.autoplay_enabled),
        inline=True,
    )

    embed.add_field(
        name=f"📜 Cola • {session.queue.size()}",
        value=_queue_preview(guild_id),
        inline=False,
    )

    if notice:
        embed.add_field(
            name="✨ Última acción",
            value=notice,
            inline=False,
        )

    embed.set_footer(
        text="CTX RANK X7 • Music System V11"
    )

    return embed


class CTXMusicView(discord.ui.View):

    def __init__(
        self,
        guild_id: int,
    ) -> None:

        super().__init__(timeout=3600)

        self.guild_id = guild_id
        self._sync_buttons()


    async def _check_permission(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if not isinstance(
            interaction.user,
            discord.Member,
        ):
            await interaction.response.send_message(
                "❌ No pude identificar tu usuario.",
                ephemeral=True,
            )
            return False

        if not can_manage_music(
            interaction.user
        ):
            await interaction.response.send_message(
                "⛔ No tienes permiso para controlar CTX Music.",
                ephemeral=True,
            )
            return False

        return True


    def _sync_buttons(self) -> None:

        session = music_session_manager.get_session(
            self.guild_id
        )

        has_track = (
            session.current_track is not None
        )

        self.pause_resume_button.disabled = not has_track
        self.skip_button.disabled = not has_track
        self.stop_button.disabled = not has_track

        if session.state.paused:
            self.pause_resume_button.label = "Reanudar"
            self.pause_resume_button.emoji = "▶️"
            self.pause_resume_button.style = (
                discord.ButtonStyle.success
            )
        else:
            self.pause_resume_button.label = "Pausar"
            self.pause_resume_button.emoji = "⏸️"
            self.pause_resume_button.style = (
                discord.ButtonStyle.secondary
            )

        self.loop_button.style = (
            discord.ButtonStyle.success
            if session.state.loop_enabled
            else discord.ButtonStyle.secondary
        )

        self.autoplay_button.style = (
            discord.ButtonStyle.success
            if session.state.autoplay_enabled
            else discord.ButtonStyle.secondary
        )


    async def _refresh(
        self,
        interaction: discord.Interaction,
        *,
        notice: str | None = None,
    ) -> None:

        self._sync_buttons()

        embed = build_player_embed(
            self.guild_id,
            notice=notice,
        )

        await interaction.edit_original_response(
            embed=embed,
            view=self,
        )


    @discord.ui.button(
        label="Pausar",
        emoji="⏸️",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def pause_resume_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        await interaction.response.defer()

        session = music_session_manager.get_session(
            self.guild_id
        )

        if session.state.paused:
            result = await resume_current_track(
                self.guild_id
            )
        else:
            result = await pause_current_track(
                self.guild_id
            )

        await self._refresh(
            interaction,
            notice=result.message,
        )


    @discord.ui.button(
        label="Saltar",
        emoji="⏭️",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def skip_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        await interaction.response.defer()

        result = await skip_current_track(
            self.guild_id
        )

        await self._refresh(
            interaction,
            notice=result.message,
        )


    @discord.ui.button(
        label="Detener",
        emoji="⏹️",
        style=discord.ButtonStyle.danger,
        row=0,
    )
    async def stop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        await interaction.response.defer()

        result = await stop_music(
            guild_id=self.guild_id,
            clear_queue=True,
        )

        await self._refresh(
            interaction,
            notice=result.message,
        )


    @discord.ui.button(
        label="Loop",
        emoji="🔁",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def loop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        await interaction.response.defer()

        result = await toggle_loop(
            self.guild_id
        )

        await self._refresh(
            interaction,
            notice=result.message,
        )


    @discord.ui.button(
        label="Autoplay",
        emoji="♾️",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def autoplay_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        await interaction.response.defer()

        result = await toggle_autoplay(
            self.guild_id
        )

        await self._refresh(
            interaction,
            notice=result.message,
        )


    @discord.ui.button(
        label="-10",
        emoji="🔉",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def volume_down_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        await interaction.response.defer()

        current = get_music_volume(
            self.guild_id
        )

        result = await set_music_volume(
            guild_id=self.guild_id,
            volume=max(0, current - 10),
        )

        await self._refresh(
            interaction,
            notice=result.message,
        )


    @discord.ui.button(
        label="+10",
        emoji="🔊",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def volume_up_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        await interaction.response.defer()

        current = get_music_volume(
            self.guild_id
        )

        result = await set_music_volume(
            guild_id=self.guild_id,
            volume=min(100, current + 10),
        )

        await self._refresh(
            interaction,
            notice=result.message,
        )


    @discord.ui.button(
        label="Cola",
        emoji="📜",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def queue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        session = music_session_manager.get_session(
            self.guild_id
        )

        tracks = session.queue.get_all()

        if not tracks:
            text = "📭 No hay canciones esperando."
        else:
            lines = []

            for index, track in enumerate(
                tracks[:10],
                start=1,
            ):
                lines.append(
                    f"**{index}.** {track.title} • `{track.formatted_duration}`"
                )

            hidden = len(tracks) - len(lines)

            if hidden > 0:
                lines.append(
                    f"\n➕ {hidden} canción(es) más."
                )

            text = "\n".join(lines)

        await interaction.response.send_message(
            f"📜 **CTX MUSIC — COLA**\n\n{text}",
            ephemeral=True,
        )


    @discord.ui.button(
        label="Actualizar",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def refresh_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:

        if not await self._check_permission(interaction):
            return

        await interaction.response.defer()

        await self._refresh(
            interaction,
            notice="Panel actualizado.",
        )


class MusicPanelCommands(
    commands.Cog
):

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:

        self.bot = bot


    @commands.command(
        name="ctx_player",
        aliases=[
            "ctx_panel",
        ],
    )
    @commands.guild_only()
    async def ctx_player(
        self,
        ctx: commands.Context,
    ) -> None:

        if ctx.guild is None:
            return

        if not isinstance(
            ctx.author,
            discord.Member,
        ):
            return

        if not can_manage_music(
            ctx.author
        ):
            await ctx.send(
                "⛔ No tienes permiso para controlar CTX Music."
            )
            return

        view = CTXMusicView(
            ctx.guild.id
        )

        await ctx.send(
            embed=build_player_embed(
                ctx.guild.id
            ),
            view=view,
        )


    @app_commands.command(
        name="player",
        description=(
            "Abre el panel interactivo de CTX Music."
        ),
    )
    async def slash_player(
        self,
        interaction: discord.Interaction,
    ) -> None:

        if (
            interaction.guild is None
            or interaction.guild_id is None
        ):
            await interaction.response.send_message(
                "❌ Este comando solo funciona en un servidor.",
                ephemeral=True,
            )
            return

        if not isinstance(
            interaction.user,
            discord.Member,
        ):
            await interaction.response.send_message(
                "❌ No pude identificar tu usuario.",
                ephemeral=True,
            )
            return

        if not can_manage_music(
            interaction.user
        ):
            await interaction.response.send_message(
                "⛔ No tienes permiso para controlar CTX Music.",
                ephemeral=True,
            )
            return

        view = CTXMusicView(
            interaction.guild_id
        )

        await interaction.response.send_message(
            embed=build_player_embed(
                interaction.guild_id
            ),
            view=view,
        )


async def setup(
    bot: commands.Bot,
) -> None:

    await bot.add_cog(
        MusicPanelCommands(
            bot
        )
    )
