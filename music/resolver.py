"""
CTX V11
Sistema de resolución de fuentes musicales.

Este módulo administra los resolvers/proveedores
capaces de transformar una SearchRequest en un
ResolvedAudioSource.

TODAVÍA NO:
- busca en Internet
- reproduce audio
- descarga música
- contiene comandos Discord
"""

from abc import ABC, abstractmethod

from music.audio_source import ResolvedAudioSource
from music.search import SearchRequest


# ============================================================
# ERRORES
# ============================================================

class ResolverError(Exception):
    """
    Error general del sistema de resolución musical.
    """


class ResolverNotFoundError(ResolverError):
    """
    No existe ningún resolver capaz de manejar
    la búsqueda recibida.
    """


class ResolverFailedError(ResolverError):
    """
    Un resolver encontró la petición,
    pero no pudo resolverla correctamente.
    """


# ============================================================
# RESOLVER BASE
# ============================================================

class AudioResolver(ABC):
    """
    Clase base para todos los proveedores musicales.

    Más adelante podremos tener distintos resolvers
    sin modificar el resto de CTX Music.
    """

    name: str = "unknown"


    @abstractmethod
    def can_handle(
        self,
        request: SearchRequest
    ) -> bool:
        """
        Indica si este resolver puede manejar
        la petición recibida.
        """

        raise NotImplementedError


    @abstractmethod
    async def resolve(
        self,
        request: SearchRequest
    ) -> ResolvedAudioSource:
        """
        Resuelve la petición y devuelve
        una fuente musical preparada.
        """

        raise NotImplementedError


# ============================================================
# REGISTRO DE RESOLVERS
# ============================================================

class ResolverRegistry:
    """
    Registro central de proveedores musicales.
    """

    def __init__(
        self
    ) -> None:

        self._resolvers: list[
            AudioResolver
        ] = []


    # ========================================================
    # REGISTRAR
    # ========================================================

    def register(
        self,
        resolver: AudioResolver
    ) -> None:
        """
        Registra un nuevo resolver.

        Evita registrar dos veces
        exactamente la misma instancia.
        """

        if resolver in self._resolvers:
            return

        self._resolvers.append(
            resolver
        )


    # ========================================================
    # ELIMINAR
    # ========================================================

    def unregister(
        self,
        resolver: AudioResolver
    ) -> bool:

        if resolver not in self._resolvers:
            return False

        self._resolvers.remove(
            resolver
        )

        return True


    # ========================================================
    # BUSCAR RESOLVER
    # ========================================================

    def find_resolver(
        self,
        request: SearchRequest
    ) -> AudioResolver | None:
        """
        Devuelve el primer resolver capaz
        de manejar la búsqueda.
        """

        for resolver in self._resolvers:

            if resolver.can_handle(
                request
            ):
                return resolver


        return None


    # ========================================================
    # RESOLVER PETICIÓN
    # ========================================================

    async def resolve(
        self,
        request: SearchRequest
    ) -> ResolvedAudioSource:
        """
        Encuentra automáticamente el resolver
        adecuado y procesa la búsqueda.
        """

        resolver = self.find_resolver(
            request
        )


        if resolver is None:

            raise ResolverNotFoundError(
                "No existe un proveedor musical "
                "capaz de resolver esta búsqueda."
            )


        try:

            result = await resolver.resolve(
                request
            )


        except ResolverError:
            raise


        except Exception as error:

            raise ResolverFailedError(
                f"El resolver '{resolver.name}' "
                "no pudo procesar la búsqueda."
            ) from error


        if not result.is_valid():

            raise ResolverFailedError(
                f"El resolver '{resolver.name}' "
                "devolvió una fuente inválida."
            )


        return result


    # ========================================================
    # LISTAR RESOLVERS
    # ========================================================

    def get_registered_names(
        self
    ) -> list[str]:

        return [
            resolver.name
            for resolver in self._resolvers
        ]


    # ========================================================
    # CANTIDAD
    # ========================================================

    def count(
        self
    ) -> int:

        return len(
            self._resolvers
        )


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

resolver_registry = ResolverRegistry()


# ============================================================
# RESUMEN
# ============================================================

def get_resolver_system_summary() -> dict:
    """
    Estado actual del sistema.

    Todavía aparecerá sin proveedores porque
    aún no hemos creado ninguno.
    """

    return {

        "registered_resolvers":
            resolver_registry.count(),

        "resolver_names":
            resolver_registry.get_registered_names(),

        "internet_enabled":
            False,

        "ready_for_providers":
            True,
    }