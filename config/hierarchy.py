"""
CTX V11
Sistema oficial de jerarquías.

La posición y el nivel determinan la autoridad del usuario.

IMPORTANTE:
- Las autoridades especiales se reconocen por ID de usuario.
- Los rangos se reconocen por ID de rol.
- Los nombres y nicknames NO otorgan autoridad.
"""

import os
from enum import IntEnum

# Importar settings provoca también la carga segura del archivo .env
from config.settings import ENV_FILE


# ============================================================
# NIVELES DE JERARQUÍA
# ============================================================

class HierarchyLevel(IntEnum):
    """
    Cuanto mayor sea el número,
    mayor autoridad tiene el usuario.
    """

    # --------------------------------------------------------
    # SIN JERARQUÍA / CASTIGOS
    # --------------------------------------------------------

    SIN_ACCESO = 0

    ALMA_CONDENADA = 100

    SIMPLE_MORTAL = 200

    DEVOTO = 300

    PERRA_DE_ZAREK = 350

    SER_ASCENDIDO = 400

    ANGELES = 450

    SUPERVISOR = 500

    DIOS_EN_PROCESO = 550

    SEMIDIOS = 600

    DIOS = 650

    PRIMORDIAL = 700

    ASISTENTE = 750

    DEIDAD = 800

    # --------------------------------------------------------
    # AUTORIDADES ESPECIALES
    # --------------------------------------------------------

    REY_PVP = 850

    CREADOR_DEL_SERVIDOR = 900

    ALTO_MANDO = 950

    CREADOR = 1000


# ============================================================
# NOMBRES VISIBLES
# ============================================================

HIERARCHY_NAMES = {

    HierarchyLevel.SIN_ACCESO:
        "Sin Acceso",

    HierarchyLevel.ALMA_CONDENADA:
        "Alma Condenada",

    HierarchyLevel.SIMPLE_MORTAL:
        "Simple Mortal",

    HierarchyLevel.DEVOTO:
        "Devoto",

    HierarchyLevel.PERRA_DE_ZAREK:
        "Perra de Zarek",

    HierarchyLevel.SER_ASCENDIDO:
        "Ser Ascendido",

    HierarchyLevel.ANGELES:
        "Ángeles",

    HierarchyLevel.SUPERVISOR:
        "Supervisor",

    HierarchyLevel.DIOS_EN_PROCESO:
        "Dios en Proceso",

    HierarchyLevel.SEMIDIOS:
        "Semidios",

    HierarchyLevel.DIOS:
        "Dios",

    HierarchyLevel.PRIMORDIAL:
        "Primordial",

    HierarchyLevel.ASISTENTE:
        "Asistente",

    HierarchyLevel.DEIDAD:
        "Deidad",

    HierarchyLevel.REY_PVP:
        "Rey PVP",

    HierarchyLevel.CREADOR_DEL_SERVIDOR:
        "Creador del Servidor",

    HierarchyLevel.ALTO_MANDO:
        "Alto Mando",

    HierarchyLevel.CREADOR:
        "Creador",
}


# ============================================================
# EMOJIS
# ============================================================

HIERARCHY_EMOJIS = {

    HierarchyLevel.SIN_ACCESO:
        "🚫",

    HierarchyLevel.ALMA_CONDENADA:
        "💀",

    HierarchyLevel.SIMPLE_MORTAL:
        "👤",

    HierarchyLevel.DEVOTO:
        "🙏",

    HierarchyLevel.PERRA_DE_ZAREK:
        "⛓️",

    HierarchyLevel.SER_ASCENDIDO:
        "✨",

    HierarchyLevel.ANGELES:
        "😇",

    HierarchyLevel.SUPERVISOR:
        "🛡️",

    HierarchyLevel.DIOS_EN_PROCESO:
        "⚡",

    HierarchyLevel.SEMIDIOS:
        "⚔️",

    HierarchyLevel.DIOS:
        "🔥",

    HierarchyLevel.PRIMORDIAL:
        "🌌",

    HierarchyLevel.ASISTENTE:
        "🧠",

    HierarchyLevel.DEIDAD:
        "👁️",

    HierarchyLevel.REY_PVP:
        "⚔️",

    HierarchyLevel.CREADOR_DEL_SERVIDOR:
        "👑",

    HierarchyLevel.ALTO_MANDO:
        "🎖️",

    HierarchyLevel.CREADOR:
        "👑",
}


