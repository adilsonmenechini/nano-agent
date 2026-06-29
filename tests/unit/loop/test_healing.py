import pytest
from nanoagent.loop.constants import (
    FaultCategory,
    FaultRecord,
    FaultSeverity,
    HealingAction,
    HealingStrategyType,
)
from nanoagent.loop.healing import (
    DEFAULT_STRATEGIES,
    HealingEngine,
    HealingStrategy,
)


class TestFaultRecord:
    def test_defaults(self):
        fault = FaultRecord(
            fault_type=FaultCategory.OSCILLATION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
        )
        assert fault.fault_type == FaultCategory.OSCILLATION
        assert fault.severity == FaultSeverity.HIGH

    def test_with_description(self):
        fault = FaultRecord(
            fault_type=FaultCategory.RESOURCE_EXHAUSTION,
            severity=FaultSeverity.CRITICAL,
            timestamp=200.0,
            description="LLM provider unavailable",
        )
        assert fault.description == "LLM provider unavailable"


class TestHealingStrategy:
    def test_default_strategies_count(self):
        assert len(DEFAULT_STRATEGIES) == 6

    def test_retry_strategy(self):
        retry = [s for s in DEFAULT_STRATEGIES if s.strategy_type == HealingStrategyType.retry][0]
        assert retry.expected_recovery_seconds == 5.0
        assert retry.success_probability == 0.70
        assert FaultCategory.RESOURCE_EXHAUSTION in retry.applies_to
        assert FaultCategory.TOOL_TIMEOUT in retry.applies_to


class TestHealingAction:
    def test_defaults(self):
        action = HealingAction(
            strategy_type=HealingStrategyType.retry,
            fault_type=FaultCategory.RESOURCE_EXHAUSTION,
        )
        assert action.strategy_type == HealingStrategyType.retry
        assert action.execution_time == 0.0
        assert action.success is False


class TestHealingEngine:
    def test_handle_fault_selects_strategy(self):
        engine = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.RESOURCE_EXHAUSTION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
            description="LLM provider timeout",
        )
        action = engine.handle_fault(fault)
        assert action is not None
        assert action.fault_type == FaultCategory.RESOURCE_EXHAUSTION

    def test_retry_for_resource_exhaustion(self):
        engine = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.RESOURCE_EXHAUSTION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
        )
        action = engine.handle_fault(fault)
        assert action.strategy_type == HealingStrategyType.retry

    def test_oscillation_strategy(self):
        engine = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.OSCILLATION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
        )
        action = engine.handle_fault(fault)
        assert action.strategy_type == HealingStrategyType.break_oscillation

    def test_context_overflow_strategy(self):
        engine = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.CONTEXT_OVERFLOW,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
        )
        action = engine.handle_fault(fault)
        assert action.strategy_type == HealingStrategyType.compact_context

    def test_effectiveness_tracking(self):
        engine = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.RESOURCE_EXHAUSTION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
        )
        engine.handle_fault(fault)
        engine.record_success(HealingStrategyType.retry)
        summary = engine.effectiveness_summary()
        assert HealingStrategyType.retry in summary
        assert summary[HealingStrategyType.retry]["execution_count"] == 1
        assert summary[HealingStrategyType.retry]["success_count"] == 1

    def test_effectiveness_tracking_multiple(self):
        engine = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.RESOURCE_EXHAUSTION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
        )
        for _ in range(3):
            engine.handle_fault(fault)
            engine.record_success(HealingStrategyType.retry)
        summary = engine.effectiveness_summary()
        assert summary[HealingStrategyType.retry]["execution_count"] == 3
        assert summary[HealingStrategyType.retry]["success_count"] == 3

    def test_strategies_for_all_fault_categories(self):
        engine = HealingEngine()
        categories = list(FaultCategory)
        for cat in categories:
            fault = FaultRecord(
                fault_type=cat,
                severity=FaultSeverity.MEDIUM,
                timestamp=100.0,
            )
            action = engine.handle_fault(fault)
            assert action is not None, f"No strategy for {cat}"
            assert isinstance(action.strategy_type, HealingStrategyType)

    def test_action_history(self):
        engine = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.OSCILLATION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
        )
        engine.handle_fault(fault)
        assert len(engine.action_history()) == 1

    def test_reset_clears(self):
        engine = HealingEngine()
        fault = FaultRecord(
            fault_type=FaultCategory.RESOURCE_EXHAUSTION,
            severity=FaultSeverity.HIGH,
            timestamp=100.0,
        )
        engine.handle_fault(fault)
        assert len(engine.action_history()) == 1
        engine.reset()
        assert len(engine.action_history()) == 0
        summary = engine.effectiveness_summary()
        assert summary[HealingStrategyType.retry]["execution_count"] == 0
