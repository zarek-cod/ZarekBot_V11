"""
CTX V11
Resolver musical de prueba.

Este módulo sirve únicamente para comprobar
que el sistema de resolvers funciona correctamente.

NO:
- usa Internet
- reproduce música
- descarga archivos
- contiene comandos
"""

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
# RESOLVER DE PRUEBA
# ============================================================

class TestMusicResolver(
    AudioResolver
):
    """
    Resolver ficticio utilizado durante
    el desarrollo de CTX Music.
    """

    name = "ctx_test_resolver"


    # ========================================================
    # ¿PUEDE MANEJAR ESTA BÚSQUEDA?
    # ========================================================

    def can_handle(
        self,
        request: SearchRequest
    ) -> bool:

        return (
            request.search_type
            in {
                SearchType.TEXT,
                SearchType.URL,
            }
        )


    # ========================================================
    # RESOLVER
    # ========================================================

    async def resolve(
        self,
        request: SearchRequest
    ) -> ResolvedAudioSource:
        """
        Genera una canción ficticia utilizando
        los datos de la búsqueda.
        """

        return ResolvedAudioSource(

            title=request.normalized_query,

            artist="CTX TEST",

            source_type=AudioSourceType.SEARCH,

            webpage_url=(
                request.normalized_query
                if request.is_url
                else None
            ),

            thumbnail=None,

            duration=180,

            stream_url=None,

            source_id="ctx-test-001",
        )


# ============================================================
# INSTANCIA
# ============================================================

test_music_resolver = (
    TestMusicResolver()
)


# ============================================================
# RESUMEN
# ============================================================

def get_test_resolver_summary() -> dict:

    return {

        "name":
            test_music_resolver.name,

        "internet":
            False,

        "real_audio":
            False,

        "text_search":
            True,

        "url_search":
            True,

        "development_only":
            True,
    }