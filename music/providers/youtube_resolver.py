"""
CTX V11
Proveedor real de YouTube mediante yt-dlp.

Versión reforzada:
- búsqueda por texto
- enlaces de YouTube
- stream para FFmpeg
- cookies opcionales desde navegador
- mensajes cortos ante bloqueo anti-bot
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import yt_dlp

from music.audio_source import (
    AudioSourceType,
    ResolvedAudioSource,
)
from music.resolver import (
    AudioResolver,
    ResolverFailedError,
)
from music.search import (
    SearchRequest,
    SearchType,
)
from music.ytdlp_config import (
    build_ytdlp_options,
    get_ytdlp_browser,
    is_youtube_antibot_error,
)


YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


# ============================================================
# URL YOUTUBE
# ============================================================

def is_youtube_url(value: str) -> bool:

    try:
        parsed = urlparse(value)
        hostname = (parsed.hostname or "").lower()
        return hostname in YOUTUBE_DOMAINS
    except ValueError:
        return False


# ============================================================
# ARTISTA
# ============================================================

def _extract_artist(info: dict) -> str | None:

    for key in (
        "artist",
        "uploader",
        "channel",
    ):
        value = info.get(key)
        if value:
            return str(value)

    return None


# ============================================================
# DURACIÓN
# ============================================================

def _extract_duration(info: dict) -> int | None:

    duration = info.get("duration")

    if duration is None:
        return None

    try:
        return int(duration)
    except (TypeError, ValueError):
        return None


# ============================================================
# YT-DLP BLOQUEANTE
# ============================================================

def _extract_with_ytdlp(query: str) -> dict:

    options = build_ytdlp_options(
        flat=False,
        audio=True,
    )

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                query,
                download=False,
            )
    except Exception as error:
        if is_youtube_antibot_error(error):
            browser = get_ytdlp_browser()

            if browser:
                raise ResolverFailedError(
                    "YouTube rechazó temporalmente la extracción "
                    f"incluso usando cookies de {browser}."
                ) from error

            raise ResolverFailedError(
                "YouTube pidió verificación anti-bot. "
                "Agrega YTDLP_BROWSER=chrome en .env "
                "y reinicia CTX."
            ) from error

        raise

    if not info:
        raise ResolverFailedError(
            "YouTube no devolvió resultados."
        )

    entries = info.get("entries")

    if entries is not None:
        valid_entries = [
            entry
            for entry in entries
            if entry is not None
        ]

        if not valid_entries:
            raise ResolverFailedError(
                "No se encontraron resultados para esa búsqueda."
            )

        info = valid_entries[0]

    return info


# ============================================================
# RESOLVER YOUTUBE
# ============================================================

class YouTubeResolver(AudioResolver):

    name = "youtube"

    def can_handle(
        self,
        request: SearchRequest,
    ) -> bool:

        if request.search_type == SearchType.TEXT:
            return True

        if request.search_type == SearchType.URL:
            return is_youtube_url(
                request.normalized_query
            )

        return False

    async def resolve(
        self,
        request: SearchRequest,
    ) -> ResolvedAudioSource:

        if request.is_text:
            query = (
                "ytsearch1:"
                f"{request.normalized_query}"
            )
        else:
            query = request.normalized_query

        try:
            info = await asyncio.to_thread(
                _extract_with_ytdlp,
                query,
            )
        except ResolverFailedError:
            raise
        except Exception as error:
            raise ResolverFailedError(
                "YouTube no pudo resolver la búsqueda solicitada."
            ) from error

        title = (
            info.get("title")
            or "Canción desconocida"
        )

        stream_url = info.get("url")

        webpage_url = (
            info.get("webpage_url")
            or info.get("original_url")
        )

        thumbnail = info.get("thumbnail")
        source_id = info.get("id")
        artist = _extract_artist(info)
        duration = _extract_duration(info)

        if not stream_url:
            raise ResolverFailedError(
                "YouTube encontró la canción, "
                "pero no entregó un stream de audio."
            )

        return ResolvedAudioSource(
            title=str(title),
            artist=artist,
            source_type=AudioSourceType.YOUTUBE,
            webpage_url=(
                str(webpage_url)
                if webpage_url
                else None
            ),
            thumbnail=(
                str(thumbnail)
                if thumbnail
                else None
            ),
            duration=duration,
            stream_url=str(stream_url),
            source_id=(
                str(source_id)
                if source_id
                else None
            ),
        )


youtube_resolver = YouTubeResolver()


def get_youtube_resolver_summary() -> dict:

    return {
        "name": youtube_resolver.name,
        "text_search": True,
        "youtube_urls": True,
        "provides_stream": True,
        "provides_title": True,
        "provides_artist": True,
        "provides_duration": True,
        "provides_thumbnail": True,
        "downloads_files": False,
        "async_non_blocking": True,
        "browser_cookies": bool(
            get_ytdlp_browser()
        ),
    }
