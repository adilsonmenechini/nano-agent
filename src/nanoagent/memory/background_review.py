from .constants import COMBINED_REVIEW_PROMPT
from .utils import parse_category_content, persist_entries


class BackgroundReview:
    """Automatic background memory review.

    Triggered periodically after N turns or M tool calls to extract
    notable facts, user preferences, and failures to save to memory.
    """

    def __init__(self, agent, nudge_interval: int = 10, nudge_tool_calls: int = 15):
        self.agent = agent
        self.nudge_interval = nudge_interval
        self.nudge_tool_calls = nudge_tool_calls
        self.turn_count = 0
        self.tool_call_count = 0

    def on_turn_end(self, turn_count: int, tool_calls: int, messages: list[dict]) -> None:
        """Accrue counts and check if review should trigger."""
        self.turn_count += turn_count
        self.tool_call_count += tool_calls
        if self.turn_count >= self.nudge_interval or self.tool_call_count >= self.nudge_tool_calls:
            self._run_review(messages)
            self.turn_count = 0
            self.tool_call_count = 0

    def _run_review(self, messages: list[dict]) -> None:
        """Run the LLM review extraction and persist results."""
        if not self.agent.llm_provider:
            return

        convo_lines = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                convo_lines.append(f"User: {content}")
            elif role == "assistant" and content:
                convo_lines.append(f"Assistant: {content}")
            elif role == "tool":
                convo_lines.append(f"Tool Result: {content}")

        prompt = f"{COMBINED_REVIEW_PROMPT}\n\nRecent Conversation:\n" + "\n".join(convo_lines)
        try:
            response_text = self.agent.llm_provider.generate(
                prompt=prompt,
                system_prompt="You are a memory extraction assistant. Output only CATEGORY and CONTENT lines as requested.",
            )
            persist_entries(parse_category_content(response_text), self.agent, prefix="review")
        except Exception:
            pass
