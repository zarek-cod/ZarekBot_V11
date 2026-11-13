"""
CTX V11
Administrador de backends de reproducción.

Este módulo mantiene un backend independiente
para cada servidor de Discord.

TODAVÍA NO:
- reproduce audio real
- conecta a Discord Voice
- utiliza FFmpeg directamente
- contiene comandos
- contiene interfaz
"""

from collections.abc import Callable

from music.playback_backend import PlaybackBackend


# ============================================================
# TIPOS
# ============================================================

BackendFactory = Callable[
    [int],
    PlaybackBackend
]


# ============================================================
# ADMINISTRADOR DE BACKENDS
# ============================================================

class PlaybackBackendManager:
    """
    Administra un backend de reproducción
    independiente para cada servidor.
    """

    def __init__(
        self
    ) -> None:

        self._backends: dict[
            int,
            PlaybackBackend
        ] = {}

        self._factory: BackendFactory | None = None


    # ========================================================
    # CONFIGURAR FÁBRICA
    # ========================================================

    def set_factory(
        self,
        factory: BackendFactory
    ) -> None:
        """
        Configura la función encargada
        de crear los backends.

        Más adelante utilizaremos:

            DiscordPlaybackBackend
        """

        self._factory = factory


    # ========================================================
    # ¿HAY FÁBRICA?
    # ========================================================

    def has_factory(
        self
    ) -> bool:

        return (
            self._factory
            is not None
        )


    # ========================================================
    # REGISTRAR BACKEND MANUALMENTE
    # ========================================================

    def register_backend(
        self,
        guild_id: int,
        backend: PlaybackBackend
    ) -> None:
        """
        Permite registrar manualmente
        un backend existente.
        """

        if backend.guild_id != guild_id:

            raise ValueError(
                "El guild_id del backend "
                "no coincide con el servidor."
            )


        self._backends[
            guild_id
        ] = backend


    # ========================================================
    # OBTENER BACKEND
    # ========================================================

    def get_backend(
        self,
        guild_id: int
    ) -> PlaybackBackend:
        """
        Devuelve el backend del servidor.

        Si no existe, intentará crearlo
        utilizando la fábrica configurada.
        """

        existing = self._backends.get(
            guild_id
        )


        if existing is not None:

            return existing


        if self._factory is None:

            raise RuntimeError(
                "CTX Music todavía no tiene "
                "un backend de reproducción configurado."
            )


        backend = self._factory(
            guild_id
        )


        if not isinstance(
            backend,
            PlaybackBackend
        ):

            raise TypeError(
                "La fábrica configurada no devolvió "
                "un PlaybackBackend válido."
            )


        self._backends[
            guild_id
        ] = backend


        return backend


    # ========================================================
    # COMPROBAR SI EXISTE
    # ========================================================

    def has_backend(
        self,
        guild_id: int
    ) -> bool:

        return (
            guild_id
            in self._backends
        )


    # ========================================================
    # ELIMINAR BACKEND
    # ========================================================

    def remove_backend(
        self,
        guild_id: int
    ) -> bool:

        if guild_id not in self._backends:

            return False


        del self._backends[
            guild_id
        ]

        return True


    # ========================================================
    # OBTENER TODOS
    # ========================================================

    def get_all_backends(
        self
    ) -> list[PlaybackBackend]:

        return list(
            self._backends.values()
        )


    # ========================================================
    # CANTIDAD
    # ========================================================

    def active_backends(
        self
    ) -> int:

        return len(
            self._backends
        )


    # ========================================================
    # LIMPIAR
    # ========================================================

    def clear(
        self
    ) -> None:

        self._backends.clear()


    # ========================================================
    # RESUMEN
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:

        return {

            "factory_configured":
                self.has_factory(),

            "active_backends":
                self.active_backends(),

            "guilds":
                list(
                    self._backends.keys()
                ),
        }


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

playback_backend_manager = PlaybackBackendManager()


# ============================================================
# RESUMEN DEL SISTEMA
# ============================================================

def get_backend_manager_summary() -> dict:

    return playback_backend_manager.to_safe_dict()