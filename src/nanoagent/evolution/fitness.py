from __future__ import annotations



class SkillFitness:
    def __init__(self, eval_model: str = "gpt-4.1-mini"):
        self.eval_model = eval_model

    def evaluate(self, skill_code: str, eval_dataset: list[dict]) -> dict:
        if not eval_dataset:
            return {"fitness_score": 0.0, "success_rate": 0.0, "avg_latency_ms": 0, "output_quality": 0.0}
        total = len(eval_dataset)
        successes = sum(1 for item in eval_dataset if item.get("outcome") == "success")
        success_rate = successes / total if total > 0 else 0.0
        has_tool_refs = sum(1 for item in eval_dataset if any(
            t in skill_code for t in item.get("expected_tools", [])
        )) if eval_dataset and "expected_tools" in eval_dataset[0] else 0
        tool_coverage = has_tool_refs / total if total > 0 else 0.0
        quality = min(1.0, success_rate * 0.6 + tool_coverage * 0.4) if total > 0 else 0.0
        return {
            "fitness_score": round(quality, 3),
            "success_rate": round(success_rate, 3),
            "avg_latency_ms": 0,
            "output_quality": round(quality, 3),
        }


class ConstraintValidator:
    def __init__(self, max_size: int = 50_000, max_growth_pct: float = 50.0):
        self.max_size = max_size
        self.max_growth_pct = max_growth_pct

    def validate(self, artifact_text: str, artifact_type: str = "skill", baseline_text: str | None = None) -> list[dict]:
        results = []
        if len(artifact_text) > self.max_size:
            results.append({"constraint": "size", "passed": False, "message": f"Size {len(artifact_text)} exceeds max {self.max_size}"})
        else:
            results.append({"constraint": "size", "passed": True, "message": "Within size limit"})
        if not artifact_text.strip():
            results.append({"constraint": "non_empty", "passed": False, "message": "Artifact is empty"})
        else:
            results.append({"constraint": "non_empty", "passed": True, "message": "Non-empty"})
        if baseline_text and len(artifact_text) > len(baseline_text) * (1 + self.max_growth_pct / 100):
            results.append({"constraint": "growth", "passed": False, "message": f"Growth exceeds {self.max_growth_pct}%"})
        else:
            results.append({"constraint": "growth", "passed": True, "message": "Growth within limits"})
        if artifact_type == "skill":
            has_docstring = artifact_text.strip().startswith('"""') or artifact_text.strip().startswith("'''")
            results.append({"constraint": "skill_structure", "passed": has_docstring, "message": "Has docstring" if has_docstring else "Missing docstring"})
        return results
