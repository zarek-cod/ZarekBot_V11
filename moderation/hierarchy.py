"""
CTX V11
Resolver de jerarquía para miembros de Discord.

Este módulo NO define los rangos.
Los rangos oficiales están en:

    config/hierarchy.py

Aquí únicamente analizamos a un miembro real de Discord
y determinamos qué autoridad posee.
"""

from dataclasses import dataclass

import discord

from config.hierarchy import (
    HierarchyLevel,
    get_hierarchy_emoji,
    get_hierarchy_name,
    get_role_level,
    get_special_user_level,
)


# ============================================================
# RESULTADO DE JERARQUÍA
# ============================================================

@dataclass(frozen=True)
class MemberHierarchy:
    """
    Información final de jerarquía de un miembro.
    """

    user_id: int

    level: HierarchyLevel

    name: str

    emoji: str

    source: str

    role_id: int | None = None


# ============================================================
# RANGO PREDETERMINADO
# ============================================================

DEFAULT_HIERARCHY = HierarchyLevel.SIMPLE_MORTAL


# ============================================================
# RESOLVER JERARQUÍA
# ============================================================

def resolve_member_hierarchy(
    member: discord.Member
) -> MemberHierarchy:
    """
    Determina el rango real de un miembro.

    Prioridad:

    1. Autoridad especial por ID de usuario.
    2. Rol con jerarquía más alta.
    3. Simple Mortal si no tiene ningún rango conocido.
    """

    # --------------------------------------------------------
    # 1. USUARIOS ESPECIALES
    # --------------------------------------------------------

    special_level = get_special_user_level(
        member.id
    )

    if special_level is not None:

        return MemberHierarchy(
            user_id=member.id,
            level=special_level,
            name=get_hierarchy_name(
                special_level
            ),
            emoji=get_hierarchy_emoji(
                special_level
            ),
            source="special_user",
            role_id=None,
        )


    # --------------------------------------------------------
    # 2. BUSCAR EL ROL DE MAYOR JERARQUÍA
    # --------------------------------------------------------

    highest_level: HierarchyLevel | None = None

    highest_role_id: int | None = None


    for role in member.roles:

        role_level = get_role_level(
            role.id
        )

        if role_level is None:
            continue


        if (
            highest_level is None
            or role_level > highest_level
        ):

            highest_level = role_level

            highest_role_id = role.id


    # --------------------------------------------------------
    # 3. SI TIENE ALGÚN ROL DE JERARQUÍA
    # --------------------------------------------------------

    if highest_level is not None:

        return MemberHierarchy(
            user_id=member.id,
            level=highest_level,
            name=get_hierarchy_name(
                highest_level
            ),
            emoji=get_hierarchy_emoji(
                highest_level
            ),
            source="role",
            role_id=highest_role_id,
        )


    # --------------------------------------------------------
    # 4. SIN ROL CONOCIDO
    # --------------------------------------------------------

    return MemberHierarchy(
        user_id=member.id,
        level=DEFAULT_HIERARCHY,
        name=get_hierarchy_name(
            DEFAULT_HIERARCHY
        ),
        emoji=get_hierarchy_emoji(
            DEFAULT_HIERARCHY
        ),
        source="default",
        role_id=None,
    )


# ============================================================
# COMPARAR DOS USUARIOS
# ============================================================

def compare_members(
    first: discord.Member,
    second: discord.Member
) -> int:
    """
    Compara la autoridad de dos miembros.

    Devuelve:

        1  -> first tiene mayor autoridad
        0  -> tienen la misma autoridad
       -1  -> second tiene mayor autoridad
    """

    first_rank = resolve_member_hierarchy(
        first
    )

    second_rank = resolve_member_hierarchy(
        second
    )


    if first_rank.level > second_rank.level:
        return 1


    if first_rank.level < second_rank.level:
        return -1


    return 0


# ============================================================
# ¿PUEDE CONTROLAR A OTRO USUARIO?
# ============================================================

def can_control_member(
    actor: discord.Member,
    target: discord.Member
) -> bool:
    """
    Determina si actor posee autoridad superior
    sobre target.

    Un usuario no puede controlar a alguien
    de su mismo nivel ni superior.
    """

    actor_rank = resolve_member_hierarchy(
        actor
    )

    target_rank = resolve_member_hierarchy(
        target
    )


    return (
        actor_rank.level
        > target_rank.level
    )


# ============================================================
# ¿ES AUTORIDAD?
# ============================================================

def is_authority(
    member: discord.Member
) -> bool:
    """
    Consideramos autoridad desde Supervisor hacia arriba.
    """

    rank = resolve_member_hierarchy(
        member
    )

    return (
        rank.level
        >= HierarchyLevel.SUPERVISOR
    )


# ============================================================
# ¿ES AUTORIDAD ABSOLUTA?
# ============================================================

def is_absolute_authority(
    member: discord.Member
) -> bool:
    """
    Autoridades especiales superiores.
    """

    rank = resolve_member_hierarchy(
        member
    )

    return rank.level in {

        HierarchyLevel.CREADOR,

        HierarchyLevel.ALTO_MANDO,

        HierarchyLevel.CREADOR_DEL_SERVIDOR,

        HierarchyLevel.REY_PVP,
    }


# ============================================================
# INFORMACIÓN SEGURA PARA LOGS
# ============================================================

def get_member_hierarchy_summary(
    member: discord.Member
) -> dict:
    """
    Información útil para depuración.

    No muestra tokens ni configuraciones privadas.
    """

    rank = resolve_member_hierarchy(
        member
    )


    return {

        "user_id":
            member.id,

        "display_name":
            member.display_name,

        "hierarchy":
            rank.name,

        "level":
            int(rank.level),

        "source":
            rank.source,

        "role_detected":
            rank.role_id is not None,
    }