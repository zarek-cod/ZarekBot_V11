"""
CTX V11
Controlador del sistema LOOP.

Este módulo administra el estado de repetición
musical de cada servidor.

Permite:

- activar loop
- desactivar loop
- alternar loop
- consultar su estado

POR AHORA:
solo administra el estado.

TODAVÍA NO:
- repite físicamente una canción
- contiene comandos Discord
- contiene interfaz
- decide permisos
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
class LoopResult:
    """
    Resultado de modificar LOOP.
    """

    success: bool

    enabled: bool

    changed: bool

    track: Track | None

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_loop_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_loop_lock(
    guild_id: int
) -> asyncio.Lock:
    """
    Cada servidor tiene su propio lock.

    Esto evita cambios simultáneos
    sobre LOOP.
    """

    if guild_id not in _loop_locks:

        _loop_locks[
            guild_id
        ] = asyncio.Lock()


    return _loop_locks[
        guild_id
    ]


# ============================================================
# OBTENER ESTADO
# ============================================================

def is_loop_enabled(
    guild_id: int
) -> bool:
    """
    Devuelve True si LOOP está activo.
    """

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    return (
        session.state.loop_enabled
    )


# ============================================================
# ACTIVAR LOOP
# ============================================================

async def enable_loop(
    guild_id: int
) -> LoopResult:

    lock = _get_loop_lock(
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

        if session.state.loop_enabled:

            return LoopResult(
                success=True,
                enabled=True,
                changed=False,
                track=track,
                message=(
                    "LOOP ya estaba activado."
                ),
            )


        # ====================================================
        # ACTIVAR
        # ====================================================

        session.state.enable_loop()


        return LoopResult(
            success=True,
            enabled=True,
            changed=True,
            track=track,
            message=(
                "LOOP activado."
            ),
        )


# ============================================================
# DESACTIVAR LOOP
# ============================================================

async def disable_loop(
    guild_id: int
) -> LoopResult:

    lock = _get_loop_lock(
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

        if not session.state.loop_enabled:

            return LoopResult(
                success=True,
                enabled=False,
                changed=False,
                track=track,
                message=(
                    "LOOP ya estaba desactivado."
                ),
            )


        # ====================================================
        # DESACTIVAR
        # ====================================================

        session.state.disable_loop()


        return LoopResult(
            success=True,
            enabled=False,
            changed=True,
            track=track,
            message=(
                "LOOP desactivado."
            ),
        )


# ============================================================
# ALTERNAR LOOP
# ============================================================

async def toggle_loop(
    guild_id: int
) -> LoopResult:
    """
    Si LOOP está apagado:
        lo enciende.

    Si LOOP está encendido:
        lo apaga.
    """

    lock = _get_loop_lock(
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
            session.toggle_loop()
        )


        if enabled:

            message = (
                "LOOP activado."
            )

        else:

            message = (
                "LOOP desactivado."
            )


        return LoopResult(
            success=True,
            enabled=enabled,
            changed=True,
            track=track,
            message=message,
        )


# ============================================================
# RESUMEN
# ============================================================

def get_loop_controller_summary() -> dict:

    return {

        "loop_available":
            True,

        "enable_loop":
            True,

        "disable_loop":
            True,

        "toggle_loop":
            True,

        "guild_locks":
            len(_loop_locks),

        "concurrent_loop_protection":
            True,

        # Todavía falta conectar LOOP
        # con AutoAdvance.
        "real_track_repeat":
            False,
    }