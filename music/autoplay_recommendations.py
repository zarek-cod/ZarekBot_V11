"""
CTX V11
AUTOPLAY REAL / RECOMENDACIONES AUTOMÁTICAS - V2

Mejoras de estabilidad:
- usa la configuración central de yt-dlp
- soporta cookies opcionales del navegador
- guarda un pequeño pool de candidatos por servidor
- reduce búsquedas repetidas a YouTube
- corta los reintentos cuando YouTube activa anti-bot
- evita imprimir 5 errores iguales seguidos
- LOOP y cola manual siguen teniendo prioridad
"""

from __future__ import annotations

import asyncio
import re
import time
import unicodedata
from collections import deque

import yt_dlp

from music.async_scheduler import (
    is_async_scheduler_initialized,
    schedule_coroutine,
)
from music.auto_playback import _start_prepared_track_unlocked
from music.operation_lock import get_guild_operation_lock
from music.playback_events import (
    PlaybackEvent,
    PlaybackEventType,
    playback_event_bus,
)
from music.resolver import resolver_registry
from music.search import create_search_request
from music.session import music_session_manager
from music.track import Track
from music.ytdlp_config import (
    build_ytdlp_options,
    get_ytdlp_browser,
    is_youtube_antibot_error,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

SEARCH_RESULTS = 16
MAX_SEARCH_QUERIES_PER_REFILL = 2
MAX_RESOLVE_ATTEMPTS = 4
RECENT_HISTORY_SIZE = 16
CANDIDATE_POOL_SIZE = 24
MIN_DURATION = 60
MAX_DURATION = 900
ANTI_BOT_COOLDOWN_SECONDS = 300


# ============================================================
# ESTADO
# ============================================================

_registered = False
_finished_received = 0
_recommendation_attempts = 0
_recommendations_found = 0
_tracks_started = 0
_failures = 0
_skipped_autoplay_off = 0
_skipped_queue_not_empty = 0
_skipped_loop = 0
_skipped_current_track = 0
_pool_refills = 0
_pool_hits = 0
_anti_bot_blocks = 0

_recent_titles: dict[int, deque[str]] = {}
_recent_urls: dict[int, deque[str]] = {}
_candidate_pools: dict[int, deque[dict]] = {}
_guild_locks: dict[int, asyncio.Lock] = {}
_pending_tasks: dict[int, object] = {}
_guild_generations: dict[int, int] = {}

_youtube_blocked_until = 0.0
_youtube_block_notice_shown = False


# ============================================================
# LOCKS
# ============================================================

def _get_guild_lock(guild_id: int) -> asyncio.Lock:
    lock = _guild_locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        _guild_locks[guild_id] = lock
    return lock


def _current_generation(guild_id: int) -> int:
    return _guild_generations.get(guild_id, 0)


def cancel_pending_autoplay(guild_id: int) -> bool:
    """Invalidate a delayed recommendation without cancelling audio mid-start."""

    _guild_generations[guild_id] = _current_generation(guild_id) + 1
    task = _pending_tasks.get(guild_id)
    if task is None:
        return False

    done = getattr(task, "done", None)
    if callable(done) and done():
        return False
    return True


# ============================================================
# NORMALIZACIÓN
# ============================================================

def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )
    value = value.lower()
    value = re.sub(
        r"\b(official|oficial|video|audio|lyrics|lyric|letra|visualizer|hd|4k|hq)\b",
        " ",
        value,
    )
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _clean_title_for_search(title: str) -> str:
    title = re.sub(r"\([^)]*\)", " ", title)
    title = re.sub(r"\[[^\]]*\]", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def _extract_artist_from_track(track: Track) -> str | None:
    title = track.title or ""

    if " — " in title:
        possible_artist = title.rsplit(" — ", 1)[1].strip()
        if possible_artist:
            return possible_artist

    return None


# ============================================================
# HISTORIAL
# ============================================================

def _get_title_history(guild_id: int) -> deque[str]:
    history = _recent_titles.get(guild_id)
    if history is None:
        history = deque(maxlen=RECENT_HISTORY_SIZE)
        _recent_titles[guild_id] = history
    return history


def _get_url_history(guild_id: int) -> deque[str]:
    history = _recent_urls.get(guild_id)
    if history is None:
        history = deque(maxlen=RECENT_HISTORY_SIZE)
        _recent_urls[guild_id] = history
    return history


def _get_candidate_pool(guild_id: int) -> deque[dict]:
    pool = _candidate_pools.get(guild_id)
    if pool is None:
        pool = deque(maxlen=CANDIDATE_POOL_SIZE)
        _candidate_pools[guild_id] = pool
    return pool


def _remember_track(guild_id: int, track: Track | None) -> None:
    if track is None:
        return

    title_key = _normalize_text(track.title)

    if title_key:
        history = _get_title_history(guild_id)
        if title_key not in history:
            history.append(title_key)

    if track.url:
        history = _get_url_history(guild_id)
        if track.url not in history:
            history.append(track.url)


def _candidate_was_recent(
    guild_id: int,
    title: str,
    url: str | None,
) -> bool:
    title_key = _normalize_text(title)

    if title_key and title_key in _get_title_history(guild_id):
        return True

    if url and url in _get_url_history(guild_id):
        return True

    return False


# ============================================================
# FILTROS
# ============================================================

def _is_bad_candidate(title: str, duration: int | None) -> bool:
    normalized = _normalize_text(title)

    blocked_words = (
        "playlist",
        "full album",
        "album completo",
        "compilation",
        "reaction",
        "reaccion",
        "1 hour",
        "1 hora",
        "10 hours",
        "10 horas",
    )

    if any(word in normalized for word in blocked_words):
        return True

    if duration is not None:
        if duration < MIN_DURATION:
            return True
        if duration > MAX_DURATION:
            return True

    return False


# ============================================================
# ANTI-BOT
# ============================================================

def _youtube_is_temporarily_blocked() -> bool:
    return time.monotonic() < _youtube_blocked_until


def _mark_youtube_blocked(error: BaseException | str) -> None:
    global _youtube_blocked_until
    global _youtube_block_notice_shown
    global _anti_bot_blocks

    _youtube_blocked_until = (
        time.monotonic()
        + ANTI_BOT_COOLDOWN_SECONDS
    )

    _anti_bot_blocks += 1

    if _youtube_block_notice_shown:
        return

    _youtube_block_notice_shown = True

    browser = get_ytdlp_browser()

    print()
    print("⚠️ [CTX AUTOPLAY] YouTube activó verificación anti-bot.")

    if browser:
        print(
            f"Cookies del navegador configuradas: {browser}. "
            "YouTube las rechazó temporalmente."
        )
    else:
        print(
            "Solución local: agrega YTDLP_BROWSER=chrome "
            "a tu .env y reinicia CTX."
        )

    print(
        "Autoplay no seguirá insistiendo durante 5 minutos "
        "para evitar empeorar el bloqueo."
    )
    print()


# ============================================================
# YOUTUBE SEARCH
# ============================================================

def _search_youtube(query: str) -> list[dict]:
    options = build_ytdlp_options(
        flat=True,
        audio=False,
    )

    with yt_dlp.YoutubeDL(options) as ydl:
        result = ydl.extract_info(
            f"ytsearch{SEARCH_RESULTS}:{query}",
            download=False,
        )

    if not result:
        return []

    entries = result.get("entries") or []

    return [
        entry
        for entry in entries
        if entry
    ]


def _candidate_url(entry: dict) -> str | None:
    webpage_url = entry.get("webpage_url")

    if webpage_url:
        return str(webpage_url)

    video_id = entry.get("id")

    if video_id:
        return (
            "https://www.youtube.com/watch?v="
            f"{video_id}"
        )

    url = entry.get("url")

    if isinstance(url, str) and url.startswith("http"):
        return url

    return None


# ============================================================
# QUERIES
# ============================================================

def _build_search_queries(track: Track) -> list[str]:
    artist = _extract_artist_from_track(track)
    clean_title = _clean_title_for_search(track.title)
    queries: list[str] = []

    if artist:
        queries.extend(
            [
                f"{artist} official audio",
                f"{artist} topic",
            ]
        )

    if clean_title:
        queries.extend(
            [
                f"{clean_title} similar songs",
                f"{clean_title} related music",
            ]
        )

    if track.query:
        queries.append(
            f"{track.query} music"
        )

    unique_queries: list[str] = []
    seen: set[str] = set()

    for query in queries:
        key = query.strip().lower()

        if not key or key in seen:
            continue

        seen.add(key)
        unique_queries.append(query)

    return unique_queries


# ============================================================
# RELLENAR POOL
# ============================================================

async def _refill_candidate_pool(
    guild_id: int,
    finished_track: Track,
) -> None:
    global _pool_refills

    if _youtube_is_temporarily_blocked():
        return

    pool = _get_candidate_pool(guild_id)
    queries = _build_search_queries(finished_track)

    known_urls = {
        str(item.get("url") or "")
        for item in pool
    }

    used_queries = 0

    for query in queries:
        if used_queries >= MAX_SEARCH_QUERIES_PER_REFILL:
            break

        used_queries += 1

        try:
            entries = await asyncio.to_thread(
                _search_youtube,
                query,
            )
        except Exception as error:
            if is_youtube_antibot_error(error):
                _mark_youtube_blocked(error)
                return

            continue

        for entry in entries:
            title = str(entry.get("title") or "")
            url = _candidate_url(entry)

            duration_raw = entry.get("duration")

            try:
                duration = (
                    int(duration_raw)
                    if duration_raw is not None
                    else None
                )
            except (TypeError, ValueError):
                duration = None

            if not title or not url:
                continue

            if url in known_urls:
                continue

            if _is_bad_candidate(title, duration):
                continue

            if _candidate_was_recent(
                guild_id,
                title,
                url,
            ):
                continue

            pool.append(
                {
                    "title": title,
                    "url": url,
                    "duration": duration,
                }
            )

            known_urls.add(url)

            if len(pool) >= CANDIDATE_POOL_SIZE:
                break

        if len(pool) >= CANDIDATE_POOL_SIZE:
            break

    _pool_refills += 1


# ============================================================
# RESOLVER RECOMENDACIÓN
# ============================================================

async def _find_recommendation(
    guild_id: int,
    finished_track: Track,
    *,
    refills_remaining: int = 2,
) -> Track | None:
    global _recommendation_attempts
    global _recommendations_found
    global _pool_hits

    if _youtube_is_temporarily_blocked():
        return None

    _remember_track(
        guild_id,
        finished_track,
    )

    pool = _get_candidate_pool(guild_id)

    if not pool:
        if refills_remaining <= 0:
            return None
        await _refill_candidate_pool(
            guild_id,
            finished_track,
        )
        refills_remaining -= 1

    attempts = 0

    while pool and attempts < MAX_RESOLVE_ATTEMPTS:
        candidate = pool.popleft()
        _pool_hits += 1

        title = str(candidate.get("title") or "")
        url = str(candidate.get("url") or "")

        if not title or not url:
            continue

        if _candidate_was_recent(
            guild_id,
            title,
            url,
        ):
            continue

        attempts += 1
        _recommendation_attempts += 1

        try:
            request = create_search_request(url)
            resolved = await resolver_registry.resolve(request)
        except Exception as error:
            if is_youtube_antibot_error(error):
                _mark_youtube_blocked(error)
                return None

            continue

        if not resolved.stream_url:
            continue

        final_url = resolved.webpage_url or url
        final_title = resolved.title or title

        if _candidate_was_recent(
            guild_id,
            final_title,
            final_url,
        ):
            continue

        display_title = final_title

        if resolved.artist:
            display_title = (
                f"{final_title} — {resolved.artist}"
            )

        source_type = getattr(
            resolved.source_type,
            "value",
            str(resolved.source_type),
        )

        recommendation = Track(
            title=display_title,
            query=final_url,
            url=final_url,
            stream_url=resolved.stream_url,
            duration=resolved.duration,
            thumbnail=resolved.thumbnail,
            requester_id=0,
            requester_name="CTX AUTOPLAY",
            guild_id=guild_id,
            voice_channel_id=(
                finished_track.voice_channel_id
            ),
            source=source_type,
        )

        _recommendations_found += 1
        return recommendation

    # Si el pool quedó vacío por candidatos malos,
    # hacemos UN refill adicional, no una lluvia de búsquedas.
    if (
        not pool
        and refills_remaining > 0
        and not _youtube_is_temporarily_blocked()
    ):
        await _refill_candidate_pool(
            guild_id,
            finished_track,
        )

        if pool:
            return await _find_recommendation(
                guild_id,
                finished_track,
                refills_remaining=refills_remaining - 1,
            )

    return None


# ============================================================
# AUTOPLAY REAL
# ============================================================

async def continue_with_autoplay(
    guild_id: int,
    finished_track: Track | None,
    *,
    generation: int | None = None,
) -> bool:
    global _tracks_started
    global _failures
    global _skipped_autoplay_off
    global _skipped_queue_not_empty
    global _skipped_loop
    global _skipped_current_track
    global _youtube_block_notice_shown

    if finished_track is None:
        return False

    if generation is None:
        generation = _current_generation(guild_id)

    lock = _get_guild_lock(guild_id)

    async with lock:
        # AutoAdvance / AutoPlayback reciben primero el evento.
        await asyncio.sleep(0.40)

        if generation != _current_generation(guild_id):
            return False

        session = music_session_manager.get_session(guild_id)

        if not session.state.autoplay_enabled:
            _skipped_autoplay_off += 1
            return False

        if session.state.loop_enabled:
            _skipped_loop += 1
            return False

        if session.current_track is not None:
            _skipped_current_track += 1
            return False

        if session.has_pending_tracks():
            _skipped_queue_not_empty += 1
            return False

        if _youtube_is_temporarily_blocked():
            return False

        # Si el cooldown anterior ya terminó,
        # permitimos mostrar un aviso nuevo si vuelve a ocurrir.
        _youtube_block_notice_shown = False

        recommendation = await _find_recommendation(
            guild_id=guild_id,
            finished_track=finished_track,
        )

        if generation != _current_generation(guild_id):
            return False

        if recommendation is None:
            _failures += 1

            if not _youtube_is_temporarily_blocked():
                print(
                    "⚠️ [CTX AUTOPLAY] "
                    "No se encontró una recomendación reproducible."
                )

            return False

        # Revalidate and claim the idle player atomically against manual PLAY,
        # SKIP and STOP.  The generation was invalidated as soon as a manual
        # request arrived, even if its resolver is still running.
        async with get_guild_operation_lock(guild_id):
            if generation != _current_generation(guild_id):
                return False
            if not session.state.autoplay_enabled or session.state.loop_enabled:
                return False
            if session.current_track is not None or session.has_pending_tracks():
                return False

            session.queue.current = recommendation
            session.state.resume()

            try:
                started = await _start_prepared_track_unlocked(guild_id)
            except Exception as error:
                if session.current_track is recommendation:
                    session.queue.current = None

                _failures += 1

                if is_youtube_antibot_error(error):
                    _mark_youtube_blocked(error)
                else:
                    print(
                        "❌ [CTX AUTOPLAY] "
                        "No se pudo iniciar la recomendación:",
                        type(error).__name__,
                    )

                return False

        if not started:
            if session.current_track is recommendation:
                session.queue.current = None

            _failures += 1
            return False

        _remember_track(
            guild_id,
            recommendation,
        )

        _tracks_started += 1

        print()
        print(
            "🧠 [CTX AUTOPLAY] "
            "RECOMENDACIÓN AUTOMÁTICA"
        )
        print(
            "Anterior:",
            finished_track.title,
        )
        print(
            "Ahora:",
            recommendation.title,
        )
        print(
            "Pool restante:",
            len(_get_candidate_pool(guild_id)),
        )
        print()

        return True


# ============================================================
# EVENTOS
# ============================================================

def handle_autoplay_recommendation_event(
    event: PlaybackEvent,
) -> None:
    global _finished_received

    if event.event_type != PlaybackEventType.FINISHED:
        return

    _finished_received += 1

    if not is_async_scheduler_initialized():
        return

    try:
        cancel_pending_autoplay(event.guild_id)
        generation = _current_generation(event.guild_id)
        task = schedule_coroutine(
            continue_with_autoplay(
                guild_id=event.guild_id,
                finished_track=event.track,
                generation=generation,
            )
        )
        _pending_tasks[event.guild_id] = task

        def _remove_finished(completed) -> None:
            if _pending_tasks.get(event.guild_id) is completed:
                _pending_tasks.pop(event.guild_id, None)

        task.add_done_callback(_remove_finished)
    except RuntimeError:
        return


# ============================================================
# REGISTRO
# ============================================================

def register_autoplay_recommendations() -> None:
    global _registered

    if _registered:
        return

    playback_event_bus.subscribe(
        handle_autoplay_recommendation_event
    )

    _registered = True


def unregister_autoplay_recommendations() -> None:
    global _registered

    if not _registered:
        return

    playback_event_bus.unsubscribe(
        handle_autoplay_recommendation_event
    )

    for guild_id in tuple(_pending_tasks):
        task = _pending_tasks.pop(guild_id)
        cancel = getattr(task, "cancel", None)
        if callable(cancel):
            cancel()
        _guild_generations[guild_id] = _current_generation(guild_id) + 1

    _registered = False


# ============================================================
# RESUMEN
# ============================================================

def get_autoplay_recommendations_summary() -> dict:
    return {
        "registered": _registered,
        "finished_received": _finished_received,
        "recommendation_attempts": _recommendation_attempts,
        "recommendations_found": _recommendations_found,
        "tracks_started": _tracks_started,
        "failures": _failures,
        "pool_refills": _pool_refills,
        "pool_hits": _pool_hits,
        "anti_bot_blocks": _anti_bot_blocks,
        "youtube_temporarily_blocked": (
            _youtube_is_temporarily_blocked()
        ),
        "browser_cookies": bool(
            get_ytdlp_browser()
        ),
        "browser": get_ytdlp_browser(),
        "skipped_autoplay_off": _skipped_autoplay_off,
        "skipped_queue_not_empty": _skipped_queue_not_empty,
        "skipped_loop": _skipped_loop,
        "skipped_current_track": _skipped_current_track,
        "recent_history_size": RECENT_HISTORY_SIZE,
        "candidate_pool_size": CANDIDATE_POOL_SIZE,
        "pending_tasks": len(_pending_tasks),
        "real_recommendations": True,
        "loop_priority": True,
        "manual_queue_priority": True,
        "stopped_event_safe": True,
        "error_event_safe": True,
    }
