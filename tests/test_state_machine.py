import pytest
from nanoagent.agent.agent import AgentState, _VALID_TRANSITIONS, StateTransition
from nanoagent.agent.errors import StateTransitionError


def test_state_enum_values():
    assert len(AgentState) == 5
    assert AgentState.IDLE.name == "IDLE"
    assert AgentState.THINKING.name == "THINKING"
    assert AgentState.EXECUTING_TOOLS.name == "EXECUTING_TOOLS"
    assert AgentState.AWAITING_INPUT.name == "AWAITING_INPUT"
    assert AgentState.ERROR.name == "ERROR"


def test_valid_transitions_idle():
    assert AgentState.THINKING in _VALID_TRANSITIONS[AgentState.IDLE]


def test_valid_transitions_thinking():
    allowed = _VALID_TRANSITIONS[AgentState.THINKING]
    assert AgentState.EXECUTING_TOOLS in allowed
    assert AgentState.AWAITING_INPUT in allowed
    assert AgentState.IDLE in allowed
    assert AgentState.ERROR in allowed


def test_valid_transitions_executing_tools():
    allowed = _VALID_TRANSITIONS[AgentState.EXECUTING_TOOLS]
    assert AgentState.THINKING in allowed
    assert AgentState.ERROR in allowed


def test_valid_transitions_awaiting_input():
    allowed = _VALID_TRANSITIONS[AgentState.AWAITING_INPUT]
    assert AgentState.IDLE in allowed


def test_valid_transitions_error():
    allowed = _VALID_TRANSITIONS[AgentState.ERROR]
    assert AgentState.IDLE in allowed
    assert AgentState.THINKING in allowed


def test_invalid_transition_not_allowed():
    assert AgentState.EXECUTING_TOOLS not in _VALID_TRANSITIONS[AgentState.IDLE]
    assert AgentState.IDLE not in _VALID_TRANSITIONS[AgentState.EXECUTING_TOOLS]


def test_state_transition_dataclass():
    from datetime import datetime

    t = StateTransition(
        from_state=AgentState.IDLE,
        to_state=AgentState.THINKING,
        reason="test",
        metadata={"key": "value"},
    )
    assert t.from_state == AgentState.IDLE
    assert t.to_state == AgentState.THINKING
    assert t.reason == "test"
    assert t.metadata == {"key": "value"}
    assert isinstance(t.timestamp, datetime)


def test_agent_state_transition(agent):
    assert agent.state == AgentState.IDLE
    agent._transition(AgentState.THINKING, "test")
    assert agent.state == AgentState.THINKING
    agent._transition(AgentState.IDLE, "done")
    assert agent.state == AgentState.IDLE


def test_agent_invalid_transition_raises(agent):
    with pytest.raises(StateTransitionError):
        agent._transition(AgentState.ERROR, "invalid start")


def test_agent_state_change_callback(agent):
    transitions = []
    agent.on_state_change = lambda t: transitions.append(t)
    agent._transition(AgentState.THINKING, "callback test")
    assert len(transitions) == 1
    assert transitions[0].from_state == AgentState.IDLE
    assert transitions[0].to_state == AgentState.THINKING


def test_agent_state_listener(agent):
    transitions = []
    agent.add_state_listener(lambda t: transitions.append(t))
    agent._transition(AgentState.THINKING, "listener test")
    assert len(transitions) == 1


def test_full_tool_call_transition_flow(agent):
    transitions = []
    agent.add_state_listener(lambda t: transitions.append(t))
    agent._transition(AgentState.THINKING, "start")
    assert agent.state == AgentState.THINKING
    agent._transition(AgentState.EXECUTING_TOOLS, "tool call")
    assert agent.state == AgentState.EXECUTING_TOOLS
    agent._transition(AgentState.THINKING, "tool result")
    assert agent.state == AgentState.THINKING
    agent._transition(AgentState.IDLE, "done")
    assert agent.state == AgentState.IDLE
    assert len(transitions) == 4


def test_error_then_recovery_transition(agent):
    agent._transition(AgentState.THINKING, "start")
    agent._transition(AgentState.ERROR, "something failed")
    assert agent.state == AgentState.ERROR
    agent._transition(AgentState.IDLE, "recovered")
    assert agent.state == AgentState.IDLE
