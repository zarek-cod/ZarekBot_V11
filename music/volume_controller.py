"""
CTX V11
Controlador seguro de VOLUMEN.

Mantiene sincronizados:

- MusicSession
- Backend de reproducción

El volumen permitido es:

    0%   -> silencio
    100% -> máximo

NO:
- contiene comandos Discord
- contiene interfaz
- decide permisos
- busca canciones
"""

import asyncio

from dataclasses import dataclass

from music.backend_manager import (
    playback_backend_manager,
)

from music.session import (
    music_session_manager,
)

from music.track import Track


# ============================================================
# RESULTADO
# ============================================================

@dataclass(frozen=True)
class VolumeResult:
    """
    Resultado de cambiar el volumen.
    """

    success: bool

    requested_volume: int

    final_volume: int

    track: Track | None

    message: str


# ============================================================
# LOCKS POR SERVIDOR
# ============================================================

_volume_locks: dict[
    int,
    asyncio.Lock
] = {}


def _get_volume_lock(
    guild_id: int
) -> asyncio.Lock:
    """
    Cada servidor tiene su propio lock.

    Evita dos cambios de volumen
    exactamente al mismo tiempo.
    """

    if guild_id not in _volume_locks:

        _volume_locks[
            guild_id
        ] = asyncio.Lock()


    return _volume_locks[
        guild_id
    ]


# ============================================================
# CAMBIAR VOLUMEN
# ============================================================

async def set_music_volume(
    guild_id: int,
    volume: int
) -> VolumeResult:
    """
    Cambia el volumen de CTX Music.

    Valores menores de 0:
        se convierten en 0.

    Valores mayores de 100:
        se convierten en 100.
    """

    lock = _get_volume_lock(
        guild_id
    )


    async with lock:

        # ====================================================
        # SESIÓN
        # ====================================================

        session = (
            music_session_manager.get_session(
                guild_id
            )
        )


        # ====================================================
        # GUARDAR VALOR SOLICITADO
        # ====================================================

        requested_volume = volume


        # ====================================================
        # NORMALIZAR MEDIANTE LA SESIÓN
        # ====================================================

        final_volume = (
            session.set_volume(
                volume
            )
        )


        # ====================================================
        # BACKEND
        # ====================================================

        try:

            backend = (
                playback_backend_manager.get_backend(
                    guild_id
                )
            )

        except Exception as error:

            return VolumeResult(
                success=False,
                requested_volume=requested_volume,
                final_volume=final_volume,
                track=session.current_track,
                message=(
                    "El volumen lógico fue actualizado, "
                    "pero CTX no pudo obtener el backend: "
                    f"{error}"
                ),
            )


        # ====================================================
        # ACTUALIZAR BACKEND
        # ====================================================

        try:

            backend_result = (
                await backend.set_volume(
                    final_volume
                )
            )

        except Exception as error:

            return VolumeResult(
                success=False,
                requested_volume=requested_volume,
                final_volume=final_volume,
                track=session.current_track,
                message=(
                    "El volumen lógico fue actualizado, "
                    "pero no pudo aplicarse al audio: "
                    f"{error}"
                ),
            )


        # ====================================================
        # BACKEND RECHAZÓ CAMBIO
        # ====================================================

        if not backend_result.success:

            return VolumeResult(
                success=False,
                requested_volume=requested_volume,
                final_volume=final_volume,
                track=session.current_track,
                message=backend_result.message,
            )


        # ====================================================
        # ÉXITO
        # ====================================================

        return VolumeResult(
            success=True,
            requested_volume=requested_volume,
            final_volume=final_volume,
            track=session.current_track,
            message=(
                f"Volumen de CTX Music "
                f"establecido en {final_volume}%."
            ),
        )


# ============================================================
# OBTENER VOLUMEN
# ============================================================

def get_music_volume(
    guild_id: int
) -> int:
    """
    Devuelve el volumen actual
    del servidor.
    """

    session = (
        music_session_manager.get_session(
            guild_id
        )
    )


    return session.state.volume


# ============================================================
# RESUMEN
# ============================================================

def get_volume_controller_summary() -> dict:

    return {

        "volume_available":
            True,

        "minimum_volume":
            0,

        "maximum_volume":
            100,

        "guild_locks":
            len(_volume_locks),

        "concurrent_volume_protection":
            True,

        "session_sync":
            True,

        "backend_sync":
            True,

        "realtime_volume_change":
            True,
    }