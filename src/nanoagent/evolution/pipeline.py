from __future__ import annotations


from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.skills.skill_storage import SkillStorage
from nanoagent.evolution.config import EvolutionConfig
from nanoagent.evolution.dataset import DatasetBuilder
from nanoagent.evolution.optimizer import GeptOptimizer


class EvolutionPipeline:
    def __init__(self, store: SQLiteMemoryStore, config: EvolutionConfig | None = None):
        self.store = store
        self.config = config or EvolutionConfig()
        self.skill_storage = SkillStorage(store=store)
        self.dataset_builder = DatasetBuilder(store=store)
        self.optimizer = GeptOptimizer(
            model=self.config.model,
            iterations=self.config.iterations,
        )

    def evolve(
        self, slug: str, iterations: int | None = None, eval_source: str | None = None
    ) -> dict:
        skill = self.skill_storage.get_skill(slug)
        if not skill:
            return {"error": f"Skill '{slug}' not found", "success": False}
        skill_code = skill.get("code", "")
        if not skill_code:
            return {"error": f"Skill '{slug}' has no code", "success": False}
        iters = iterations or self.config.iterations
        source = eval_source or self.config.eval_source
        if source == "reflection_records":
            eval_dataset = self.dataset_builder.build_from_reflections(limit=50)
        else:
            eval_dataset = self.dataset_builder.build_synthetic(
                skill_domain=slug, count=10
            )
        self.optimizer.iterations = iters
        result = self.optimizer.optimize(skill_code, eval_dataset)
        result["slug"] = slug
        result["success"] = True
        return result

    def accept_evolution(self, slug: str, evolved_code: str) -> bool:
        skill = self.skill_storage.get_skill(slug)
        if not skill:
            return False
        return self.skill_storage.update_skill(
            slug=slug,
            code=evolved_code,
            description=f"[Evolved] {skill.get('description', '')}",
        )
