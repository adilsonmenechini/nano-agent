import pytest
from nanoagent.loop.constants import (
    DEFAULT_CONFIG,
    FaultCategory,
    FaultSeverity,
    HealthLevel,
    HealingStrategyType,
    LoopConfig,
    Phase,
    ProgressAction,
    StopReason,
)


class TestPhase:
    def test_enum_values(self):
        assert len(Phase) == 6
        assert Phase.IDLE.value == "idle"
        assert Phase.RECEIVE.value == "receive"
        assert Phase.EXPLORE.value == "explore"
        assert Phase.EXECUTE.value == "execute"
        assert Phase.VERIFY.value == "verify"
        assert Phase.RESPOND.value == "respond"

    def test_ordered_values(self):
        expected = [Phase.IDLE, Phase.RECEIVE, Phase.EXPLORE, Phase.EXECUTE, Phase.VERIFY, Phase.RESPOND]
        assert list(Phase) == expected


class TestStopReason:
    def test_enum_values(self):
        assert len(StopReason) == 6
        assert StopReason.done.value == "done"
        assert StopReason.max_steps.value == "max_steps"
        assert StopReason.await_user.value == "await_user"
        assert StopReason.blocked.value == "blocked"
        assert StopReason.verification_failed.value == "verification_failed"


class TestHealthLevel:
    def test_enum_values(self):
        assert len(HealthLevel) == 4
        assert HealthLevel.healthy.value == "healthy"

    def test_from_score_healthy(self):
        for score in [0.80, 0.85, 0.95, 1.0]:
            assert HealthLevel.from_score(score) == HealthLevel.healthy

    def test_from_score_degraded(self):
        for score in [0.50, 0.60, 0.79]:
            assert HealthLevel.from_score(score) == HealthLevel.degraded

    def test_from_score_warning(self):
        for score in [0.20, 0.35, 0.49]:
            assert HealthLevel.from_score(score) == HealthLevel.warning

    def test_from_score_critical(self):
        for score in [0.0, 0.10, 0.19]:
            assert HealthLevel.from_score(score) == HealthLevel.critical


class TestFaultCategory:
    def test_enum_values(self):
        assert len(FaultCategory) == 6
        assert FaultCategory.OSCILLATION.value == "oscillation"
        assert FaultCategory.RESOURCE_EXHAUSTION.value == "resource_exhaustion"
        assert FaultCategory.CONTEXT_OVERFLOW.value == "context_overflow"
        assert FaultCategory.TOOL_TIMEOUT.value == "tool_timeout"
        assert FaultCategory.ERROR_SPIKE.value == "error_spike"
        assert FaultCategory.DEADLOCK.value == "deadlock"


class TestFaultSeverity:
    def test_enum_values(self):
        assert len(FaultSeverity) == 4
        assert FaultSeverity.LOW.value == "low"
        assert FaultSeverity.MEDIUM.value == "medium"
        assert FaultSeverity.HIGH.value == "high"
        assert FaultSeverity.CRITICAL.value == "critical"


class TestHealingStrategyType:
    def test_enum_values(self):
        assert len(HealingStrategyType) == 6
        assert HealingStrategyType.retry.value == "retry"
        assert HealingStrategyType.compact_context.value == "compact_context"
        assert HealingStrategyType.reduce_scope.value == "reduce_scope"
        assert HealingStrategyType.break_oscillation.value == "break_oscillation"
        assert HealingStrategyType.request_confirmation.value == "request_confirmation"
        assert HealingStrategyType.abort_turn.value == "abort_turn"


class TestProgressAction:
    def test_enum_values(self):
        assert len(ProgressAction) == 5
        assert ProgressAction.continue_.value == "continue"
        assert ProgressAction.switch_strategy.value == "switch_strategy"
        assert ProgressAction.narrow_scope.value == "narrow_scope"
        assert ProgressAction.request_confirmation.value == "request_confirmation"
        assert ProgressAction.stop.value == "stop"


class TestLoopConfig:
    def test_default_values(self):
        config = LoopConfig()
        assert config.max_steps_per_turn == 50
        assert config.tool_timeout_seconds == 30.0
        assert config.llm_timeout_seconds == 120.0
        assert config.stall_threshold == 5
        assert config.oscillation_window == 3
        assert config.compaction_threshold == 0.80
        assert config.diagnostics_enabled is False
        assert config.health_window_size == 20

    def test_custom_values(self):
        config = LoopConfig(max_steps_per_turn=10, tool_timeout_seconds=5.0)
        assert config.max_steps_per_turn == 10
        assert config.tool_timeout_seconds == 5.0

    def test_max_steps_below_min(self):
        with pytest.raises(ValueError, match="max_steps_per_turn must be 1-500"):
            LoopConfig(max_steps_per_turn=0)

    def test_max_steps_above_max(self):
        with pytest.raises(ValueError, match="max_steps_per_turn must be 1-500"):
            LoopConfig(max_steps_per_turn=501)

    def test_tool_timeout_non_positive(self):
        with pytest.raises(ValueError, match="tool_timeout_seconds must be positive"):
            LoopConfig(tool_timeout_seconds=-1.0)

    def test_llm_timeout_non_positive(self):
        with pytest.raises(ValueError, match="llm_timeout_seconds must be positive"):
            LoopConfig(llm_timeout_seconds=0.0)

    def test_stall_threshold_below_min(self):
        with pytest.raises(ValueError, match="stall_threshold must be >= 1"):
            LoopConfig(stall_threshold=0)

    def test_oscillation_window_below_min(self):
        with pytest.raises(ValueError, match="oscillation_window must be >= 2"):
            LoopConfig(oscillation_window=1)

    def test_compaction_threshold_above_max(self):
        with pytest.raises(ValueError, match="compaction_threshold must be 0.0-1.0"):
            LoopConfig(compaction_threshold=1.5)

    def test_health_window_below_min(self):
        with pytest.raises(ValueError, match="health_window_size must be >= 5"):
            LoopConfig(health_window_size=4)

    def test_frozen(self):
        config = LoopConfig()
        with pytest.raises(AttributeError):
            config.max_steps_per_turn = 100


class TestDefaultConfig:
    def test_default_config_is_loop_config(self):
        assert isinstance(DEFAULT_CONFIG, LoopConfig)

    def test_default_config_defaults(self):
        assert DEFAULT_CONFIG == LoopConfig()
