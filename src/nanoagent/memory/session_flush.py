import hashlib
from .constants import FLUSH_PROMPT

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

        convo_text = "\n".join(convo_lines)
        prompt = f"{FLUSH_PROMPT}\n\nSession Conversation:\n{convo_text}"

        try:
            response_text = agent.llm_provider.generate(
                prompt=prompt,
                system_prompt="You are a memory flush assistant. Output only CATEGORY and CONTENT lines."
            )

            entries = []
            current_category = None

            for line in response_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.upper().startswith("CATEGORY:"):
                    current_category = line[len("CATEGORY:"):].strip().lower()
                elif line.upper().startswith("CONTENT:"):
                    current_content = line[len("CONTENT:"):].strip()
                    if current_category and current_content:
                        entries.append((current_category, current_content))
                        current_category = None

            for category, content in entries:
                if category in ("user", "memory"):
                    key_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
                    key = f"flush-{category}-{key_hash}"
                    agent.remember(
                        key=key,
                        value=content,
                        target=category,
                        scope="project" if agent.project_path else "global"
                    )
                elif category == "failure":
                    agent.memory.add_failure(
                        content=content,
                        category="failure",
                        project_path=agent.project_path
                    )
        except Exception:
            pass
