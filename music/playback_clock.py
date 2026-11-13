"""
CTX V11
Reloj interno de reproducción para CTX Music.

Este módulo NO reproduce audio.
Solo mide el tiempo transcurrido de la canción actual.

Se usará para:
- barra de progreso
- tiempo transcurrido
- pausa / reanudación sin perder posición visual
- reinicio correcto al cambiar de canción

No modifica:
- YouTube
- FFmpeg
- cola
- permisos
- autoplay
"""

from __future__ import annotations

import time
from dataclasses import dataclass


# ============================================================
# ESTADO DE RELOJ POR SERVIDOR
# ============================================================

@dataclass
class PlaybackClockState:
    guild_id: int

    started_at: float | None = None
    paused_at: float | None = None

    paused_total: float = 0.0

    track_key: str | None = None


    # ========================================================
    # ESTADO
    # ========================================================

    @property
    def running(self) -> bool:
        return (
            self.started_at is not None
            and self.paused_at is None
        )


    @property
    def paused(self) -> bool:
        return (
            self.started_at is not None
            and self.paused_at is not None
        )


# ============================================================
# MANAGER
# ============================================================

class PlaybackClockManager:

    def __init__(self) -> None:
        self._states: dict[
            int,
            PlaybackClockState,
        ] = {}


    # ========================================================
    # OBTENER / CREAR ESTADO
    # ========================================================

    def get_state(
        self,
        guild_id: int,
    ) -> PlaybackClockState:

        state = self._states.get(
            guild_id
        )

        if state is None:
            state = PlaybackClockState(
                guild_id=guild_id
            )

            self._states[
                guild_id
            ] = state

        return state


    # ========================================================
    # CLAVE DE TRACK
    # ========================================================

    @staticmethod
    def make_track_key(
        track,
    ) -> str | None:

        if track is None:
            return None

        url = getattr(
            track,
            "url",
            None,
        )

        if url:
            return str(url)

        title = getattr(
            track,
            "title",
            None,
        )

        if title:
            return str(title)

        return None


    # ========================================================
    # INICIAR NUEVA CANCIÓN
    # ========================================================

    def start(
        self,
        guild_id: int,
        track=None,
    ) -> None:

        state = self.get_state(
            guild_id
        )

        state.started_at = (
            time.monotonic()
        )

        state.paused_at = None
        state.paused_total = 0.0

        state.track_key = (
            self.make_track_key(
                track
            )
        )


    # ========================================================
    # PAUSAR
    # ========================================================

    def pause(
        self,
        guild_id: int,
    ) -> None:

        state = self.get_state(
            guild_id
        )

        if state.started_at is None:
            return

        if state.paused_at is not None:
            return

        state.paused_at = (
            time.monotonic()
        )


    # ========================================================
    # REANUDAR
    # ========================================================

    def resume(
        self,
        guild_id: int,
    ) -> None:

        state = self.get_state(
            guild_id
        )

        if state.started_at is None:
            return

        if state.paused_at is None:
            return

        now = time.monotonic()

        state.paused_total += (
            now
            - state.paused_at
        )

        state.paused_at = None


    # ========================================================
    # DETENER / LIMPIAR
    # ========================================================

    def stop(
        self,
        guild_id: int,
    ) -> None:

        state = self.get_state(
            guild_id
        )

        state.started_at = None
        state.paused_at = None
        state.paused_total = 0.0
        state.track_key = None


    # ========================================================
    # TIEMPO TRANSCURRIDO
    # ========================================================

    def elapsed_seconds(
        self,
        guild_id: int,
    ) -> int:

        state = self.get_state(
            guild_id
        )

        if state.started_at is None:
            return 0

        reference_time = (
            state.paused_at
            if state.paused_at is not None
            else time.monotonic()
        )

        elapsed = (
            reference_time
            - state.started_at
            - state.paused_total
        )

        return max(
            0,
            int(elapsed),
        )


    # ========================================================
    # PROGRESO
    # ========================================================

    def progress_ratio(
        self,
        guild_id: int,
        duration: int | None,
    ) -> float:

        if (
            duration is None
            or duration <= 0
        ):
            return 0.0

        elapsed = self.elapsed_seconds(
            guild_id
        )

        return max(
            0.0,
            min(
                1.0,
                elapsed / duration,
            ),
        )


    # ========================================================
    # FORMATEAR SEGUNDOS
    # ========================================================

    @staticmethod
    def format_seconds(
        seconds: int,
    ) -> str:

        seconds = max(
            0,
            int(seconds),
        )

        hours, remainder = divmod(
            seconds,
            3600,
        )

        minutes, seconds = divmod(
            remainder,
            60,
        )

        if hours > 0:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )


    # ========================================================
    # BARRA VISUAL
    # ========================================================

    def build_progress_bar(
        self,
        guild_id: int,
        duration: int | None,
        *,
        width: int = 16,
    ) -> str:

        width = max(
            8,
            min(
                24,
                width,
            ),
        )

        if (
            duration is None
            or duration <= 0
        ):
            return (
                "━" * (width - 1)
                + "●"
            )

        ratio = self.progress_ratio(
            guild_id,
            duration,
        )

        position = int(
            ratio * (width - 1)
        )

        left = "━" * position
        right = "━" * (
            width - position - 1
        )

        return (
            f"{left}●{right}"
        )


    # ========================================================
    # TEXTO COMPLETO DE PROGRESO
    # ========================================================

    def progress_text(
        self,
        guild_id: int,
        duration: int | None,
    ) -> str:

        elapsed = self.elapsed_seconds(
            guild_id
        )

        elapsed_text = self.format_seconds(
            elapsed
        )

        if (
            duration is None
            or duration <= 0
        ):
            return (
                f"`{elapsed_text}` "
                f"{self.build_progress_bar(guild_id, duration)} "
                "`--:--`"
            )

        total_text = self.format_seconds(
            duration
        )

        return (
            f"`{elapsed_text}` "
            f"{self.build_progress_bar(guild_id, duration)} "
            f"`{total_text}`"
        )


    # ========================================================
    # RESUMEN
    # ========================================================

    def summary(
        self,
        guild_id: int,
    ) -> dict:

        state = self.get_state(
            guild_id
        )

        return {
            "guild_id":
                guild_id,

            "running":
                state.running,

            "paused":
                state.paused,

            "elapsed_seconds":
                self.elapsed_seconds(
                    guild_id
                ),

            "track_key":
                state.track_key,
        }


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

playback_clock_manager = (
    PlaybackClockManager()
)
