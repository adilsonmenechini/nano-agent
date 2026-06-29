import pytest
from nanoagent.loop.constants import FaultCategory, FaultSeverity, HealthLevel, LoopConfig
from nanoagent.loop.health import HealthMetrics, StabilityMonitor, StabilityReport
from nanoagent.loop.progress import ProgressSignal


class TestHealthMetrics:
    def test_defaults(self):
        m = HealthMetrics()
        assert m.success_rate == 1.0
        assert m.error_frequency == 0.0


class TestStabilityMonitor:
    def test_analyze_healthy(self):
        monitor = StabilityMonitor(LoopConfig())
        signal = ProgressSignal(
            failure_ratio=0.0, tool_calls=1,
            output_changes=1, error_rate_window=0.0,
            oscillation_index=0.0, context_usage_ratio=0.1,
            completion_ratio=0.5,
        )
        report = monitor.analyze(signal)
        assert isinstance(report, StabilityReport)
        assert report.health_level == HealthLevel.healthy

    def test_detect_oscillation_anomaly(self):
        monitor = StabilityMonitor(LoopConfig())
        signal = ProgressSignal(
            oscillation_index=0.95, failure_ratio=0.0,
            error_rate_window=0.0, context_usage_ratio=0.1,
            tool_calls=5, output_changes=0, completion_ratio=0.0,
        )
        anomalies = monitor.detect_anomalies(signal)
        oscillation = [a for a in anomalies if a.fault_type == FaultCategory.OSCILLATION]
        assert len(oscillation) >= 1

    def test_detect_error_spike(self):
        monitor = StabilityMonitor(LoopConfig())
        signal = ProgressSignal(
            error_rate_window=0.8, oscillation_index=0.0,
            failure_ratio=0.0, context_usage_ratio=0.1,
            tool_calls=1, output_changes=1, completion_ratio=0.0,
        )
        anomalies = monitor.detect_anomalies(signal)
        error_spike = [a for a in anomalies if a.fault_type == FaultCategory.ERROR_SPIKE]
        assert len(error_spike) >= 1

    def test_detect_context_overflow(self):
        monitor = StabilityMonitor(LoopConfig())
        signal = ProgressSignal(
            context_usage_ratio=0.95, error_rate_window=0.0,
            oscillation_index=0.0, failure_ratio=0.0,
            tool_calls=1, output_changes=1, completion_ratio=0.0,
        )
        anomalies = monitor.detect_anomalies(signal)
        overflow = [a for a in anomalies if a.fault_type == FaultCategory.CONTEXT_OVERFLOW]
        assert len(overflow) >= 1

    def test_no_anomalies_on_healthy(self):
        monitor = StabilityMonitor(LoopConfig())
        signal = ProgressSignal(
            error_rate_window=0.0, oscillation_index=0.0,
            context_usage_ratio=0.1, failure_ratio=0.0,
            tool_calls=2, output_changes=2, completion_ratio=1.0,
        )
        anomalies = monitor.detect_anomalies(signal)
        assert len(anomalies) == 0

    def test_analyze_twice_accumulates(self):
        monitor = StabilityMonitor(LoopConfig())
        s1 = ProgressSignal(failure_ratio=0.0, tool_calls=1, output_changes=1,
                            error_rate_window=0.0, oscillation_index=0.0,
                            context_usage_ratio=0.1, completion_ratio=0.5)
        s2 = ProgressSignal(failure_ratio=0.5, tool_calls=2, output_changes=0,
                            error_rate_window=0.3, oscillation_index=0.0,
                            context_usage_ratio=0.8, completion_ratio=0.6)
        r1 = monitor.analyze(s1)
        r2 = monitor.analyze(s2)
        assert r1.stability_index != r2.stability_index

    def test_reset_clears(self):
        monitor = StabilityMonitor(LoopConfig())
        signal = ProgressSignal(
            oscillation_index=0.95, failure_ratio=0.0,
            error_rate_window=0.0, context_usage_ratio=0.1,
            tool_calls=1, output_changes=1, completion_ratio=0.0,
        )
        monitor.detect_anomalies(signal)
        assert len(monitor._detected_faults) > 0  # noqa: SLF001
        monitor.reset()
        assert len(monitor._detected_faults) == 0  # noqa: SLF001
