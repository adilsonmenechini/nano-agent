from __future__ import annotations

from nanoagent.evolution.fitness import SkillFitness, ConstraintValidator


def test_fitness_empty_dataset():
    fitness = SkillFitness()
    score = fitness.evaluate("print('hello')", [])
    assert score["fitness_score"] == 0.0


def test_fitness_all_success():
    fitness = SkillFitness()
    dataset = [
        {
            "task_description": "do X",
            "expected_tools": ["run_shell"],
            "outcome": "success",
        },
        {
            "task_description": "do Y",
            "expected_tools": ["read_file"],
            "outcome": "success",
        },
    ]
    score = fitness.evaluate("run_shell code", dataset)
    assert score["success_rate"] > 0


def test_constraint_size_pass():
    validator = ConstraintValidator(max_size=1000)
    results = validator.validate('"""small"""\ncode', "skill")
    assert all(r["passed"] for r in results)


def test_constraint_size_fail():
    validator = ConstraintValidator(max_size=10)
    results = validator.validate("x" * 20, "skill")
    size_result = [r for r in results if r["constraint"] == "size"]
    assert not size_result[0]["passed"]


def test_constraint_non_empty():
    validator = ConstraintValidator()
    results = validator.validate("", "skill")
    non_empty = [r for r in results if r["constraint"] == "non_empty"]
    assert not non_empty[0]["passed"]


def test_constraint_growth_fail():
    validator = ConstraintValidator(max_growth_pct=10.0)
    baseline = "short"
    long_text = "x" * 100
    results = validator.validate(long_text, "skill", baseline_text=baseline)
    growth = [r for r in results if r["constraint"] == "growth"]
    assert not growth[0]["passed"]
