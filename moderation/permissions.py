"""
CTX V11
Sistema central de permisos especiales.

Jerarquía administrativa:

1. Zarek   -> CREADOR
2. Centi   -> CREADOR DEL SERVIDOR
3. Jhilmar -> REY PVP
4. Resto   -> sin poderes administrativos

Los roles normales del servidor NO obtienen poderes
administrativos solamente por su nombre o nivel.
"""

from dataclasses import dataclass
from enum import Enum

import discord

from config.hierarchy import HierarchyLevel
from moderation.hierarchy import resolve_member_hierarchy


# ============================================================
# ACCIONES DE CTX
# ============================================================

class PermissionAction(str, Enum):

    # IA NORMAL
    AI_CHAT = "ai_chat"
    AI_IMAGE = "ai_image"

    # MÚSICA
    MUSIC_PLAY = "music_play"
    MUSIC_PAUSE = "music_pause"
    MUSIC_RESUME = "music_resume"
    MUSIC_SKIP = "music_skip"
    MUSIC_STOP = "music_stop"
    MUSIC_QUEUE = "music_queue"
    MUSIC_VOLUME = "music_volume"

    # MODERACIÓN
    MODERATION_MUTE = "moderation_mute"
    MODERATION_UNMUTE = "moderation_unmute"
    MODERATION_KICK = "moderation_kick"
    MODERATION_BAN = "moderation_ban"

    # CONTROL SUPERIOR
    SERVER_CONTROL = "server_control"


# ============================================================
# RESULTADO
# ============================================================

@dataclass(frozen=True)
class PermissionResult:

    allowed: bool

    action: PermissionAction

    user_level: HierarchyLevel

    reason: str


# ============================================================
# NIVELES ESPECIALES
# ============================================================

ZAREK_LEVEL = HierarchyLevel.CREADOR

CENTI_LEVEL = HierarchyLevel.CREADOR_DEL_SERVIDOR

JHILMAR_LEVEL = HierarchyLevel.REY_PVP


# ============================================================
# IDENTIFICACIÓN DE AUTORIDADES
# ============================================================

def is_zarek(
    member: discord.Member
) -> bool:

    hierarchy = resolve_member_hierarchy(
        member
    )

    return (
        hierarchy.level
        == ZAREK_LEVEL
    )


def is_centi(
    member: discord.Member
) -> bool:

    hierarchy = resolve_member_hierarchy(
        member
    )

    return (
        hierarchy.level
        == CENTI_LEVEL
    )


def is_jhilmar(
    member: discord.Member
) -> bool:

    hierarchy = resolve_member_hierarchy(
        member
    )

    return (
        hierarchy.level
        == JHILMAR_LEVEL
    )


# ============================================================
# PERMISOS DE IA
# ============================================================

def can_use_ai(
    member: discord.Member
) -> bool:
    """
    Por ahora cualquier miembro normal puede hablar con CTX.

    Más adelante podremos bloquear SIN ACCESO,
    castigados, usuarios específicos, etc.
    """

    hierarchy = resolve_member_hierarchy(
        member
    )

    return (
        hierarchy.level
        != HierarchyLevel.SIN_ACCESO
    )


# ============================================================
# PERMISOS DE MÚSICA
# ============================================================

def can_control_music(
    member: discord.Member
) -> bool:
    """
    ÚNICAMENTE:

    Zarek
    Centi

    pueden controlar el sistema musical.
    """

    hierarchy = resolve_member_hierarchy(
        member
    )

    return hierarchy.level in {

        ZAREK_LEVEL,

        CENTI_LEVEL,
    }


# ============================================================
# PERMISOS DE MODERACIÓN
# ============================================================

def can_use_moderation(
    member: discord.Member
) -> bool:
    """
    Únicamente las tres autoridades principales
    pueden utilizar moderación.
    """

    hierarchy = resolve_member_hierarchy(
        member
    )

    return hierarchy.level in {

        ZAREK_LEVEL,

        CENTI_LEVEL,

        JHILMAR_LEVEL,
    }


# ============================================================
# REGLAS ENTRE USUARIOS
# ============================================================

