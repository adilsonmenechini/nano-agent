from nanoagent.loop.constants import Phase, StopReason
from nanoagent.loop.diagnostics import DiagnosticsCollector, DiagnosticsReport


class TestDiagnosticsReport:
    def test_defaults(self):
        report = DiagnosticsReport()
        assert report.phase_timings == {}
        assert report.total_duration == 0.0

    def test_with_data(self):
        report = DiagnosticsReport(
            phase_timings={"explore": 0.042, "execute": 1.237},
            stop_reason="done",
            total_duration=1.279,
        )
        assert report.phase_timings["explore"] == 0.042
        assert report.stop_reason == "done"


class TestDiagnosticsCollector:
    def test_disabled_by_default(self):
        collector = DiagnosticsCollector(enabled=False)
        collector.record_phase(Phase.EXPLORE, 0.042)
        report = collector.report()
        assert report.phase_timings == {}

    def test_records_phase_timing(self):
        collector = DiagnosticsCollector(enabled=True)
        collector.record_phase(Phase.EXPLORE, 0.042)
        collector.record_phase(Phase.EXECUTE, 1.237)
        report = collector.report()
        assert report.phase_timings["explore"] == 0.042
        assert report.phase_timings["execute"] == 1.237

    def test_records_tool_call(self):
        collector = DiagnosticsCollector(enabled=True)
        collector.record_tool_call("get_weather", 0.5, success=True)
        collector.record_tool_call("search_web", 1.2, success=False)
        report = collector.report()
        assert len(report.tool_calls) == 2
        assert report.tool_calls[0]["name"] == "get_weather"
        assert report.tool_calls[1]["success"] is False

    def test_records_health_snapshot(self):
        collector = DiagnosticsCollector(enabled=True)
        collector.record_health(0.85, "healthy")
        collector.record_health(0.45, "warning")
        report = collector.report()
        assert len(report.health_snapshots) == 2
        assert report.health_snapshots[-1]["level"] == "warning"

    def test_records_healing_action(self):
        collector = DiagnosticsCollector(enabled=True)
        collector.record_healing(
            {
                "fault_type": "OSCILLATION",
                "strategy": "break_oscillation",
                "success": True,
                "duration": 0.003,
            }
        )
        report = collector.report()
        assert len(report.healing_actions) == 1
        assert report.healing_actions[0]["fault_type"] == "OSCILLATION"

    def test_report_contains_stop_reason(self):
        collector = DiagnosticsCollector(enabled=True)
        collector.record_phase(Phase.EXPLORE, 0.1)
        report = collector.report(StopReason.done)
        assert report.stop_reason == "done"

    def test_total_duration(self):
        collector = DiagnosticsCollector(enabled=True)
        collector.record_phase(Phase.EXPLORE, 0.042)
        collector.record_phase(Phase.EXECUTE, 1.237)
        collector.record_phase(Phase.VERIFY, 0.018)
        report = collector.report()
        assert abs(report.total_duration - 1.297) < 0.001

    def test_render_empty_when_disabled(self):
        collector = DiagnosticsCollector(enabled=False)
        rendered = collector.render()
        assert rendered == ""

    def test_render_format(self):
        collector = DiagnosticsCollector(enabled=True)
        collector.record_phase(Phase.EXPLORE, 0.042)
        collector.record_health(0.92, "healthy")
        rendered = collector.render(StopReason.done)
        assert "Diagnostics" in rendered
        assert "explore" in rendered
        assert "0.042" in rendered
        assert "0.92" in rendered

    def test_reset_clears(self):
        collector = DiagnosticsCollector(enabled=True)
        collector.record_phase(Phase.EXPLORE, 0.042)
        assert len(collector.report().phase_timings) == 1
        collector.reset()
        assert len(collector.report().phase_timings) == 0
