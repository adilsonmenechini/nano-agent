from __future__ import annotations


from nanoagent.evolution.fitness import SkillFitness, ConstraintValidator


class GeptOptimizer:
    def __init__(self, model: str = "gpt-4.1-mini", iterations: int = 5):
        self.model = model
        self.iterations = iterations
        self.fitness = SkillFitness(eval_model=model)
        self.validator = ConstraintValidator()

    def optimize(self, skill_code: str, eval_dataset: list[dict]) -> dict:
        baseline = self.fitness.evaluate(skill_code, eval_dataset)
        variants = self._generate_variants(skill_code, self.iterations)
        best_variant = skill_code
        best_fitness = baseline
        for variant in variants:
            constraints = self.validator.validate(variant, "skill", baseline_text=skill_code)
            if not all(c["passed"] for c in constraints):
                continue
            score = self.fitness.evaluate(variant, eval_dataset)
            if score["fitness_score"] > best_fitness["fitness_score"]:
                best_fitness = score
                best_variant = variant
        return {
            "baseline": baseline,
            "best_fitness": best_fitness,
            "best_variant": best_variant,
            "improved": best_fitness["fitness_score"] > baseline["fitness_score"],
        }

    def _generate_variants(self, code: str, count: int) -> list[str]:
        variants = []
        for i in range(count):
            mutated = self._mutate(code)
            if mutated != code:
                variants.append(mutated)
        if not variants:
            variants.append(code)
        return variants

    def _mutate(self, code: str) -> str:
        lines = code.split("\n")
        if len(lines) > 3 and "description" in lines[2].lower():
            desc_line = lines[2]
            words = desc_line.split()
            if len(words) > 3:
                import random
                i = random.randint(2, len(words) - 1)
                words[i] = words[i].upper()
                lines[2] = " ".join(words)
        return "\n".join(lines)
