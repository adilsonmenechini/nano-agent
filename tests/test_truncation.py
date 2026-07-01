from nanoagent.truncation import OutputTruncator


class TestOutputTruncator:
    def test_within_threshold(self):
        t = OutputTruncator(max_chars=100)
        result = t.truncate("hello world")
        assert result == "hello world"

    def test_exceeding_threshold(self):
        t = OutputTruncator(max_chars=10)
        result = t.truncate("a" * 200)
        assert len(result) < 200
        assert "[truncated" in result

    def test_snaps_to_line_boundary(self):
        t = OutputTruncator(max_chars=10)
        result = t.truncate("line1\nline2\nline3")
        assert result == "line1\n[truncated 2 lines, 12 chars]"

    def test_no_newline_before_threshold(self):
        t = OutputTruncator(max_chars=5)
        result = t.truncate("helloworld")
        assert "[truncated" in result
        assert len(result) <= 5 + 30

    def test_zero_length_output(self):
        t = OutputTruncator(max_chars=100)
        result = t.truncate("")
        assert result == ""

    def test_configurable_max_chars(self):
        t = OutputTruncator(max_chars=5)
        result = t.truncate("a" * 100)
        assert "[truncated" in result
