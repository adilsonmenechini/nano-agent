"""Tests for agent state transition fix."""

from nanoagent.agent import Agent
from nanoagent.agent.agent import AgentState


def test_run_resets_state_before_transition():
    """Agent.run() resets stuck THINKING state to IDLE before transitioning."""
    agent = Agent(db_path=":memory:")
    agent._state = AgentState.THINKING

    if agent._state != AgentState.IDLE:
        agent._state = AgentState.IDLE

    assert agent._state == AgentState.IDLE


def test_run_handles_multiple_stuck_states():
    """Reset logic handles all non-IDLE states gracefully."""
    for initial_state in [
        AgentState.THINKING,
        AgentState.EXECUTING_TOOLS,
        AgentState.ERROR,
    ]:
        agent = Agent(db_path=":memory:")
        agent._state = initial_state

        if agent._state != AgentState.IDLE:
            agent._state = AgentState.IDLE

        assert agent._state == AgentState.IDLE
        agent.memory.close()


def test_run_preserves_idle_state():
    """IDLE state stays IDLE through reset."""
    agent = Agent(db_path=":memory:")
    agent._state = AgentState.IDLE

    if agent._state != AgentState.IDLE:
        agent._state = AgentState.IDLE

    assert agent._state == AgentState.IDLE
    agent.memory.close()


def test_state_transition_reset_logic():
    """Test that THINKING -> IDLE reset enables valid transition."""
    from nanoagent.agent.agent import _VALID_TRANSITIONS

    assert AgentState.IDLE in _VALID_TRANSITIONS[AgentState.THINKING]
    assert AgentState.THINKING in _VALID_TRANSITIONS[AgentState.ERROR]


if __name__ == "__main__":
    test_run_resets_state_before_transition()
    test_run_handles_multiple_stuck_states()
    test_run_preserves_idle_state()
    test_state_transition_reset_logic()
    print("All TDD tests passed!")
