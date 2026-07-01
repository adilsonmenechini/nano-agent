from __future__ import annotations

import time
import uuid

from nanoagent.learning import CycleResult
from nanoagent.learning.reflector import Reflector
from nanoagent.learning.experience import ExperienceEngine
from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore


class BackgroundLearner:
    def __init__(
        self,
        store: SQLiteMemoryStore,
        enabled: bool = False,
        cycle_interval_turns: int = 10,
        cycle_interval_seconds: int = 3600,
        max_cycle_duration_ms: int = 5000,
    ):
        self.store = store
        self.enabled = enabled
        self.cycle_interval_turns = cycle_interval_turns
        self.cycle_interval_seconds = cycle_interval_seconds
        self.max_cycle_duration_ms = max_cycle_duration_ms
        self._last_cycle_turn: int = 0
        self._last_cycle_time: float = 0.0

    def start_if_due(self, current_turn_count: int) -> bool:
        if not self.enabled:
            return False
        turn_delta = current_turn_count - self._last_cycle_turn
        time_delta = time.time() - self._last_cycle_time
        if (
            turn_delta >= self.cycle_interval_turns
            or time_delta >= self.cycle_interval_seconds
        ):
            return True
        return False

    def execute_cycle(self, reflections: list[dict] | None = None) -> CycleResult:
        start = time.time()
        cycle_id = uuid.uuid4().hex[:12]
        errors = []

        reflector = Reflector(self.store)
        if reflections is None:
            reflections = reflector.get_recent(limit=100)

        engine = ExperienceEngine(self.store)
        try:
            patterns = engine.analyze_reflections(reflections)
        except Exception as e:
            patterns = []
            errors.append(f"analyze_reflections failed: {e}")

        proposals_created = 0
        if patterns:
            try:
                from nanoagent.learning.synthesizer import Synthesizer

                synthesizer = Synthesizer(self.store)
                proposals_created = len(synthesizer.check_for_proposals())
            except Exception:
                pass

        duration_ms = int((time.time() - start) * 1000)
        self._last_cycle_turn = len(reflections)
        self._last_cycle_time = time.time()

        return CycleResult(
            cycle_id=cycle_id,
            turn_count=len(reflections),
            patterns_found=len(patterns),
            proposals_created=proposals_created,
            errors=errors,
            duration_ms=duration_ms,
        )

    def get_last_cycle(self) -> float:
        return self._last_cycle_time
