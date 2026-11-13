"""
CTX V11
Prueba real del proveedor de YouTube.

Esta prueba:

- realiza una búsqueda real
- obtiene información mediante yt-dlp
- comprueba que exista stream
- NO reproduce audio
- NO conecta a Discord
- NO muestra la URL privada/temporal del stream
"""

import asyncio

from music.providers.youtube_resolver import (
    youtube_resolver,
)

from music.search import (
    create_search_request,
)


# ============================================================
# PRUEBA
# ============================================================

async def run_youtube_resolver_test() -> dict:

    # ========================================================
    # BÚSQUEDA REAL
    # ========================================================

    request = create_search_request(
        "Blinding Lights The Weeknd"
    )


    # ========================================================
    # RESOLVER CON YT-DLP
    # ========================================================

    source = await youtube_resolver.resolve(
        request
    )


    # ========================================================
    # RESULTADO SEGURO
    # ========================================================

    result = {

        "title":
            source.title,

        "artist":
            source.artist,

        "source":
            source.source_type.value,

        "duration":
            source.formatted_duration,

        "has_stream":
            source.has_stream,

        "has_thumbnail":
            source.has_thumbnail,

        "source_id":
            source.source_id,

        "webpage_url":
            source.webpage_url,

        "valid":
            source.is_valid(),
    }


    return result


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    try:

        result = asyncio.run(
            run_youtube_resolver_test()
        )


        print(
            result
        )


    except Exception as error:

        print(
            "YOUTUBE TEST ERROR:"
        )

        print(
            type(error).__name__
        )

        print(
            str(error)
        )