def can_act_on_member(
    actor: discord.Member,
    target: discord.Member
) -> bool:
    """
    Reglas absolutas:

    Zarek:
        puede actuar contra cualquiera.

    Centi:
        puede actuar contra cualquiera MENOS Zarek.

    Jhilmar:
        puede actuar contra cualquiera MENOS
        Zarek y Centi.

    Resto:
        no puede actuar contra nadie.
    """

    # Nadie puede castigarse a sí mismo
    if actor.id == target.id:
        return False


    actor_rank = resolve_member_hierarchy(
        actor
    )

    target_rank = resolve_member_hierarchy(
        target
    )


    # --------------------------------------------------------
    # ZAREK
    # --------------------------------------------------------

    if actor_rank.level == ZAREK_LEVEL:

        return True


    # --------------------------------------------------------
    # CENTI
    # --------------------------------------------------------

    if actor_rank.level == CENTI_LEVEL:

        # Zarek está protegido
        if target_rank.level == ZAREK_LEVEL:
            return False

        return True


    # --------------------------------------------------------
    # JHILMAR
    # --------------------------------------------------------

    if actor_rank.level == JHILMAR_LEVEL:

        # Zarek y Centi están protegidos
        if target_rank.level in {

            ZAREK_LEVEL,

            CENTI_LEVEL,

        }:
            return False


        # También impedimos atacar
        # autoridades iguales o superiores.
        return (
            target_rank.level
            < JHILMAR_LEVEL
        )


    # --------------------------------------------------------
    # RESTO
    # --------------------------------------------------------

    return False


# ============================================================
# SILENCIAR
# ============================================================

def can_mute_member(
    actor: discord.Member,
    target: discord.Member
) -> bool:

    if not can_use_moderation(
        actor
    ):
        return False


    return can_act_on_member(
        actor,
        target
    )


# ============================================================
# CONTROL TOTAL DEL SERVIDOR
# ============================================================

def has_server_control(
    member: discord.Member
) -> bool:
    """
    Control total reservado para Zarek.

    Centi tendrá muchas funciones administrativas,
    pero Zarek continúa siendo la autoridad máxima.
    """

    return is_zarek(
        member
    )


# ============================================================
# COMPROBAR ACCIÓN
# ============================================================

def check_permission(
    member: discord.Member,
    action: PermissionAction
) -> PermissionResult:

    hierarchy = resolve_member_hierarchy(
        member
    )


    # --------------------------------------------------------
    # IA
    # --------------------------------------------------------

    if action in {

        PermissionAction.AI_CHAT,

        PermissionAction.AI_IMAGE,

    }:

        allowed = can_use_ai(
            member
        )


    # --------------------------------------------------------
    # MÚSICA
    # --------------------------------------------------------

    elif action in {

        PermissionAction.MUSIC_PLAY,

        PermissionAction.MUSIC_PAUSE,

        PermissionAction.MUSIC_RESUME,

        PermissionAction.MUSIC_SKIP,

        PermissionAction.MUSIC_STOP,

        PermissionAction.MUSIC_QUEUE,

        PermissionAction.MUSIC_VOLUME,

    }:

        allowed = can_control_music(
            member
        )


    # --------------------------------------------------------
    # MODERACIÓN
    # --------------------------------------------------------

    elif action in {

        PermissionAction.MODERATION_MUTE,

        PermissionAction.MODERATION_UNMUTE,

        PermissionAction.MODERATION_KICK,

        PermissionAction.MODERATION_BAN,

    }:

        allowed = can_use_moderation(
            member
        )


    # --------------------------------------------------------
    # CONTROL DEL SERVIDOR
    # --------------------------------------------------------

    elif action == PermissionAction.SERVER_CONTROL:

        allowed = has_server_control(
            member
        )


    else:

        allowed = False


    if allowed:

        reason = (
            f"{hierarchy.name} tiene permiso "
            f"para {action.value}."
        )

    else:

        reason = (
            f"{hierarchy.name} no tiene permiso "
            f"para {action.value}."
        )


    return PermissionResult(

        allowed=allowed,

        action=action,

        user_level=hierarchy.level,

        reason=reason,
    )


# ============================================================
# ACCESO SIMPLE
# ============================================================

def has_permission(
    member: discord.Member,
    action: PermissionAction
) -> bool:

    return check_permission(
        member,
        action
    ).allowed


# ============================================================
# RESUMEN
# ============================================================

def get_permission_summary() -> dict:

    return {

        "zarek": {
            "music": True,
            "moderation": True,
            "server_control": True,
            "can_act_on_everyone": True,
        },

        "centi": {
            "music": True,
            "moderation": True,
            "server_control": False,
            "can_act_on_zarek": False,
        },

        "jhilmar": {
            "music": False,
            "moderation": True,
            "server_control": False,
            "can_act_on_zarek": False,
            "can_act_on_centi": False,
        },

        "others": {
            "music": False,
            "moderation": False,
            "server_control": False,
        },
    }