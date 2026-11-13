"""
CTX V11
Prueba aislada:

YouTube
   ↓
yt-dlp
   ↓
stream_url
   ↓
FFmpeg

No usa Discord.
"""

import asyncio
import os
import subprocess

from music.resolver_setup import (
    configure_music_resolvers,
)

from music.resolver import (
    resolver_registry,
)

from music.search import (
    create_search_request,
)


async def main():

    print(
        "🔎 Buscando..."
    )


    configure_music_resolvers()


    request = create_search_request(
        "Blinding Lights The Weeknd"
    )


    result = await resolver_registry.resolve(
        request
    )


    print()
    print(
        "TÍTULO:",
        result.title
    )

    print(
        "ARTISTA:",
        result.artist
    )

    print(
        "FUENTE:",
        result.source_type.value
    )

    print(
        "DURACIÓN:",
        result.duration
    )

    print(
        "STREAM:",
        bool(result.stream_url)
    )

    print(
        "SOURCE ID:",
        result.source_id
    )


    if not result.stream_url:

        print(
            "❌ YouTube no entregó stream."
        )

        return


    ffmpeg = os.path.abspath(
        "ffmpeg.exe"
    )


    if not os.path.exists(
        ffmpeg
    ):

        ffmpeg = "ffmpeg"


    print()
    print(
        "🎧 Probando 8 segundos de audio..."
    )


    process = subprocess.run(

        [
            ffmpeg,

            "-hide_banner",

            "-loglevel",
            "warning",

            "-reconnect",
            "1",

            "-reconnect_streamed",
            "1",

            "-reconnect_delay_max",
            "5",

            "-i",
            result.stream_url,

            "-t",
            "8",

            "-vn",

            "-f",
            "null",

            "NUL",
        ],

        capture_output=True,

        text=True,
    )


    print()
    print(
        "FFMPEG EXIT:",
        process.returncode
    )


    stderr = (
        process.stderr.strip()
    )


    if stderr:

        print()
        print(
            "FFMPEG:"
        )

        print(
            stderr[-2000:]
        )


    if process.returncode == 0:

        print()
        print(
            "✅ FFmpeg pudo leer "
            "el stream."
        )

    else:

        print()
        print(
            "❌ FFmpeg NO pudo "
            "leer correctamente "
            "el stream."
        )


if __name__ == "__main__":

    asyncio.run(
        main()
    )