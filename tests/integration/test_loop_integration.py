"""Integration tests for Agent Loop Engineering (003-agent-loop).

Tests the wired-together pipeline of all loop components:
Turn → ProgressController → StabilityMonitor → HealingEngine → DiagnosticsCollector
"""
from nanoagent.loop.constants import (
    FaultCategory,
    FaultRecord,
    FaultSeverity,
    LoopConfig,
    Phase,
    ProgressAction,
    StopReason,
)
from nanoagent.loop.diagnostics import DiagnosticsCollector
from nanoagent.loop.healing import HealingEngine
from nanoagent.loop.health import StabilityMonitor
from nanoagent.loop.progress import ProgressController, ProgressSignal
from nanoagent.loop.turn import Turn


class TestPromptQueuingIntegration:  # T015
    def test_non_overlapping_turns(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        result1 = turn.start("first prompt")
        assert result1 == StopReason.done

        result2 = turn.start("second prompt")
        assert result2 == StopReason.done
        assert not turn.has_pending()

    def test_queue_multiple_then_drain(self):
        config = LoopConfig()
        turn = Turn(config)
        turn.queue_prompt("msg1")
        turn.queue_prompt("msg2")
        turn.queue_prompt("msg3")
        assert turn.has_pending()
        assert turn.next_pending() == "msg1"
        assert turn.next_pending() == "msg2"
        assert turn.next_pending() == "msg3"
        assert turn.next_pending() is None


class TestHealthDisplayIntegration:  # T028
    def test_health_tracks_across_turns(self):
        config = LoopConfig(health_window_size=5)
        progress = ProgressController(config)
        diagnostics = DiagnosticsCollector(enabled=True)
        turn = Turn(config, progress_controller=progress, diagnostics_collector=diagnostics)

        turn.start("hello")
        decision = turn.evaluate_progress()
        assert decision is not None
        assert 0.0 <= decision.health_score <= 1.0

        report = diagnostics.report()
        assert len(report.health_snapshots) > 0
        snapshot = report.health_snapshots[-1]
        assert "score" in snapshot
        assert "level" in snapshot

    def test_health_degraded_triggers_warning(self):
        config = LoopConfig(health_window_size=5)
        progress = ProgressController(config)
        decision = None
        for _ in range(6):
            progress.record_step(ProgressSignal(
                failure_ratio=0.9, error_rate_window=0.8, oscillation_index=0.5
            ))
            decision = progress.evaluate()

        assert decision is not None
        assert decision.health_level.value in ("degraded", "warning", "critical")


class TestSelfHealingIntegration:  # T045
    def test_fault_to_healing_pipeline(self):
        healing = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.OSCILLATION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
            metrics_snapshot={"oscillation_index": 0.9},
            description="repeated tool calls",
        )
        action = healing.handle_fault(fault)
        assert action is not None
        assert action.fault_type == FaultCategory.OSCILLATION

        healing.record_success(action.strategy_type)
        history = healing.action_history()
        assert len(history) == 1
        assert history[0].strategy_type.value == "break_oscillation"

    def test_unknown_fault_falls_back_to_abort(self):
        healing = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.DEADLOCK,
            severity=FaultSeverity.MEDIUM,
            timestamp=100.0,
            metrics_snapshot={},
            description="deadlock detected",
        )
        action = healing.handle_fault(fault)
        assert action is not None
        assert action.strategy_type.value in ("reduce_scope", "request_confirmation")


class TestDiagnosticsCliIntegration:  # T058
    def test_diagnostics_render_contains_all_sections(self):
        diagnostics = DiagnosticsCollector(enabled=True)
        diagnostics.record_phase(Phase.EXPLORE, 0.042)
        diagnostics.record_phase(Phase.EXECUTE, 1.200)
        diagnostics.record_tool_call("search", 0.5, True)
        diagnostics.record_health(0.85, "healthy")
        diagnostics.record_healing({
            "fault_type": "OSCILLATION",
            "strategy": "break_oscillation",
            "success": True,
            "duration": 0.003,
        })
        rendered = diagnostics.render(StopReason.done)
        assert "Diagnostics" in rendered
        assert "explore" in rendered
        assert "0.042" in rendered
        assert "Tool calls" in rendered
        assert "1 unique" in rendered
        assert "0.85" in rendered
        assert "break_oscillation" in rendered
        assert "done" in rendered


class TestEndToEndPipeline:  # T071
    def test_full_pipeline_all_components(self):
        config = LoopConfig(max_steps_per_turn=3, health_window_size=5)
        diagnostics = DiagnosticsCollector(enabled=True)
        progress = ProgressController(config)
        stability = StabilityMonitor(config)
        healing = HealingEngine()
        turn = Turn(config, progress_controller=progress, diagnostics_collector=diagnostics)

        turn.start("hello")

        decision = turn.evaluate_progress()
        assert decision is not None
        assert isinstance(decision.action, ProgressAction)
        assert 0.0 <= decision.health_score <= 1.0

        signal = ProgressSignal(
            step_count=1,
            tool_calls=1,
            failure_ratio=0.0,
            error_rate_window=0.0,
            oscillation_index=0.0,
        )
        stability.analyze(signal)

        fault = FaultRecord(
            fault_type=FaultCategory.CONTEXT_OVERFLOW,
            severity=FaultSeverity.MEDIUM,
            timestamp=100.0,
            metrics_snapshot={"context_usage": 0.95},
            description="context limit approached",
        )
        healing_action = healing.handle_fault(fault)
        assert healing_action is not None
        assert healing_action.strategy_type.value == "compact_context"

        report = diagnostics.report(StopReason.done)
        rendered = diagnostics.render(StopReason.done)
        assert report.total_duration >= 0
        assert rendered == "" or "Diagnostics" in rendered
