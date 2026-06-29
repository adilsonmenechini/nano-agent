"""Smart output truncation for tool results.

Provides OutputTruncator that caps tool return size at a configurable
threshold while respecting line boundaries.
"""

from __future__ import annotations


class OutputTruncator:
    """Truncates strings that exceed a configurable character threshold.

    Truncation snaps to the nearest line boundary (``\\n``) before the
    threshold and appends a ``[truncated N lines, M chars]`` marker.
    """

    def __init__(self, max_chars: int = 10_240, suffix: str = ""):
        if max_chars < 1:
            max_chars = 1
        self.max_chars = max_chars
        self._suffix = suffix

    def truncate(self, text: str) -> str:
        """Truncate *text* if it exceeds ``max_chars``.

        Args:
            text: The string to potentially truncate.

        Returns:
            The original string if within the threshold, otherwise a
            truncated version ending with ``[truncated N lines, M chars]``.
        """
        if len(text) <= self.max_chars:
            return text

        total_lines = text.count("\n") + 1

        # Snap to the last newline before the threshold
        truncate_pos = text.rfind("\n", 0, self.max_chars)
        if truncate_pos == -1:
            # No newline found — truncate at max_chars
            truncate_pos = self.max_chars

        truncated = text[:truncate_pos]
        omitted_chars = len(text) - len(truncated)
        omitted_lines = total_lines - (truncated.count("\n") + 1)

        suffix = self._build_suffix(omitted_lines, omitted_chars)
        return truncated + suffix

    def _build_suffix(self, omitted_lines: int, omitted_chars: int) -> str:
        if self._suffix:
            return self._suffix
        return f"\n[truncated {omitted_lines} lines, {omitted_chars} chars]"


__all__ = ["OutputTruncator"]