# ============================================================
# FUNCIONES PARA LEER IDS
# ============================================================

def _parse_id(
    value: str | None
) -> int | None:
    """
    Convierte una variable del .env
    en un ID entero.
    """

    if not value:
        return None

    value = value.strip()

    if not value:
        return None

    try:
        return int(value)

    except ValueError:
        return None


def _parse_id_list(
    value: str | None
) -> set[int]:
    """
    Permite utilizar varios IDs.

    Ejemplo:

    123456,987654,555555

    Resultado:

    {
        123456,
        987654,
        555555
    }
    """

    if not value:
        return set()

    ids: set[int] = set()

    for item in value.split(","):

        item = item.strip()

        if not item:
            continue

        try:
            ids.add(
                int(item)
            )

        except ValueError:
            continue

    return ids


# ============================================================
# AUTORIDADES POR ID DE USUARIO
# ============================================================

CREATOR_IDS = _parse_id_list(
    os.getenv(
        "CREATOR_IDS"
    )
)


HIGH_COMMAND_IDS = _parse_id_list(
    os.getenv(
        "HIGH_COMMAND_IDS"
    )
)


CREADOR_DEL_SERVIDOR_IDS = _parse_id_list(
    os.getenv(
        "CREADOR_DEL_SERVIDOR_IDS"
    )
)


REY_PVP_IDS = _parse_id_list(
    os.getenv(
        "REY_PVP_IDS"
    )
)


# ============================================================
# ROLES DE DISCORD
# ============================================================

ROLE_DEIDAD_ID = _parse_id(
    os.getenv(
        "ROLE_DEIDAD_ID"
    )
)


ROLE_ASISTENTE_ID = _parse_id(
    os.getenv(
        "ROLE_ASISTENTE_ID"
    )
)


ROLE_PRIMORDIAL_ID = _parse_id(
    os.getenv(
        "ROLE_PRIMORDIAL_ID"
    )
)


ROLE_DIOS_ID = _parse_id(
    os.getenv(
        "ROLE_DIOS_ID"
    )
)


ROLE_SEMIDIOS_ID = _parse_id(
    os.getenv(
        "ROLE_SEMIDIOS_ID"
    )
)


ROLE_DIOS_EN_PROCESO_ID = _parse_id(
    os.getenv(
        "ROLE_DIOS_EN_PROCESO_ID"
    )
)


ROLE_SUPERVISOR_ID = _parse_id(
    os.getenv(
        "ROLE_SUPERVISOR_ID"
    )
)


ROLE_ANGELES_ID = _parse_id(
    os.getenv(
        "ROLE_ANGELES_ID"
    )
)


ROLE_SER_ASCENDIDO_ID = _parse_id(
    os.getenv(
        "ROLE_SER_ASCENDIDO_ID"
    )
)


ROLE_PERRA_DE_ZAREK_ID = _parse_id(
    os.getenv(
        "ROLE_PERRA_DE_ZAREK_ID"
    )
)


ROLE_DEVOTO_ID = _parse_id(
    os.getenv(
        "ROLE_DEVOTO_ID"
    )
)


ROLE_SIMPLE_MORTAL_ID = _parse_id(
    os.getenv(
        "ROLE_SIMPLE_MORTAL_ID"
    )
)


ROLE_ALMA_CONDENADA_ID = _parse_id(
    os.getenv(
        "ROLE_ALMA_CONDENADA_ID"
    )
)


ROLE_SIN_ACCESO_ID = _parse_id(
    os.getenv(
        "ROLE_SIN_ACCESO_ID"
    )
)


# ============================================================
# JERARQUÍA DE USUARIOS ESPECIALES
# ============================================================

SPECIAL_USER_HIERARCHY = {}


for user_id in CREATOR_IDS:

    SPECIAL_USER_HIERARCHY[
        user_id
    ] = HierarchyLevel.CREADOR


for user_id in HIGH_COMMAND_IDS:

    SPECIAL_USER_HIERARCHY[
        user_id
    ] = HierarchyLevel.ALTO_MANDO


