import hashlib
from .constants import COMBINED_REVIEW_PROMPT

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
            # Reset counters
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

        convo_text = "\n".join(convo_lines)
        prompt = f"{COMBINED_REVIEW_PROMPT}\n\nRecent Conversation:\n{convo_text}"

        try:
            response_text = self.agent.llm_provider.generate(
                prompt=prompt,
                system_prompt="You are a memory extraction assistant. Output only CATEGORY and CONTENT lines as requested."
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
                    key = f"review-{category}-{key_hash}"
                    self.agent.remember(
                        key=key,
                        value=content,
                        target=category,
                        scope="project" if self.agent.project_path else "global"
                    )
                elif category == "failure":
                    self.agent.memory.add_failure(
                        content=content,
                        category="failure",
                        project_path=self.agent.project_path
                    )
        except Exception:
            pass
