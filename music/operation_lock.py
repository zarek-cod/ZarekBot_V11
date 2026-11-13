"""Shared per-guild locks for state-changing music operations."""

from __future__ import annotations

import asyncio


_guild_operation_locks: dict[int, asyncio.Lock] = {}


def get_guild_operation_lock(guild_id: int) -> asyncio.Lock:
    """Return the lock that serializes playback state transitions for a guild."""

    lock = _guild_operation_locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        _guild_operation_locks[guild_id] = lock
    return lock


def operation_lock_count() -> int:
    return len(_guild_operation_locks)


def reset_operation_locks() -> None:
    """Clear lock references during tests or a controlled runtime reset."""

    _guild_operation_locks.clear()
