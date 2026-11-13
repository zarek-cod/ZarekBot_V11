"""
CTX V11
Configuración central de proveedores musicales.

ORDEN DE PRIORIDAD:

1. DirectAudioResolver
   - enlaces directos .mp3, .ogg, .m4a, etc.

2. YouTubeResolver
   - búsquedas por texto
   - enlaces de YouTube

3. TestMusicResolver
   - solamente fallback temporal de desarrollo

El orden es importante.
Los resolvers más específicos deben ejecutarse primero.
"""

from music.resolver import (
    resolver_registry,
)

from music.providers.direct_resolver import (
    direct_audio_resolver,
)

from music.providers.youtube_resolver import (
    youtube_resolver,
)

from music.test_resolver import (
    test_music_resolver,
)


# ============================================================
# ESTADO
# ============================================================

_configured = False


# ============================================================
# CONFIGURAR PROVEEDORES
# ============================================================

def configure_music_resolvers() -> None:
    """
    Registra todos los resolvers disponibles.

    Puede ejecutarse varias veces
    sin registrar duplicados.
    """

    global _configured


    if _configured:
        return


    # ========================================================
    # 1. AUDIO DIRECTO
    # ========================================================
    #
    # Ejemplo:
    #
    # https://servidor.com/cancion.mp3
    #

    resolver_registry.register(
        direct_audio_resolver
    )


    # ========================================================
    # 2. YOUTUBE
    # ========================================================
    #
    # Ejemplos:
    #
    # Blinding Lights The Weeknd
    #
    # https://youtube.com/watch?v=...
    #

    resolver_registry.register(
        youtube_resolver
    )


    # ========================================================
    # 3. RESOLVER DE PRUEBA
    # ========================================================
    #
    # Temporal.
    #
    # Más adelante podremos eliminarlo
    # cuando todos los proveedores reales
    # estén terminados.
    #

    resolver_registry.register(
        test_music_resolver
    )


    _configured = True


# ============================================================
# ¿ESTÁ CONFIGURADO?
# ============================================================

def are_music_resolvers_configured() -> bool:

    return _configured


# ============================================================
# REINICIAR
# ============================================================

def reset_music_resolvers() -> None:
    """
    Elimina los resolvers registrados.

    Útil durante pruebas.
    """

    global _configured


    resolver_registry.unregister(
        direct_audio_resolver
    )


    resolver_registry.unregister(
        youtube_resolver
    )


    resolver_registry.unregister(
        test_music_resolver
    )


    _configured = False


# ============================================================
# RESUMEN
# ============================================================

def get_music_resolver_setup_summary() -> dict:

    names = (
        resolver_registry.get_registered_names()
    )


    return {

        "configured":
            _configured,

        "registered_resolvers":
            resolver_registry.count(),

        "resolver_names":
            names,

        "direct_audio":
            (
                direct_audio_resolver.name
                in names
            ),

        "youtube":
            (
                youtube_resolver.name
                in names
            ),

        "test_resolver":
            (
                test_music_resolver.name
                in names
            ),

        "real_music_search":
            (
                youtube_resolver.name
                in names
            ),
    }