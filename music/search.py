"""
CTX V11
Sistema base de búsquedas musicales.

Este módulo prepara y clasifica las búsquedas.

TODAVÍA NO:
- consulta Internet
- reproduce música
- descarga audio
- contiene comandos Discord

Ejemplos que podrá interpretar:

    blinding lights
    Bad Bunny Monaco
    https://...
"""


from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


# ============================================================
# TIPO DE BÚSQUEDA
# ============================================================

class SearchType(str, Enum):

    TEXT = "text"

    URL = "url"

    UNKNOWN = "unknown"


# ============================================================
# PETICIÓN DE BÚSQUEDA
# ============================================================

@dataclass(frozen=True)
class SearchRequest:
    """
    Representa lo que un usuario quiere buscar.
    """

    original_query: str

    normalized_query: str

    search_type: SearchType


    # ========================================================
    # COMPROBACIONES
    # ========================================================

    @property
    def is_url(
        self
    ) -> bool:

        return (
            self.search_type
            == SearchType.URL
        )


    @property
    def is_text(
        self
    ) -> bool:

        return (
            self.search_type
            == SearchType.TEXT
        )


    # ========================================================
    # VALIDACIÓN
    # ========================================================

    def is_valid(
        self
    ) -> bool:

        return bool(
            self.normalized_query
        )


    # ========================================================
    # RESUMEN
    # ========================================================

    def to_safe_dict(
        self
    ) -> dict:

        return {

            "original_query":
                self.original_query,

            "normalized_query":
                self.normalized_query,

            "search_type":
                self.search_type.value,

            "valid":
                self.is_valid(),
        }


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalize_query(
    query: str
) -> str:
    """
    Limpia espacios innecesarios.

    Ejemplo:

        "   Bad   Bunny   Monaco  "

    pasa a:

        "Bad Bunny Monaco"
    """

    if not query:
        return ""


    return " ".join(
        query.strip().split()
    )


# ============================================================
# DETECTAR URL
# ============================================================

def is_valid_url(
    value: str
) -> bool:
    """
    Comprueba si el texto parece
    una URL HTTP/HTTPS válida.
    """

    try:

        result = urlparse(
            value
        )


        return (
            result.scheme
            in {
                "http",
                "https",
            }
            and bool(
                result.netloc
            )
        )


    except ValueError:

        return False


# ============================================================
# DETECTAR TIPO
# ============================================================

def detect_search_type(
    query: str
) -> SearchType:

    normalized = normalize_query(
        query
    )


    if not normalized:

        return SearchType.UNKNOWN


    if is_valid_url(
        normalized
    ):

        return SearchType.URL


    return SearchType.TEXT


# ============================================================
# CREAR PETICIÓN
# ============================================================

def create_search_request(
    query: str
) -> SearchRequest:
    """
    Convierte el texto recibido
    en una petición preparada para CTX Music.
    """

    normalized = normalize_query(
        query
    )


    search_type = detect_search_type(
        normalized
    )


    return SearchRequest(

        original_query=query,

        normalized_query=normalized,

        search_type=search_type,
    )


# ============================================================
# VALIDAR PETICIÓN
# ============================================================

def validate_search_request(
    request: SearchRequest
) -> None:
    """
    Lanza un error si la búsqueda está vacía
    o no puede utilizarse.
    """

    if not request.is_valid():

        raise ValueError(
            "La búsqueda musical está vacía."
        )


    if (
        request.search_type
        == SearchType.UNKNOWN
    ):

        raise ValueError(
            "No se pudo identificar la búsqueda."
        )


# ============================================================
# RESUMEN DEL SISTEMA
# ============================================================

def get_search_system_summary() -> dict:

    return {

        "text_search":
            True,

        "url_detection":
            True,

        "internet_search":
            False,

        "audio_playback":
            False,
    }