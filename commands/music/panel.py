"""Premium, persistent and synchronized CTX Music Components V2 panel."""

from __future__ import annotations

import asyncio
import json
import logging
import os
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
IDLE_COLOR = discord.Color.from_rgb(63, 65, 72)
MAX_QUEUE_PREVIEW = 8
PANEL_STORE = Path("data/music_panels.json")


def _env_seconds(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


PANEL_DEBOUNCE_SECONDS = _env_seconds(
    "CTX_MUSIC_PANEL_DEBOUNCE_SECONDS", 1.5, 0.5, 5.0
)
PANEL_MIN_EDIT_INTERVAL_SECONDS = _env_seconds(
    "CTX_MUSIC_PANEL_MIN_EDIT_INTERVAL_SECONDS", 2.5, 1.0, 10.0
)
PROGRESS_REFRESH_SECONDS = _env_seconds(
    "CTX_MUSIC_PANEL_REFRESH_SECONDS", 15.0, 10.0, 60.0
)


def _truncate(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 1)].rstrip()}…"


def _status_text(guild_id: int) -> tuple[str, str]:
    session = music_session_manager.get_session(guild_id)
    if session.current_track is not None and not session.state.connected:
        return "OFFLINE", "SIN CONEXIÓN DE VOZ"
    if session.current_track is None:
        return "READY", "EN ESPERA"
    if session.state.paused:
        return "PAUSED", "REPRODUCCIÓN PAUSADA"
    return "LIVE", "REPRODUCIENDO"


def _on_off(value: bool) -> str:
    return "ON" if value else "OFF"


def _safe_http_url(value: object) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    return None


def _track_parts(track) -> tuple[str, str]:
    title = _truncate(getattr(track, "title", "Canción desconocida"), 120)
    for separator in (" — ", " – "):
        if separator in title:
            song, artist = title.rsplit(separator, 1)
            return _truncate(song, 80), _truncate(artist, 60)
    return _truncate(title, 80), "Artista no disponible"


def _queue_preview(guild_id: int) -> str:
    tracks = music_session_manager.get_session(guild_id).queue.get_all()
    if not tracks:
        return "No hay canciones esperando."

    lines = [
        f"`{index:02d}`  **{discord.utils.escape_markdown(_truncate(track.title, 75))}** "
        f"· `{track.formatted_duration}` · {discord.utils.escape_markdown(_truncate(track.requester_name, 32))}"
        for index, track in enumerate(tracks[:MAX_QUEUE_PREVIEW], start=1)
    ]
    hidden = len(tracks) - len(lines)
    if hidden > 0:
        lines.append(f"…y **{hidden}** canción(es) más")
    return "\n".join(lines)


@dataclass(frozen=True)
class PlayerPresentation:
    accent_color: discord.Color
    header: str
    media_url: str | None
    media_description: str | None
    track_block: str
    metadata_block: str
    modes_block: str
    next_block: str | None
    notice_block: str | None
    has_track: bool
    paused: bool


def build_player_presentation(
    guild_id: int,
    *,
    notice: str | None = None,
) -> PlayerPresentation:
    """Create a compact, mobile-safe representation from authoritative state."""

    session = music_session_manager.get_session(guild_id)
    track = session.current_track
    status_badge, status_name = _status_text(guild_id)
    header = (
        f"### CTX MUSIC  ·  {status_badge}\n"
        f"**ZAREK AUDIO SYSTEM**  ·  {status_name}"
    )

    media_url: str | None = None
    media_description: str | None = None
    if track is None:
        track_block = (
            "## EN ESPERA\n"
            "Solicita una canción con `/play` y este mismo panel se actualizará."
        )
    else:
        song, artist = _track_parts(track)
        safe_song = discord.utils.escape_markdown(song)
        safe_artist = discord.utils.escape_markdown(artist)
        track_url = _safe_http_url(getattr(track, "url", None))
        heading = f"[{safe_song}]({track_url})" if track_url else safe_song
        track_block = (
            f"## {heading}\n"
            f"**{safe_artist}**\n\n"
            f"{playback_clock_manager.progress_text(guild_id, track.duration)}"
        )
        media_url = _safe_http_url(getattr(track, "thumbnail", None))
        media_description = f"Portada de {_truncate(song, 180)}" if media_url else None

    requester = (
        discord.utils.escape_markdown(_truncate(track.requester_name, 40))
        if track is not None
        else "—"
    )
    metadata_block = (
        f"**SOLICITADA POR**  {requester}\n"
        f"**VOLUMEN**  `{session.state.volume:03d}%`   ·   "
        f"**COLA**  `{session.queue.size():02d}`"
    )
    modes_block = (
        f"**LOOP**  `{_on_off(session.state.loop_enabled)}`   ·   "
        f"**AUTOPLAY**  `{_on_off(session.state.autoplay_enabled)}`"
    )

    next_track = session.queue.peek()
    next_block = None
    if next_track is not None:
        next_block = (
            "**SIGUIENTE**\n"
            f"{discord.utils.escape_markdown(_truncate(next_track.title, 90))} "
            f"· `{next_track.formatted_duration}`"
        )
    elif track is not None and session.state.autoplay_enabled:
        next_block = "**SIGUIENTE**\nAutoplay elegirá una canción relacionada."

    notice_block = None
    if notice:
        notice_block = f"-# {_truncate(discord.utils.escape_markdown(notice), 180)}"

    return PlayerPresentation(
        accent_color=PANEL_COLOR if track is not None else IDLE_COLOR,
        header=header,
        media_url=media_url,
        media_description=media_description,
        track_block=track_block,
        metadata_block=metadata_block,
        modes_block=modes_block,
        next_block=next_block,
        notice_block=notice_block,
        has_track=track is not None,
        paused=session.state.paused,
    )


