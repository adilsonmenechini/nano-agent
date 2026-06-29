import pytest
from nanoagent.loop.constants import HealthLevel, LoopConfig, ProgressAction
from nanoagent.loop.progress import ProgressController, ProgressDecision, ProgressSignal


class TestProgressSignal:
    def test_defaults(self):
        signal = ProgressSignal()
        assert signal.step_count == 0
        assert signal.completion_ratio == 0.0
        assert signal.failure_ratio == 0.0


class TestProgressDecision:
    def test_defaults(self):
        d = ProgressDecision()
        assert d.action == ProgressAction.continue_
        assert d.health_level == HealthLevel.healthy
        assert d.health_score == 1.0


class TestProgressController:
    def test_evaluate_with_no_data(self):
        controller = ProgressController(LoopConfig())
        decision = controller.evaluate()
        assert decision.action == ProgressAction.continue_
        assert decision.health_level == HealthLevel.healthy

    def test_healthy_evaluation(self):
        controller = ProgressController(LoopConfig())
        for i in range(5):
            signal = ProgressSignal(
                step_count=i,
                completion_ratio=0.2 * (i + 1),
                failure_ratio=0.0,
                tool_calls=1,
                output_changes=1,
                elapsed_seconds=0.5,
                error_rate_window=0.0,
                oscillation_index=0.0,
                context_usage_ratio=0.1,
            )
            controller.record_step(signal)
        decision = controller.evaluate()
        assert decision.health_level == HealthLevel.healthy
        assert decision.health_score >= 0.80

    def test_degraded_health_on_high_failure(self):
        controller = ProgressController(LoopConfig())
        for i in range(5):
            signal = ProgressSignal(
                step_count=i,
                completion_ratio=0.0,
                failure_ratio=0.8,
                tool_calls=5,
                output_changes=0,
                elapsed_seconds=5.0,
                error_rate_window=0.8,
                oscillation_index=0.5,
                context_usage_ratio=0.9,
            )
            controller.record_step(signal)
        decision = controller.evaluate()
        assert decision.health_score < 0.80

    def test_stall_detection(self):
        controller = ProgressController(LoopConfig(stall_threshold=3))
        for i in range(5):
            signal = ProgressSignal(
                step_count=i,
                completion_ratio=0.0,
                failure_ratio=0.0,
                tool_calls=i,
                output_changes=0,
                elapsed_seconds=float(i),
                error_rate_window=0.0,
                oscillation_index=0.0,
                context_usage_ratio=0.1,
            )
            controller.record_step(signal)
        decision = controller.evaluate()
        assert decision.stall_score >= 0.8

    def test_oscillation_detection(self):
        controller = ProgressController(LoopConfig(oscillation_window=3))
        for i in range(5):
            signal = ProgressSignal(
                step_count=i,
                completion_ratio=0.0,
                failure_ratio=0.0,
                tool_calls=1,
                output_changes=0,
                elapsed_seconds=float(i),
                error_rate_window=0.0,
                oscillation_index=0.0,
                context_usage_ratio=0.1,
            )
            controller.record_step(signal)
        decision = controller.evaluate()
        assert decision.oscillation_score >= 0.8

    def test_reset_clears_window(self):
        controller = ProgressController(LoopConfig())
        signal = ProgressSignal(failure_ratio=0.5, error_rate_window=0.3)
        controller.record_step(signal)
        assert controller.evaluate().health_score < 1.0
        controller.reset()
        assert controller.evaluate().health_score == 1.0

    def test_stop_on_critical(self):
        controller = ProgressController(LoopConfig())
        signal = ProgressSignal(
            failure_ratio=1.0,
            error_rate_window=1.0,
            context_usage_ratio=1.0,
            oscillation_index=1.0,
            tool_calls=0,
            output_changes=0,
        )
        controller.record_step(signal)
        decision = controller.evaluate()
        assert decision.action == ProgressAction.stop

    def test_narrow_scope_on_warning(self):
        controller = ProgressController(LoopConfig())
        signal = ProgressSignal(
            failure_ratio=0.5,
            error_rate_window=0.3,
            context_usage_ratio=0.8,
            oscillation_index=0.2,
            tool_calls=1,
            output_changes=1,
        )
        controller.record_step(signal)
        decision = controller.evaluate()
        assert decision.health_level in (HealthLevel.warning, HealthLevel.degraded)