for user_id in CREADOR_DEL_SERVIDOR_IDS:

    SPECIAL_USER_HIERARCHY[
        user_id
    ] = HierarchyLevel.CREADOR_DEL_SERVIDOR


for user_id in REY_PVP_IDS:

    SPECIAL_USER_HIERARCHY[
        user_id
    ] = HierarchyLevel.REY_PVP


# ============================================================
# JERARQUÍA DE ROLES
# ============================================================

ROLE_HIERARCHY = {}


def _register_role(
    role_id: int | None,
    level: HierarchyLevel
) -> None:
    """
    Registra un rol solamente
    si existe un ID configurado.
    """

    if role_id is not None:

        ROLE_HIERARCHY[
            role_id
        ] = level


_register_role(
    ROLE_DEIDAD_ID,
    HierarchyLevel.DEIDAD
)

_register_role(
    ROLE_ASISTENTE_ID,
    HierarchyLevel.ASISTENTE
)

_register_role(
    ROLE_PRIMORDIAL_ID,
    HierarchyLevel.PRIMORDIAL
)

_register_role(
    ROLE_DIOS_ID,
    HierarchyLevel.DIOS
)

_register_role(
    ROLE_SEMIDIOS_ID,
    HierarchyLevel.SEMIDIOS
)

_register_role(
    ROLE_DIOS_EN_PROCESO_ID,
    HierarchyLevel.DIOS_EN_PROCESO
)

_register_role(
    ROLE_SUPERVISOR_ID,
    HierarchyLevel.SUPERVISOR
)

_register_role(
    ROLE_ANGELES_ID,
    HierarchyLevel.ANGELES
)

_register_role(
    ROLE_SER_ASCENDIDO_ID,
    HierarchyLevel.SER_ASCENDIDO
)

_register_role(
    ROLE_PERRA_DE_ZAREK_ID,
    HierarchyLevel.PERRA_DE_ZAREK
)

_register_role(
    ROLE_DEVOTO_ID,
    HierarchyLevel.DEVOTO
)

_register_role(
    ROLE_SIMPLE_MORTAL_ID,
    HierarchyLevel.SIMPLE_MORTAL
)

_register_role(
    ROLE_ALMA_CONDENADA_ID,
    HierarchyLevel.ALMA_CONDENADA
)

_register_role(
    ROLE_SIN_ACCESO_ID,
    HierarchyLevel.SIN_ACCESO
)


# ============================================================
# FUNCIONES PÚBLICAS
# ============================================================

def get_hierarchy_name(
    level: HierarchyLevel
) -> str:
    """
    Devuelve el nombre visible
    de una jerarquía.
    """

    return HIERARCHY_NAMES.get(
        level,
        "Desconocido"
    )


def get_hierarchy_emoji(
    level: HierarchyLevel
) -> str:
    """
    Devuelve el emoji
    asociado al rango.
    """

    return HIERARCHY_EMOJIS.get(
        level,
        "❓"
    )


def get_special_user_level(
    user_id: int
) -> HierarchyLevel | None:
    """
    Comprueba si un usuario
    posee una autoridad especial.
    """

    return SPECIAL_USER_HIERARCHY.get(
        user_id
    )


def get_role_level(
    role_id: int
) -> HierarchyLevel | None:
    """
    Obtiene la jerarquía
    correspondiente a un rol.
    """

    return ROLE_HIERARCHY.get(
        role_id
    )


# ============================================================
# RESUMEN SEGURO
# ============================================================

def get_safe_hierarchy_summary() -> dict:
    """
    Permite comprobar la configuración
    sin revelar IDs.
    """

    return {

        "creator_count":
            len(CREATOR_IDS),

        "high_command_count":
            len(HIGH_COMMAND_IDS),

        "creator_server_count":
            len(CREADOR_DEL_SERVIDOR_IDS),

        "rey_pvp_count":
            len(REY_PVP_IDS),

        "special_users":
            len(SPECIAL_USER_HIERARCHY),

        "roles_configured":
            len(ROLE_HIERARCHY),

        "levels": [
            level.name
            for level in HierarchyLevel
        ],
    }