def build_player_embed(
    guild_id: int,
    *,
    notice: str | None = None,
) -> discord.Embed:
    """Compatibility preview for callers that cannot render Components V2."""

    presentation = build_player_presentation(guild_id, notice=notice)
    embed = discord.Embed(
        title="CTX MUSIC · ZAREK AUDIO SYSTEM",
        description=f"{presentation.track_block}\n\n{presentation.metadata_block}",
        color=presentation.accent_color,
    )
    embed.add_field(name="MODOS", value=presentation.modes_block, inline=False)
    if presentation.next_block:
        embed.add_field(name="A CONTINUACIÓN", value=presentation.next_block, inline=False)
    if presentation.media_url:
        embed.set_image(url=presentation.media_url)
    embed.set_footer(text="Vista de compatibilidad · el panel principal usa Components V2")
    return embed


def build_music_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="CTX MUSIC · Ayuda",
        description=(
            "La reproducción y la cola son compartidas por servidor. "
            "Todos los miembros reales pueden solicitar canciones."
        ),
        color=PANEL_COLOR,
    )
    embed.add_field(
        name="SOLICITAR Y CONSULTAR",
        value=(
            "`/play <título o URL>` · solicitar música\n"
            "`/queue` · consultar posiciones\n"
            "`/player` · abrir o localizar el panel\n"
            "`/musichelp` · mostrar esta guía"
        ),
        inline=False,
    )
    embed.add_field(
        name="CONTROLES RESERVADOS",
        value=(
            "`/pause`, `/resume`, `/skip`, `/stop`, `/volume`, `/loop` y "
            "`/autoplay`. La misma jerarquía se aplica a los botones."
        ),
        inline=False,
    )
    embed.add_field(
        name="COMANDOS TRADICIONALES",
        value="También están disponibles las variantes `!ctx_...`.",
        inline=False,
    )
    return embed


@dataclass(frozen=True)
class PanelReference:
    guild_id: int
    channel_id: int
    message_id: int


async def _edit_panel_message(
    message: discord.Message,
    guild_id: int,
    *,
    notice: str | None = None,
    view: CTXMusicView | None = None,
) -> discord.Message:
    view = view or CTXMusicView(guild_id, notice=notice)
    flags = getattr(message, "flags", None)
    already_v2 = bool(getattr(flags, "components_v2", False))
    if already_v2:
        return await message.edit(view=view)
    return await message.edit(
        content=None,
        embed=None,
        attachments=[],
        view=view,
    )


