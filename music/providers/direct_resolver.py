"""
CTX V11
Resolver de enlaces directos de audio.

Este proveedor permite reproducir URLs directas
que apunten a archivos de audio compatibles.

Ejemplos:

    https://servidor.com/cancion.mp3
    https://servidor.com/audio.ogg
    https://servidor.com/music.m4a

NO busca canciones por nombre.
NO utiliza YouTube.
NO descarga archivos.
"""

from urllib.parse import urlparse

from music.audio_source import (
    AudioSourceType,
    ResolvedAudioSource,
)
from music.resolver import AudioResolver
from music.search import (
    SearchRequest,
    SearchType,
)


# ============================================================
# FORMATOS SOPORTADOS
# ============================================================

SUPPORTED_AUDIO_EXTENSIONS = {

    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
}


# ============================================================
# UTILIDADES
# ============================================================

def get_url_extension(
    url: str
) -> str:
    """
    Obtiene la extensión del archivo
    ignorando parámetros de la URL.
    """

    parsed = urlparse(
        url
    )

    path = parsed.path.lower()


    for extension in (
        SUPPORTED_AUDIO_EXTENSIONS
    ):

        if path.endswith(
            extension
        ):

            return extension


    return ""


def is_direct_audio_url(
    url: str
) -> bool:
    """
    Comprueba si la URL parece apuntar
    directamente a un archivo de audio.
    """

    return bool(
        get_url_extension(
            url
        )
    )


# ============================================================
# RESOLVER DIRECTO
# ============================================================

class DirectAudioResolver(
    AudioResolver
):
    """
    Resolver para archivos de audio directos.
    """

    name = "direct_audio"


    # ========================================================
    # ¿PUEDE MANEJAR ESTA PETICIÓN?
    # ========================================================

    def can_handle(
        self,
        request: SearchRequest
    ) -> bool:

        if (
            request.search_type
            != SearchType.URL
        ):

            return False


        return is_direct_audio_url(
            request.normalized_query
        )


    # ========================================================
    # RESOLVER
    # ========================================================

    async def resolve(
        self,
        request: SearchRequest
    ) -> ResolvedAudioSource:

        url = (
            request.normalized_query
        )


        extension = get_url_extension(
            url
        )


        if not extension:

            raise ValueError(
                "La URL no apunta a un "
                "formato de audio compatible."
            )


        parsed = urlparse(
            url
        )


        filename = (
            parsed.path
            .split("/")[-1]
        )


        title = (
            filename
            .rsplit(".", 1)[0]
            .replace("_", " ")
            .replace("-", " ")
            .strip()
        )


        if not title:

            title = "Audio directo"


        return ResolvedAudioSource(

            title=title,

            artist=None,

            source_type=(
                AudioSourceType.DIRECT
            ),

            webpage_url=url,

            thumbnail=None,

            duration=None,

            # Aquí sí tenemos una fuente
            # directamente reproducible.
            stream_url=url,

            source_id=None,
        )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

direct_audio_resolver = (
    DirectAudioResolver()
)


# ============================================================
# RESUMEN
# ============================================================

def get_direct_resolver_summary() -> dict:

    return {

        "name":
            direct_audio_resolver.name,

        "direct_audio":
            True,

        "text_search":
            False,

        "internet_search":
            False,

        "provides_stream":
            True,

        "formats":
            sorted(
                SUPPORTED_AUDIO_EXTENSIONS
            ),
    }