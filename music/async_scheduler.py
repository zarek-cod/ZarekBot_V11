"""
CTX V11
Scheduler asíncrono interno de CTX Music.

Discord Voice puede ejecutar callbacks de audio
desde un hilo diferente al hilo principal de asyncio.

Este módulo permite enviar tareas de vuelta
al Event Loop principal de CTX de forma segura.

Se utilizará después para:

    canción termina
          ↓
    callback de Discord Voice
          ↓
    AsyncScheduler
          ↓
    Event Loop principal
          ↓
    reproducir siguiente canción

TODAVÍA NO:
- reproduce música
- cambia de canción automáticamente
- contiene comandos
- contiene interfaz
"""

import asyncio

from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any


# ============================================================
# EVENT LOOP PRINCIPAL
# ============================================================

_event_loop: (
    asyncio.AbstractEventLoop | None
) = None


# ============================================================
# ESTADO
# ============================================================

_initialized = False


# ============================================================
# INICIALIZAR
# ============================================================

def initialize_async_scheduler() -> None:
    """
    Guarda el Event Loop principal actualmente activo.

    IMPORTANTE:
    debe ejecutarse dentro del loop principal de CTX.
    """

    global _event_loop
    global _initialized


    try:

        loop = asyncio.get_running_loop()

    except RuntimeError as error:

        raise RuntimeError(
            "El AsyncScheduler debe inicializarse "
            "dentro de un Event Loop activo."
        ) from error


    _event_loop = loop

    _initialized = True


# ============================================================
# ¿ESTÁ INICIALIZADO?
# ============================================================

def is_async_scheduler_initialized() -> bool:

    return (
        _initialized
        and _event_loop is not None
        and not _event_loop.is_closed()
    )


# ============================================================
# OBTENER LOOP
# ============================================================

def get_music_event_loop(
) -> asyncio.AbstractEventLoop:
    """
    Obtiene el Event Loop principal.
    """

    if not is_async_scheduler_initialized():

        raise RuntimeError(
            "CTX Music AsyncScheduler "
            "todavía no está inicializado."
        )


    assert _event_loop is not None

    return _event_loop


# ============================================================
# PROGRAMAR CORRUTINA
# ============================================================

def schedule_coroutine(
    coroutine: Coroutine[
        Any,
        Any,
        Any
    ]
) -> asyncio.Task | Future:
    """
    Ejecuta una corrutina dentro del Event Loop
    principal de CTX.

    Funciona tanto si se llama:

    - desde el mismo Event Loop
    - desde otro hilo, como Discord Voice
    """

    if not is_async_scheduler_initialized():

        # Evitamos dejar una corrutina abierta
        # si el scheduler todavía no existe.
        coroutine.close()

        raise RuntimeError(
            "No se puede programar la tarea porque "
            "CTX Music AsyncScheduler no está inicializado."
        )


    loop = get_music_event_loop()


    # ========================================================
    # COMPROBAR DESDE QUÉ LOOP LLAMAMOS
    # ========================================================

    try:

        current_loop = (
            asyncio.get_running_loop()
        )

    except RuntimeError:

        current_loop = None


    # ========================================================
    # MISMO LOOP
    # ========================================================

    if current_loop is loop:

        return loop.create_task(
            coroutine
        )


    # ========================================================
    # OTRO HILO / CALLBACK DE VOZ
    # ========================================================

    return asyncio.run_coroutine_threadsafe(
        coroutine,
        loop,
    )


# ============================================================
# REINICIAR
# ============================================================

def reset_async_scheduler() -> None:
    """
    Limpia el Event Loop almacenado.

    Útil para pruebas y apagado controlado.
    """

    global _event_loop
    global _initialized


    _event_loop = None

    _initialized = False


# ============================================================
# RESUMEN SEGURO
# ============================================================

def get_async_scheduler_summary() -> dict:

    return {

        "initialized":
            _initialized,

        "event_loop_loaded":
            _event_loop is not None,

        "event_loop_closed":
            (
                _event_loop.is_closed()
                if _event_loop is not None
                else None
            ),

        "thread_safe_scheduling":
            True,
    }


# ============================================================
# PRUEBA INTERNA
# ============================================================

def run_async_scheduler_self_test() -> dict:
    """
    Prueba de desarrollo.

    NO se utilizará durante el funcionamiento
    normal del bot.
    """

    async def _test() -> dict:

        initialize_async_scheduler()


        task = schedule_coroutine(
            asyncio.sleep(
                0,
                result="CTX_OK"
            )
        )


        result = await task


        summary = (
            get_async_scheduler_summary()
        )


        return {

            "task_result":
                result,

            "initialized":
                summary["initialized"],

            "event_loop_loaded":
                summary["event_loop_loaded"],

            "thread_safe_scheduling":
                summary[
                    "thread_safe_scheduling"
                ],
        }


    try:

        return asyncio.run(
            _test()
        )

    finally:

        reset_async_scheduler()