class MusicPanelRegistry:
    """Own exactly one editable player message per guild."""

    def __init__(self) -> None:
        self.bot: commands.Bot | None = None
        self.references: dict[int, PanelReference] = {}
        self._messages: dict[int, discord.Message] = {}
        self._pending_updates: dict[int, asyncio.Task] = {}
        self._pending_notices: dict[int, str | None] = {}
        self._pending_requested_at: dict[int, float] = {}
        self._last_edits: dict[int, float] = {}
        self._panel_locks: dict[int, asyncio.Lock] = {}
        self._progress_task: asyncio.Task | None = None
        self._restored = False
        self._load()

    def bind(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _panel_lock(self, guild_id: int) -> asyncio.Lock:
        return self._panel_locks.setdefault(guild_id, asyncio.Lock())

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
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
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
            async with self._panel_lock(guild_id):
                message = await self._fetch_message(ref)
                if message is None:
                    self.references.pop(guild_id, None)
                    self._messages.pop(guild_id, None)
                    changed = True
                    continue
                view = CTXMusicView(guild_id)
                self.bot.add_view(view, message_id=ref.message_id)
                try:
                    message = await _edit_panel_message(
                        message, guild_id, view=view
                    )
                except (discord.HTTPException, discord.Forbidden):
                    logger.warning("Could not restore CTX Music panel for guild %s", guild_id)
                    continue
                self._messages[guild_id] = message
                self._last_edits[guild_id] = time.monotonic()
        if changed:
            self._save()
        self.start_progress_updates()

    async def get_or_create(
        self,
        guild_id: int,
        channel: discord.abc.Messageable,
        *,
        notice: str | None = None,
    ) -> tuple[discord.Message, bool]:
        async with self._panel_lock(guild_id):
            ref = self.references.get(guild_id)
            if ref is not None:
                message = self._messages.get(guild_id) or await self._fetch_message(ref)
                if message is not None:
                    message = await _edit_panel_message(
                        message, guild_id, notice=notice
                    )
                    self._messages[guild_id] = message
                    self._last_edits[guild_id] = time.monotonic()
                    return message, False
                self.references.pop(guild_id, None)
                self._messages.pop(guild_id, None)

            view = CTXMusicView(guild_id, notice=notice)
            message = await channel.send(view=view)
            self.references[guild_id] = PanelReference(
                guild_id=guild_id,
                channel_id=message.channel.id,
                message_id=message.id,
            )
            self._messages[guild_id] = message
            self._last_edits[guild_id] = time.monotonic()
            self._save()
            return message, True

    async def refresh(self, guild_id: int, notice: str | None = None) -> bool:
        async with self._panel_lock(guild_id):
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
                message = await _edit_panel_message(message, guild_id, notice=notice)
                self._messages[guild_id] = message
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

    async def _run_pending_updates(self, guild_id: int) -> bool:
        """Render the newest state after event bursts without exceeding edit pace."""

        updated = False
        while guild_id in self._pending_requested_at:
            requested_at = self._pending_requested_at[guild_id]
            edit_due_at = max(
                requested_at + PANEL_DEBOUNCE_SECONDS,
                self._last_edits.get(guild_id, 0.0)
                + PANEL_MIN_EDIT_INTERVAL_SECONDS,
            )
            delay = edit_due_at - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)

            # A newer request arrived while sleeping; restart the debounce window.
            if self._pending_requested_at.get(guild_id) != requested_at:
                continue

            notice = self._pending_notices.pop(guild_id, None)
            self._pending_requested_at.pop(guild_id, None)
            updated = await self.refresh(guild_id, notice=notice) or updated

        return updated

    def _start_pending_update(self, guild_id: int) -> asyncio.Task:
        existing = self._pending_updates.get(guild_id)
        if existing is not None and not existing.done():
            return existing

        task = asyncio.create_task(self._run_pending_updates(guild_id))
        self._pending_updates[guild_id] = task

        def remove_finished(completed: asyncio.Task) -> None:
            if self._pending_updates.get(guild_id) is completed:
                self._pending_updates.pop(guild_id, None)
            if not completed.cancelled():
                error = completed.exception()
                if error is not None:
                    logger.error(
                        "Deferred music panel refresh failed for guild %s",
                        guild_id,
                        exc_info=error,
                    )
            # Do not lose an event that arrived as the previous task completed.
            if guild_id in self._pending_requested_at:
                self._start_pending_update(guild_id)

        task.add_done_callback(remove_finished)
        return task

    def schedule_refresh(
        self, guild_id: int, *, notice: str | None = None
    ) -> asyncio.Task | None:
        """Coalesce a refresh request into the single per-guild update worker."""

        if guild_id not in self.references:
            return None
        self._pending_notices[guild_id] = notice
        self._pending_requested_at[guild_id] = time.monotonic()
        return self._start_pending_update(guild_id)

    async def refresh_coalesced(
        self, guild_id: int, *, notice: str | None = None
    ) -> bool:
        task = self.schedule_refresh(guild_id, notice=notice)
        if task is None:
            return False
        return bool(await asyncio.shield(task))

    def on_state_event(self, event: MusicStateEvent) -> None:
        self.schedule_refresh(event.guild_id, notice=event.notice)

    def start_progress_updates(self) -> None:
        if self._progress_task is not None and not self._progress_task.done():
            return

        async def progress_loop() -> None:
            while True:
                await asyncio.sleep(PROGRESS_REFRESH_SECONDS)
                active_guilds = [
                    guild_id
                    for guild_id in tuple(self.references)
                    if playback_clock_manager.get_state(guild_id).running
                ]
                for guild_id in active_guilds:
                    self.schedule_refresh(guild_id)

        self._progress_task = asyncio.create_task(progress_loop())

    def close(self) -> None:
        for task in self._pending_updates.values():
            task.cancel()
        self._pending_updates.clear()
        self._pending_notices.clear()
        self._pending_requested_at.clear()
        if self._progress_task is not None:
            self._progress_task.cancel()
            self._progress_task = None
        self._restored = False


