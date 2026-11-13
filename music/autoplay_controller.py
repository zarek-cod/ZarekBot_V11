"""
CTX V11
Controlador del sistema AUTOPLAY.

Este módulo administra el estado de reproducción
automática de cada servidor.

AUTOPLAY permitirá más adelante:

    termina la cola
          ↓
    CTX busca una canción relacionada
          ↓
    la agrega
          ↓
    continúa reproduciendo

POR AHORA:
- activar autoplay
- desactivar autoplay
- alternar autoplay
- consultar estado

TODAVÍA NO:
- busca canciones relacionadas
- reproduce recomendaciones
- contiene comandos
- contiene interfaz
"""

import asyncio

from dataclasses import dataclass

from music.session import (
    music_session_manager,
)

from music.track import Track


# ============================================================
# RESULTADO
# ============================================================

@dataclass(frozen=True)
class AutoplayResult:
    """
    Resultado de modificar AUTOPLAY.
    """

    success: bool

    enabled: bool

    changed: bool

    track: Track | None

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_autoplay_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_autoplay_lock(
    guild_id: int
) -> asyncio.Lock:
    """
    Obtiene un lock independiente
    para cada servidor.
    """

    if guild_id not in _autoplay_locks:

        _autoplay_locks[
            guild_id
        ] = asyncio.Lock()


    return _autoplay_locks[
        guild_id
    ]


# ============================================================
# CONSULTAR ESTADO
# ============================================================

def is_autoplay_enabled(
    guild_id: int
) -> bool:
    """
    Devuelve True si AUTOPLAY
    está activado en el servidor.
    """

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    return (
        session.state.autoplay_enabled
    )


# ============================================================
# ACTIVAR AUTOPLAY
# ============================================================

async def enable_autoplay(
    guild_id: int
) -> AutoplayResult:

    lock = _get_autoplay_lock(
        guild_id
    )


    async with lock:

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        track = (
            session.current_track
        )


        # ====================================================
        # YA ESTABA ACTIVO
        # ====================================================

        if session.state.autoplay_enabled:

            return AutoplayResult(
                success=True,
                enabled=True,
                changed=False,
                track=track,
                message=(
                    "AUTOPLAY ya estaba activado."
                ),
            )


        # ====================================================
        # ACTIVAR
        # ====================================================

        session.state.enable_autoplay()


        return AutoplayResult(
            success=True,
            enabled=True,
            changed=True,
            track=track,
            message=(
                "AUTOPLAY activado."
            ),
        )


# ============================================================
# DESACTIVAR AUTOPLAY
# ============================================================

async def disable_autoplay(
    guild_id: int
) -> AutoplayResult:

    lock = _get_autoplay_lock(
        guild_id
    )


    async with lock:

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        track = (
            session.current_track
        )


        # ====================================================
        # YA ESTABA DESACTIVADO
        # ====================================================

        if not session.state.autoplay_enabled:

            return AutoplayResult(
                success=True,
                enabled=False,
                changed=False,
                track=track,
                message=(
                    "AUTOPLAY ya estaba desactivado."
                ),
            )


        # ====================================================
        # DESACTIVAR
        # ====================================================

        session.state.disable_autoplay()


        return AutoplayResult(
            success=True,
            enabled=False,
            changed=True,
            track=track,
            message=(
                "AUTOPLAY desactivado."
            ),
        )


# ============================================================
# ALTERNAR AUTOPLAY
# ============================================================

async def toggle_autoplay(
    guild_id: int
) -> AutoplayResult:
    """
    Cambia automáticamente:

    OFF -> ON
    ON  -> OFF
    """

    lock = _get_autoplay_lock(
        guild_id
    )


    async with lock:

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        track = (
            session.current_track
        )


        enabled = (
            session.toggle_autoplay()
        )


        if enabled:

            message = (
                "AUTOPLAY activado."
            )

        else:

            message = (
                "AUTOPLAY desactivado."
            )


        return AutoplayResult(
            success=True,
            enabled=enabled,
            changed=True,
            track=track,
            message=message,
        )


# ============================================================
# RESUMEN
# ============================================================

def get_autoplay_controller_summary() -> dict:

    return {

        "autoplay_available":
            True,

        "enable_autoplay":
            True,

        "disable_autoplay":
            True,

        "toggle_autoplay":
            True,

        "guild_locks":
            len(_autoplay_locks),

        "concurrent_autoplay_protection":
            True,

        # Todavía no buscamos recomendaciones reales.
        "automatic_recommendations":
            False,
    }