"""Bounded duplicate protection for Discord music interactions."""

from __future__ import annotations

import time
from collections import OrderedDict


REQUEST_TTL_SECONDS = 300.0
MAX_REQUESTS = 2048

_seen: OrderedDict[str, float] = OrderedDict()


def claim_music_request(request_id: str | int | None) -> bool:
    """Return False when the same Discord request was already handled."""

    if request_id is None:
        return True

    now = time.monotonic()
    key = str(request_id)

    while _seen:
        oldest_key, oldest_time = next(iter(_seen.items()))
        if now - oldest_time <= REQUEST_TTL_SECONDS:
            break
        _seen.pop(oldest_key, None)

    if key in _seen:
        return False

    _seen[key] = now
    _seen.move_to_end(key)
    while len(_seen) > MAX_REQUESTS:
        _seen.popitem(last=False)
    return True


def reset_request_deduplicator() -> None:
    _seen.clear()
