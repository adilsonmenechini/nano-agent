from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanoagent.loop.constants import (
    LoopConfig,
    Phase,
    ProgressAction,
    StopReason,
)

if TYPE_CHECKING:
    from nanoagent.loop.diagnostics import DiagnosticsCollector
    from nanoagent.loop.progress import ProgressController


@dataclass
class TurnBudget:
    max_steps: int
    remaining_steps: int
    tool_error_count: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    budget_exhausted: bool = False

    @classmethod
    def from_config(cls, config: LoopConfig) -> TurnBudget:
        return cls(
            max_steps=config.max_steps_per_turn,
            remaining_steps=config.max_steps_per_turn,
        )

    def consume_step(self) -> None:
        if self.remaining_steps > 0:
            self.remaining_steps -= 1
        if self.remaining_steps <= 0:
            self.budget_exhausted = True


@dataclass
class TurnStepPolicy:
    allow_widening: bool = True
    compact_aggressively: bool = False
    current_strategy: str = "normal"


class Turn:
    def __init__(
        self,
        config: LoopConfig,
        progress_controller: ProgressController | None = None,
        diagnostics_collector: DiagnosticsCollector | None = None,
    ) -> None:
        self._config = config
        self._phase: Phase = Phase.IDLE
        self._budget: TurnBudget = TurnBudget.from_config(config)
        self._policy: TurnStepPolicy = TurnStepPolicy()
        self._pending_prompts: deque[str] = deque()
        self._stop_reason: StopReason | None = None
        self._progress = progress_controller
        self._diagnostics = diagnostics_collector

    @property
    def current_phase(self) -> Phase:
        return self._phase

    @property
    def budget(self) -> TurnBudget:
        return self._budget

    @property
    def policy(self) -> TurnStepPolicy:
        return self._policy

    @property
    def stop_reason(self) -> StopReason | None:
        return self._stop_reason

    def start(self, prompt: str) -> StopReason:
        stripped = prompt.strip()
        if not stripped:
            self._stop_reason = StopReason.done
            return self._stop_reason

        if self._phase != Phase.IDLE:
            self._pending_prompts.append(prompt)
            return StopReason.await_user

        self._reset_turn()
        self._enter_phase(Phase.RECEIVE)
        self._enter_phase(Phase.EXPLORE)
        self._enter_phase(Phase.EXECUTE)

        self._execute_single_step()

        self._enter_phase(Phase.VERIFY)
        self._enter_phase(Phase.RESPOND)
        self._phase = Phase.IDLE

        if self._stop_reason is None:
            self._stop_reason = StopReason.done
        return self._stop_reason

    def _reset_turn(self) -> None:
        self._budget = TurnBudget.from_config(self._config)
        self._policy = TurnStepPolicy()
        self._stop_reason = None

    def _enter_phase(self, phase: Phase) -> None:
        self._phase = phase

    def _execute_single_step(self) -> None:
        if self._budget.budget_exhausted:
            self._stop_reason = StopReason.max_steps
            return

        self._budget.consume_step()
        if self._budget.budget_exhausted:
            self._stop_reason = StopReason.max_steps
            return

        if self._stop_reason is None:
            self._stop_reason = StopReason.done

    def evaluate_progress(self) -> object | None:
        if self._progress is None:
            return None
        from nanoagent.loop.progress import ProgressSignal

        signal = ProgressSignal(
            step_count=self._budget.total_tool_calls,
            tool_calls=self._budget.total_tool_calls,
            failure_ratio=self._compute_failure_ratio(),
        )
        self._progress.record_step(signal)
        decision = self._progress.evaluate()

        if self._diagnostics is not None:
            self._diagnostics.record_health(float(decision.health_score), decision.health_level.value)

        if decision.action == ProgressAction.stop:
            self._stop_reason = StopReason.error
        elif decision.action == ProgressAction.switch_strategy:
            self._policy.current_strategy = "narrowed"
        elif decision.action == ProgressAction.narrow_scope:
            self._trigger_context_compaction()
        elif decision.action == ProgressAction.request_confirmation:
            self._stop_reason = StopReason.await_user

        return decision

    def _compute_failure_ratio(self) -> float:
        total = self._budget.total_tool_calls
        if total == 0:
            return 0.0
        return self._budget.tool_error_count / total

    def _trigger_context_compaction(self) -> None:
        self._policy.compact_aggressively = True

    def queue_prompt(self, prompt: str) -> None:
        self._pending_prompts.append(prompt)

    def has_pending(self) -> bool:
        return len(self._pending_prompts) > 0

    def next_pending(self) -> str | None:
        if not self._pending_prompts:
            return None
        return self._pending_prompts.popleft()
