from .constants import FLUSH_PROMPT
from .utils import parse_category_content, persist_entries


class SessionFlush:
    """Flush memory helper.

    Triggered upon exit to save critical session context before it's lost.
    """

    def __init__(self, flush_min_turns: int = 6):
        self.flush_min_turns = flush_min_turns

    def should_flush(self, turn_count: int) -> bool:
        return turn_count >= self.flush_min_turns

    def flush(self, messages: list[dict], agent) -> None:
        """Extract important details from session conversation and save them."""
        if not agent.llm_provider or not messages:
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

        prompt = f"{FLUSH_PROMPT}\n\nSession Conversation:\n" + "\n".join(convo_lines)
        try:
            response_text = agent.llm_provider.generate(
                prompt=prompt,
                system_prompt="You are a memory flush assistant. Output only CATEGORY and CONTENT lines.",
            )
            persist_entries(
                parse_category_content(response_text), agent, prefix="flush"
            )
        except Exception:
            pass
