"""Professional, persistent and synchronized CTX Music panel."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from music.autoplay_controller import toggle_autoplay
from music.loop_controller import toggle_loop
from music.pause_controller import pause_current_track
from music.permissions import can_manage_music, is_real_music_member
from music.playback_clock import playback_clock_manager
from music.resume_controller import resume_current_track
from music.session import music_session_manager
from music.skip_controller import skip_current_track
from music.state_events import MusicStateEvent, music_state_event_bus
from music.stop_controller import stop_music
from music.volume_controller import get_music_volume, set_music_volume


logger = logging.getLogger(__name__)

PANEL_COLOR = discord.Color.from_rgb(178, 16, 48)
IDLE_COLOR = discord.Color.from_rgb(35, 35, 42)
MAX_QUEUE_PREVIEW = 5
PANEL_STORE = Path("data/music_panels.json")
PANEL_DEBOUNCE_SECONDS = 1.5
PROGRESS_REFRESH_SECONDS = 15.0


def _status_text(guild_id: int) -> tuple[str, str]:
    session = music_session_manager.get_session(guild_id)
    if session.current_track is None:
        return "⏹️", "EN ESPERA"
    if session.state.paused:
        return "⏸️", "PAUSADO"
    return "▶️", "REPRODUCIENDO"


def _on_off(value: bool) -> str:
    return "🟢 ON" if value else "⚫ OFF"


def _safe_http_url(value: object) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    return None


def _track_parts(track) -> tuple[str, str]:
    title = str(getattr(track, "title", "Canción desconocida"))
    if " — " in title:
        song, artist = title.rsplit(" — ", 1)
        return song.strip(), artist.strip()
    return title, "Artista no disponible"


def _queue_preview(guild_id: int) -> str:
    tracks = music_session_manager.get_session(guild_id).queue.get_all()
    if not tracks:
        return "📭 No hay canciones esperando."

    lines = [
        f"`{index:02d}.` **{discord.utils.escape_markdown(track.title)}** "
        f"• `{track.formatted_duration}` • {discord.utils.escape_markdown(track.requester_name)}"
        for index, track in enumerate(tracks[:MAX_QUEUE_PREVIEW], start=1)
    ]
    hidden = len(tracks) - len(lines)
    if hidden > 0:
        lines.append(f"➕ **{hidden}** canción(es) más")
    return "\n".join(lines)


def build_player_embed(
    guild_id: int,
    *,
    notice: str | None = None,
) -> discord.Embed:
    """Build the panel from the authoritative guild session and clock."""

    session = music_session_manager.get_session(guild_id)
    track = session.current_track
    status_icon, status_name = _status_text(guild_id)

    embed = discord.Embed(
        title="CTX MUSIC",
        color=PANEL_COLOR if track else IDLE_COLOR,
    )

    if track is None:
        embed.description = (
            f"### {status_icon} {status_name}\n"
            "El reproductor está listo. Usa `/play` para solicitar música."
        )
    else:
        song, artist = _track_parts(track)
        track_url = _safe_http_url(getattr(track, "url", None))
        safe_song = discord.utils.escape_markdown(song)
        safe_artist = discord.utils.escape_markdown(artist)
        heading = f"[{safe_song}]({track_url})" if track_url else safe_song

        embed.description = (
            f"### {status_icon} {status_name}\n"
            f"## {heading}\n"
            f"**{safe_artist}**\n\n"
            f"{playback_clock_manager.progress_text(guild_id, track.duration)}"
        )

        artwork = _safe_http_url(getattr(track, "thumbnail", None))
        if artwork:
            embed.set_image(url=artwork)

        embed.add_field(
            name="Solicitada por",
            value=f"👤 {discord.utils.escape_markdown(track.requester_name)}",
            inline=True,
        )

    embed.add_field(
        name="Volumen",
        value=f"🔊 `{session.state.volume}%`",
        inline=True,
    )
    embed.add_field(
        name="Cola",
        value=f"📜 `{session.queue.size()}`",
        inline=True,
    )
    embed.add_field(
        name="Modos",
        value=(
            f"🔁 Loop: **{_on_off(session.state.loop_enabled)}**\n"
            f"♾️ Autoplay: **{_on_off(session.state.autoplay_enabled)}**"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"Próximas • {session.queue.size()}",
        value=_queue_preview(guild_id),
        inline=False,
    )

    if notice:
        embed.add_field(
            name="Última acción",
            value=discord.utils.escape_markdown(notice)[:1024],
            inline=False,
        )

    embed.set_footer(
        text="CTX RANK X7 • progreso aproximado • controles administrativos"
    )
    return embed


def build_music_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="CTX MUSIC • Ayuda",
        description=(
            "Todos los miembros reales pueden solicitar canciones. "
            "La reproducción y la cola son compartidas por servidor."
        ),
        color=PANEL_COLOR,
    )
    embed.add_field(
        name="Para todos los miembros",
        value=(
            "`/play <título o URL>` — solicita una canción\n"
            "`/queue` — consulta la cola y posiciones\n"
            "`/player` — abre o localiza el panel principal\n"
            "`/musichelp` — muestra esta ayuda"
        ),
        inline=False,
    )
    embed.add_field(
        name="Controles administrativos",
        value=(
            "`/pause`, `/resume`, `/skip`, `/stop`, `/volume`, "
            "`/loop` y `/autoplay`. Los mismos permisos se aplican a los botones."
        ),
        inline=False,
    )
    embed.add_field(
        name="Prefijo tradicional",
        value=(
            "Usa las variantes `!ctx_play`, `!ctx_queue`, `!ctx_player` y "
            "los demás comandos `!ctx_...`."
        ),
        inline=False,
    )
    return embed


@dataclass(frozen=True)
class PanelReference:
    guild_id: int
    channel_id: int
    message_id: int


class MusicPanelRegistry:
    """Own one editable player message per guild and restore it after restart."""

    def __init__(self) -> None:
        self.bot: commands.Bot | None = None
        self.references: dict[int, PanelReference] = {}
        self._messages: dict[int, discord.Message] = {}
        self._pending_updates: dict[int, asyncio.Task] = {}
        self._last_edits: dict[int, float] = {}
        self._progress_task: asyncio.Task | None = None
        self._restored = False
        self._load()

    def bind(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _load(self) -> None:
        if not PANEL_STORE.exists():
            return
        try:
            payload = json.loads(PANEL_STORE.read_text(encoding="utf-8"))
            for raw_guild_id, raw in payload.items():
                guild_id = int(raw_guild_id)
                self.references[guild_id] = PanelReference(
                    guild_id=guild_id,
                    channel_id=int(raw["channel_id"]),
                    message_id=int(raw["message_id"]),
                )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            logger.warning("Ignoring invalid CTX Music panel store", exc_info=True)

    def _save(self) -> None:
        payload = {
            str(guild_id): {
                "channel_id": ref.channel_id,
                "message_id": ref.message_id,
            }
            for guild_id, ref in self.references.items()
        }
        PANEL_STORE.parent.mkdir(parents=True, exist_ok=True)
        temporary = PANEL_STORE.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(PANEL_STORE)

    async def _fetch_message(self, ref: PanelReference) -> discord.Message | None:
        if self.bot is None:
            return None
        channel = self.bot.get_channel(ref.channel_id)
        if channel is None:
            with suppress(discord.HTTPException, discord.Forbidden):
                channel = await self.bot.fetch_channel(ref.channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            return None
        try:
            return await channel.fetch_message(ref.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def restore(self) -> None:
        if self.bot is None or self._restored:
            return
        self._restored = True
        changed = False
        for guild_id, ref in tuple(self.references.items()):
            message = await self._fetch_message(ref)
            if message is None:
                self.references.pop(guild_id, None)
                changed = True
                continue
            view = CTXMusicView(guild_id)
            self._messages[guild_id] = message
            self.bot.add_view(view, message_id=ref.message_id)
            with suppress(discord.HTTPException, discord.Forbidden):
                await message.edit(
                    embed=build_player_embed(guild_id),
                    view=view,
                )
        if changed:
            self._save()
        self.start_progress_updates()

    async def get_or_create(
        self,
        guild_id: int,
        channel: discord.abc.Messageable,
    ) -> tuple[discord.Message, bool]:
        ref = self.references.get(guild_id)
        if ref is not None:
            message = self._messages.get(guild_id) or await self._fetch_message(ref)
            if message is not None:
                self._messages[guild_id] = message
                await message.edit(
                    embed=build_player_embed(guild_id),
                    view=CTXMusicView(guild_id),
                )
                return message, False
            self.references.pop(guild_id, None)

        message = await channel.send(
            embed=build_player_embed(guild_id),
            view=CTXMusicView(guild_id),
        )
        self.references[guild_id] = PanelReference(
            guild_id=guild_id,
            channel_id=message.channel.id,
            message_id=message.id,
        )
        self._messages[guild_id] = message
        self._save()
        return message, True

    async def refresh(self, guild_id: int, notice: str | None = None) -> bool:
        ref = self.references.get(guild_id)
        if ref is None:
            return False
        message = self._messages.get(guild_id) or await self._fetch_message(ref)
        if message is None:
            self.references.pop(guild_id, None)
            self._messages.pop(guild_id, None)
            self._save()
            return False
        try:
            await message.edit(
                embed=build_player_embed(guild_id, notice=notice),
                view=CTXMusicView(guild_id),
            )
            self._last_edits[guild_id] = time.monotonic()
            return True
        except (discord.NotFound, discord.Forbidden):
            self.references.pop(guild_id, None)
            self._messages.pop(guild_id, None)
            self._save()
            return False
        except discord.HTTPException:
            logger.warning("Could not refresh music panel for guild %s", guild_id)
            return False

    def on_state_event(self, event: MusicStateEvent) -> None:
        if event.guild_id not in self.references:
            return
        existing = self._pending_updates.get(event.guild_id)
        if existing is not None and not existing.done():
            return

        async def delayed_refresh() -> None:
            elapsed = time.monotonic() - self._last_edits.get(event.guild_id, 0.0)
            await asyncio.sleep(max(0.0, PANEL_DEBOUNCE_SECONDS - elapsed))
            await self.refresh(event.guild_id, notice=event.notice)

        task = asyncio.create_task(delayed_refresh())
        self._pending_updates[event.guild_id] = task

        def remove_finished(completed: asyncio.Task) -> None:
            if self._pending_updates.get(event.guild_id) is completed:
                self._pending_updates.pop(event.guild_id, None)

        task.add_done_callback(remove_finished)

    def start_progress_updates(self) -> None:
        if self._progress_task is not None and not self._progress_task.done():
            return

        async def progress_loop() -> None:
            while True:
                await asyncio.sleep(PROGRESS_REFRESH_SECONDS)
                for guild_id in tuple(self.references):
                    clock = playback_clock_manager.get_state(guild_id)
                    if clock.running:
                        await self.refresh(guild_id)

        self._progress_task = asyncio.create_task(progress_loop())

    def close(self) -> None:
        for task in self._pending_updates.values():
            task.cancel()
        self._pending_updates.clear()
        if self._progress_task is not None:
            self._progress_task.cancel()
            self._progress_task = None


panel_registry = MusicPanelRegistry()
_interaction_locks: dict[int, asyncio.Lock] = {}


def _interaction_lock(guild_id: int) -> asyncio.Lock:
    return _interaction_locks.setdefault(guild_id, asyncio.Lock())


class CTXMusicView(discord.ui.View):
    def __init__(self, guild_id: int) -> None:
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self._sync_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id != self.guild_id:
            await interaction.response.send_message(
                "❌ Este panel pertenece a otro servidor.", ephemeral=True
            )
            return False
        if not isinstance(interaction.user, discord.Member) or not is_real_music_member(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ No pude validar tu membresía.", ephemeral=True
            )
            return False
        return True

    async def _require_control(self, interaction: discord.Interaction) -> bool:
        assert isinstance(interaction.user, discord.Member)
        if can_manage_music(interaction.user):
            return True
        await interaction.response.send_message(
            "⛔ No tienes permiso para controlar CTX Music.", ephemeral=True
        )
        return False

    def _sync_buttons(self) -> None:
        session = music_session_manager.get_session(self.guild_id)
        has_track = session.current_track is not None
        self.pause_resume_button.disabled = not has_track
        self.skip_button.disabled = not has_track
        self.stop_button.disabled = not has_track

        if session.state.paused:
            self.pause_resume_button.label = "Reanudar"
            self.pause_resume_button.emoji = "▶️"
            self.pause_resume_button.style = discord.ButtonStyle.success
        else:
            self.pause_resume_button.label = "Pausar"
            self.pause_resume_button.emoji = "⏸️"
            self.pause_resume_button.style = discord.ButtonStyle.secondary

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

    async def _finish_action(
        self,
        interaction: discord.Interaction,
        notice: str,
    ) -> None:
        updated = await panel_registry.refresh(self.guild_id, notice=notice)
        if not updated and interaction.message is not None:
            self._sync_buttons()
            await interaction.message.edit(
                embed=build_player_embed(self.guild_id, notice=notice),
                view=self,
            )

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        logger.error("Music panel interaction failed", exc_info=error)
        message = "❌ CTX Music no pudo completar esa acción."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(
        label="Pausar", emoji="⏸️", style=discord.ButtonStyle.secondary,
        row=0, custom_id="ctx_music:pause_resume",
    )
    async def pause_resume_button(self, interaction, button) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            session = music_session_manager.get_session(self.guild_id)
            result = (
                await resume_current_track(self.guild_id)
                if session.state.paused
                else await pause_current_track(self.guild_id)
            )
        await self._finish_action(interaction, result.message)

    @discord.ui.button(
        label="Saltar", emoji="⏭️", style=discord.ButtonStyle.primary,
        row=0, custom_id="ctx_music:skip",
    )
    async def skip_button(self, interaction, button) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await skip_current_track(self.guild_id)
        await self._finish_action(interaction, result.message)

    @discord.ui.button(
        label="Detener", emoji="⏹️", style=discord.ButtonStyle.danger,
        row=0, custom_id="ctx_music:stop",
    )
    async def stop_button(self, interaction, button) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await stop_music(self.guild_id, clear_queue=True)
        await self._finish_action(interaction, result.message)

    @discord.ui.button(
        label="Loop", emoji="🔁", style=discord.ButtonStyle.secondary,
        row=1, custom_id="ctx_music:loop",
    )
    async def loop_button(self, interaction, button) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await toggle_loop(self.guild_id)
        await self._finish_action(interaction, result.message)

    @discord.ui.button(
        label="Autoplay", emoji="♾️", style=discord.ButtonStyle.secondary,
        row=1, custom_id="ctx_music:autoplay",
    )
    async def autoplay_button(self, interaction, button) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await toggle_autoplay(self.guild_id)
        await self._finish_action(interaction, result.message)

    @discord.ui.button(
        label="-10", emoji="🔉", style=discord.ButtonStyle.secondary,
        row=1, custom_id="ctx_music:volume_down",
    )
    async def volume_down_button(self, interaction, button) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await set_music_volume(
                self.guild_id, max(0, get_music_volume(self.guild_id) - 10)
            )
        await self._finish_action(interaction, result.message)

    @discord.ui.button(
        label="+10", emoji="🔊", style=discord.ButtonStyle.secondary,
        row=1, custom_id="ctx_music:volume_up",
    )
    async def volume_up_button(self, interaction, button) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await set_music_volume(
                self.guild_id, min(100, get_music_volume(self.guild_id) + 10)
            )
        await self._finish_action(interaction, result.message)

    @discord.ui.button(
        label="Cola", emoji="📜", style=discord.ButtonStyle.secondary,
        row=2, custom_id="ctx_music:queue",
    )
    async def queue_button(self, interaction, button) -> None:
        tracks = music_session_manager.get_session(self.guild_id).queue.get_all()
        text = _queue_preview(self.guild_id)
        if len(tracks) > MAX_QUEUE_PREVIEW:
            text += f"\n\nTotal pendiente: **{len(tracks)}**"
        await interaction.response.send_message(
            f"📜 **CTX MUSIC — COLA**\n\n{text}", ephemeral=True
        )

    @discord.ui.button(
        label="Actualizar", emoji="🔄", style=discord.ButtonStyle.secondary,
        row=2, custom_id="ctx_music:refresh",
    )
    async def refresh_button(self, interaction, button) -> None:
        await interaction.response.defer()
        await self._finish_action(interaction, "Panel actualizado.")


class MusicPanelCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        panel_registry.bind(bot)

    async def cog_load(self) -> None:
        music_state_event_bus.subscribe(panel_registry.on_state_event)
        if self.bot.is_ready():
            await panel_registry.restore()

    def cog_unload(self) -> None:
        music_state_event_bus.unsubscribe(panel_registry.on_state_event)
        panel_registry.close()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await panel_registry.restore()

    @commands.command(name="ctx_player", aliases=["ctx_panel"])
    @commands.guild_only()
    async def ctx_player(self, ctx: commands.Context) -> None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return
        if not is_real_music_member(ctx.author):
            await ctx.send("⛔ Los bots no pueden abrir CTX Music.")
            return
        message, created = await panel_registry.get_or_create(ctx.guild.id, ctx.channel)
        if not created:
            await ctx.send(f"🎵 El panel principal ya está aquí: {message.jump_url}")

    @commands.command(name="ctx_musichelp", aliases=["ctx_music"])
    @commands.guild_only()
    async def ctx_musichelp(self, ctx: commands.Context) -> None:
        if isinstance(ctx.author, discord.Member) and is_real_music_member(ctx.author):
            await ctx.send(embed=build_music_help_embed())

    @app_commands.command(
        name="player",
        description="Abre o actualiza el panel principal de CTX Music.",
    )
    async def slash_player(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None or interaction.channel is None:
            await interaction.response.send_message(
                "❌ Este comando solo funciona en un servidor.", ephemeral=True
            )
            return
        if not isinstance(interaction.user, discord.Member) or not is_real_music_member(
            interaction.user
        ):
            await interaction.response.send_message(
                "⛔ Los bots no pueden abrir CTX Music.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        message, created = await panel_registry.get_or_create(
            interaction.guild_id, interaction.channel
        )
        verb = "creado" if created else "actualizado"
        await interaction.followup.send(
            f"🎵 Panel principal {verb}: {message.jump_url}", ephemeral=True
        )

    @app_commands.command(
        name="musichelp",
        description="Muestra los comandos, permisos y uso de CTX Music.",
    )
    async def slash_musichelp(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not is_real_music_member(
            interaction.user
        ):
            await interaction.response.send_message(
                "⛔ Este comando requiere un miembro real.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=build_music_help_embed(), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicPanelCommands(bot))
