from __future__ import annotations

import time


_DECAY_HALF_LIFE = 86400 * 7  # 7 days


def compute_importance(
    access_count: int,
    last_access: float,
    now: float | None = None,
    half_life: float = _DECAY_HALF_LIFE,
) -> float:
    if now is None:
        now = time.time()
    # Recency factor: exponential decay from last access
    age = max(0.0, now - last_access)
    recency = 2.0 ** (-age / half_life)
    # Frequency factor: saturating at ~20 accesses
    freq = 1.0 - 1.0 / (1.0 + access_count * 0.1)
    score = 0.4 * recency + 0.6 * freq
    return max(0.0, min(1.0, score))


def decay_importance(
    current: float,
    elapsed: float,
    half_life: float = _DECAY_HALF_LIFE,
) -> float:
    factor = 2.0 ** (-elapsed / half_life)
    return max(0.0, current * factor)