panel_registry = MusicPanelRegistry()
_interaction_locks: dict[int, asyncio.Lock] = {}


def _interaction_lock(guild_id: int) -> asyncio.Lock:
    return _interaction_locks.setdefault(guild_id, asyncio.Lock())


class CTXMusicView(discord.ui.LayoutView):
    """Native Components V2 player with persistent, state-aware controls."""

    def __init__(self, guild_id: int, *, notice: str | None = None) -> None:
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.presentation = build_player_presentation(guild_id, notice=notice)
        self._build_controls()
        self._build_layout()

    def _new_button(
        self,
        *,
        label: str,
        custom_id: str,
        style: discord.ButtonStyle,
        callback,
        emoji: str | None = None,
        disabled: bool = False,
    ) -> discord.ui.Button:
        button = discord.ui.Button(
            label=label,
            custom_id=custom_id,
            style=style,
            emoji=emoji,
            disabled=disabled,
        )
        button.callback = callback
        return button

    def _build_controls(self) -> None:
        session = music_session_manager.get_session(self.guild_id)
        has_track = self.presentation.has_track
        has_music = has_track or session.queue.size() > 0

        self.pause_resume_button = self._new_button(
            label="Reanudar" if self.presentation.paused else "Pausar",
            emoji="▶️" if self.presentation.paused else "⏸️",
            custom_id="ctx_music:pause_resume",
            style=(
                discord.ButtonStyle.success
                if self.presentation.paused
                else discord.ButtonStyle.secondary
            ),
            callback=self._pause_resume,
            disabled=not has_track,
        )
        self.skip_button = self._new_button(
            label="Siguiente",
            emoji="⏭️",
            custom_id="ctx_music:skip",
            style=discord.ButtonStyle.primary,
            callback=self._skip,
            disabled=not has_track,
        )
        self.stop_button = self._new_button(
            label="Detener",
            emoji="⏹️",
            custom_id="ctx_music:stop",
            style=discord.ButtonStyle.danger,
            callback=self._stop,
            disabled=not has_music,
        )
        self.loop_button = self._new_button(
            label=f"Loop · {_on_off(session.state.loop_enabled)}",
            emoji="🔁",
            custom_id="ctx_music:loop",
            style=(
                discord.ButtonStyle.success
                if session.state.loop_enabled
                else discord.ButtonStyle.secondary
            ),
            callback=self._loop,
            disabled=not has_track,
        )
        self.autoplay_button = self._new_button(
            label=f"Auto · {_on_off(session.state.autoplay_enabled)}",
            custom_id="ctx_music:autoplay",
            style=(
                discord.ButtonStyle.success
                if session.state.autoplay_enabled
                else discord.ButtonStyle.secondary
            ),
            callback=self._autoplay,
        )
        self.volume_down_button = self._new_button(
            label="−10",
            emoji="🔉",
            custom_id="ctx_music:volume_down",
            style=discord.ButtonStyle.secondary,
            callback=self._volume_down,
            disabled=not has_track,
        )
        self.volume_up_button = self._new_button(
            label="+10",
            emoji="🔊",
            custom_id="ctx_music:volume_up",
            style=discord.ButtonStyle.secondary,
            callback=self._volume_up,
            disabled=not has_track,
        )
        self.queue_button = self._new_button(
            label="Ver cola",
            custom_id="ctx_music:queue",
            style=discord.ButtonStyle.secondary,
            callback=self._queue,
        )
        self.refresh_button = self._new_button(
            label="Actualizar",
            custom_id="ctx_music:refresh",
            style=discord.ButtonStyle.secondary,
            callback=self._on_refresh_button,
        )

    def _build_layout(self) -> None:
        p = self.presentation
        children: list[discord.ui.Item] = [discord.ui.TextDisplay(p.header)]
        if p.media_url:
            children.append(
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(
                        p.media_url,
                        description=p.media_description,
                    )
                )
            )
        children.extend(
            [
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(p.track_block),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(p.metadata_block),
                discord.ui.TextDisplay(p.modes_block),
            ]
        )
        if p.next_block:
            children.append(discord.ui.TextDisplay(p.next_block))
        if p.notice_block:
            children.append(discord.ui.TextDisplay(p.notice_block))
        children.extend(
            [
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(
                    self.pause_resume_button,
                    self.skip_button,
                    self.stop_button,
                ),
                discord.ui.ActionRow(
                    self.loop_button,
                    self.autoplay_button,
                    self.volume_down_button,
                    self.volume_up_button,
                ),
                discord.ui.ActionRow(self.queue_button, self.refresh_button),
                discord.ui.TextDisplay(
                    "-# CTX RANK X7 · progreso aproximado · controles protegidos"
                ),
            ]
        )
        self.add_item(
            discord.ui.Container(*children, accent_color=p.accent_color)
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id != self.guild_id:
            await interaction.response.send_message(
                "Este panel pertenece a otro servidor.", ephemeral=True
            )
            return False
        if not isinstance(interaction.user, discord.Member) or not is_real_music_member(
            interaction.user
        ):
            await interaction.response.send_message(
                "No pude validar tu membresía.", ephemeral=True
            )
            return False
        return True

    async def _require_control(self, interaction: discord.Interaction) -> bool:
        assert isinstance(interaction.user, discord.Member)
        if can_manage_music(interaction.user):
            return True
        await interaction.response.send_message(
            "No tienes permiso para controlar CTX Music.", ephemeral=True
        )
        return False

    async def _finish_action(
        self, interaction: discord.Interaction, notice: str
    ) -> None:
        updated = await panel_registry.refresh_coalesced(
            self.guild_id, notice=notice
        )
        if not updated and interaction.message is not None:
            await _edit_panel_message(
                interaction.message, self.guild_id, notice=notice
            )

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        logger.error("Music panel interaction failed", exc_info=error)
        message = "CTX Music no pudo completar esa acción."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def _pause_resume(self, interaction: discord.Interaction) -> None:
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

    async def _skip(self, interaction: discord.Interaction) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await skip_current_track(self.guild_id)
        await self._finish_action(interaction, result.message)

    async def _stop(self, interaction: discord.Interaction) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await stop_music(self.guild_id, clear_queue=True)
        await self._finish_action(interaction, result.message)

    async def _loop(self, interaction: discord.Interaction) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await toggle_loop(self.guild_id)
        await self._finish_action(interaction, result.message)

    async def _autoplay(self, interaction: discord.Interaction) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await toggle_autoplay(self.guild_id)
        await self._finish_action(interaction, result.message)

    async def _volume_down(self, interaction: discord.Interaction) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await set_music_volume(
                self.guild_id, max(0, get_music_volume(self.guild_id) - 10)
            )
        await self._finish_action(interaction, result.message)

    async def _volume_up(self, interaction: discord.Interaction) -> None:
        if not await self._require_control(interaction):
            return
        await interaction.response.defer()
        async with _interaction_lock(self.guild_id):
            result = await set_music_volume(
                self.guild_id, min(100, get_music_volume(self.guild_id) + 10)
            )
        await self._finish_action(interaction, result.message)

    async def _queue(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"**CTX MUSIC · COLA**\n\n{_queue_preview(self.guild_id)}",
            ephemeral=True,
        )

    async def _on_refresh_button(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await self._finish_action(interaction, "Panel sincronizado.")


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
            await ctx.send("Los bots no pueden abrir CTX Music.")
            return
        message, created = await panel_registry.get_or_create(ctx.guild.id, ctx.channel)
        if not created:
            await ctx.send(f"Panel principal: {message.jump_url}", delete_after=12)

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
                "Este comando solo funciona en un servidor.", ephemeral=True
            )
            return
        if not isinstance(interaction.user, discord.Member) or not is_real_music_member(
            interaction.user
        ):
            await interaction.response.send_message(
                "Los bots no pueden abrir CTX Music.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        message, created = await panel_registry.get_or_create(
            interaction.guild_id, interaction.channel
        )
        verb = "creado" if created else "sincronizado"
        await interaction.followup.send(
            f"Panel principal {verb}: {message.jump_url}", ephemeral=True
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
                "Este comando requiere un miembro real.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=build_music_help_embed(), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicPanelCommands(bot))


def get_music_panel_summary() -> dict:
    return {
        "components_v2": True,
        "persistent": True,
        "one_panel_per_guild": True,
        "state_driven_controls": True,
        "debounce_seconds": PANEL_DEBOUNCE_SECONDS,
        "min_edit_interval_seconds": PANEL_MIN_EDIT_INTERVAL_SECONDS,
        "progress_refresh_seconds": PROGRESS_REFRESH_SECONDS,
    }
