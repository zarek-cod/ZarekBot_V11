"""
CTX V11
Permisos específicos del sistema musical.

Este archivo NO reproduce música.
Solamente determina quién puede utilizar
y controlar CTX Music.

REGLAS:

- TODOS LOS MIEMBROS REALES:
    Pueden buscar canciones y agregarlas
    a la cola musical compartida.

- ZAREK:
    Control musical absoluto.

- CENTI:
    Control musical completo.

- JHILMAR:
    Puede solicitar canciones,
    pero NO controlar el reproductor.

- RESTO:
    Puede solicitar canciones,
    pero NO controlar el reproductor.

- BOTS:
    No pueden solicitar ni controlar música.
"""

import discord

from config.hierarchy import HierarchyLevel
from moderation.hierarchy import resolve_member_hierarchy


# ============================================================
# AUTORIDADES MUSICALES
# ============================================================

MUSIC_ADMIN_LEVELS = {

    HierarchyLevel.CREADOR,

    HierarchyLevel.CREADOR_DEL_SERVIDOR,
}


# ============================================================
# MIEMBRO REAL
# ============================================================

def is_real_music_member(
    member: discord.Member
) -> bool:
    """
    Permite usuarios reales del servidor
    y bloquea cuentas bot.
    """

    return (
        isinstance(
            member,
            discord.Member
        )
        and not member.bot
    )


# ============================================================
# COMPROBAR SI ES ADMINISTRADOR DE MÚSICA
# ============================================================

def can_manage_music(
    member: discord.Member
) -> bool:
    """
    Solamente Zarek y Centi tienen
    control total sobre CTX Music.
    """

    if not is_real_music_member(
        member
    ):
        return False

    hierarchy = resolve_member_hierarchy(
        member
    )

    return (
        hierarchy.level
        in MUSIC_ADMIN_LEVELS
    )


# ============================================================
# SOLICITAR / PONER MÚSICA
# ============================================================

def can_request_music(
    member: discord.Member
) -> bool:
    """
    Cualquier miembro real del servidor
    puede solicitar canciones.

    Todas las canciones se agregan a la
    misma cola musical del servidor.
    """

    return is_real_music_member(
        member
    )


# ============================================================
# PLAY
# ============================================================

def can_play(
    member: discord.Member
) -> bool:
    """
    Cualquier miembro real del servidor
    puede usar PLAY para buscar canciones
    y agregarlas a la cola compartida.
    """

    return is_real_music_member(
        member
    )


# ============================================================
# PAUSE
# ============================================================

def can_pause(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden pausar la música.
    """

    return can_manage_music(
        member
    )


# ============================================================
# RESUME
# ============================================================

def can_resume(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden continuar la música pausada.
    """

    return can_manage_music(
        member
    )


# ============================================================
# SKIP
# ============================================================

def can_skip(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden saltar canciones.
    """

    return can_manage_music(
        member
    )


# ============================================================
# STOP
# ============================================================

def can_stop(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden detener completamente la música.
    """

    return can_manage_music(
        member
    )


# ============================================================
# VOLUMEN
# ============================================================

def can_change_volume(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden cambiar el volumen.
    """

    return can_manage_music(
        member
    )


# ============================================================
# LIMPIAR COLA
# ============================================================

def can_clear_queue(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden borrar toda la cola.
    """

    return can_manage_music(
        member
    )


# ============================================================
# REORDENAR COLA
# ============================================================

def can_reorder_queue(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden cambiar el orden de la cola.
    """

    return can_manage_music(
        member
    )


# ============================================================
# QUITAR CANCIÓN DE LA COLA
# ============================================================

def can_remove_track(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden quitar canciones de la cola.
    """

    return can_manage_music(
        member
    )


# ============================================================
# LOOP / REPETICIÓN
# ============================================================

def can_change_loop(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden activar o desactivar LOOP.
    """

    return can_manage_music(
        member
    )


# ============================================================
# AUTOPLAY
# ============================================================

def can_change_autoplay(
    member: discord.Member
) -> bool:
    """
    Solo administradores musicales
    pueden activar o desactivar AUTOPLAY.
    """

    return can_manage_music(
        member
    )


# ============================================================
# RESUMEN SEGURO
# ============================================================

def get_music_permission_summary() -> dict:
    """
    Resumen de permisos musicales.

    No muestra IDs privados.
    """

    return {

        "request_music": {
            "zarek": True,
            "centi": True,
            "jhilmar": True,
            "others": True,
        },

        "play": {
            "zarek": True,
            "centi": True,
            "jhilmar": True,
            "others": True,
        },

        "control_global": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "pause": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "resume": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "skip": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "stop": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "volume": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "clear_queue": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "reorder_queue": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "remove_track": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "loop": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "autoplay": {
            "zarek": True,
            "centi": True,
            "jhilmar": False,
            "others": False,
        },

        "bots": {
            "request_music": False,
            "play": False,
            "control": False,
        },
    }
