from nanoagent.loop.constants import LoopConfig, Phase, StopReason
from nanoagent.loop.turn import Turn, TurnBudget, TurnStepPolicy


class TestTurnBudget:
    def test_from_config_defaults(self):
        config = LoopConfig()
        budget = TurnBudget.from_config(config)
        assert budget.max_steps == 50
        assert budget.remaining_steps == 50
        assert budget.budget_exhausted is False

    def test_consume_step(self):
        budget = TurnBudget(max_steps=5, remaining_steps=5)
        budget.consume_step()
        assert budget.remaining_steps == 4
        assert budget.budget_exhausted is False

    def test_budget_exhaustion(self):
        budget = TurnBudget(max_steps=2, remaining_steps=1)
        budget.consume_step()
        assert budget.remaining_steps == 0
        assert budget.budget_exhausted is True

    def test_no_negative_steps(self):
        budget = TurnBudget(max_steps=2, remaining_steps=0, budget_exhausted=True)
        budget.consume_step()
        assert budget.remaining_steps == 0


class TestTurnStepPolicy:
    def test_defaults(self):
        policy = TurnStepPolicy()
        assert policy.allow_widening is True
        assert policy.compact_aggressively is False
        assert policy.current_strategy == "normal"

    def test_strategy_switch(self):
        policy = TurnStepPolicy()
        policy.current_strategy = "narrowed"
        assert policy.current_strategy == "narrowed"

    def test_compact_flag(self):
        policy = TurnStepPolicy()
        policy.compact_aggressively = True
        assert policy.compact_aggressively is True


class TestTurn:
    def test_turn_full_cycle(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        result = turn.start("hello")
        assert isinstance(result, StopReason)
        assert result == StopReason.done

    def test_phase_progression(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        assert turn.current_phase == Phase.IDLE
        result = turn.start("hello")
        assert result == StopReason.done
        assert turn.current_phase == Phase.IDLE

    def test_empty_prompt(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        result = turn.start("   ")
        assert result == StopReason.done

    def test_budget_exhaustion(self):
        config = LoopConfig(max_steps_per_turn=1)
        turn = Turn(config)
        result = turn.start("hello")
        assert result == StopReason.max_steps

    def test_prompt_queuing(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        turn.queue_prompt("second")
        assert turn.has_pending() is True
        assert turn.next_pending() == "second"
        assert turn.has_pending() is False

    def test_next_pending_empty(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        assert turn.next_pending() is None

    def test_stop_reason_property(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        assert turn.stop_reason is None
        turn.start("hello")
        assert turn.stop_reason == StopReason.done

    def test_budget_property(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        budget = turn.budget
        assert isinstance(budget, TurnBudget)
        assert budget.max_steps == 10

    def test_policy_property(self):
        config = LoopConfig(max_steps_per_turn=10)
        turn = Turn(config)
        policy = turn.policy
        assert isinstance(policy, TurnStepPolicy)
