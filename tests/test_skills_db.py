

def test_db_skill_stored_and_loaded():
    from nanoagent.agent import Agent

    agent = Agent(db_path=":memory:")
    skill_code = """
def execute(context, **kwargs):
    return f"hello {kwargs.get('name', 'world')}"
"""
    agent.skill_storage.add_skill(
        slug="greeter",
        name="greeter",
        description="Greets a person",
        code=skill_code,
        scope="global",
    )
    entry = agent.skill_storage.get_skill("greeter")
    assert entry is not None
    assert entry["name"] == "greeter"
    agent.memory.close()


def test_skill_auto_loaded_from_db():
    from nanoagent.agent import Agent

    agent = Agent(db_path=":memory:")
    skill_code = """
def execute(context, **kwargs):
    return f"auto-loaded {kwargs.get('name', 'world')}"
"""
    agent.skill_storage.add_skill(
        slug="auto_greeter",
        name="auto_greeter",
        description="Auto-loaded greet skill",
        code=skill_code,
        scope="global",
    )
    from nanoagent.skills.loader import SkillsLoader, SkillContext

    ctx = SkillContext(tools={})
    db_skills = SkillsLoader.load_from_db(agent.skill_storage, context=ctx)
    assert "auto_greeter" in db_skills
    result = db_skills["auto_greeter"](name="test")
    assert "auto-loaded test" in result
    agent.memory.close()


def test_skill_versioning():
    from nanoagent.agent import Agent

    agent = Agent(db_path=":memory:")
    v1_code = "def execute(**kw): return 'v1'"
    v2_code = "def execute(**kw): return 'v2'"
    agent.skill_storage.add_skill(
        slug="versioned",
        name="versioned",
        description="v1 desc",
        code=v1_code,
        scope="global",
    )
    agent.skill_storage.update_skill(
        "versioned",
        code=v2_code,
        scope="global",
    )
    versions = agent.skill_storage.list_versions("versioned", scope="global")
    assert len(versions) >= 1
    result = agent.skill_storage.rollback("versioned", version=1, scope="global")
    assert result is True
    entry = agent.skill_storage.get_skill("versioned", scope="global")
    assert entry is not None
    assert entry["code"] == v1_code
    agent.memory.close()


def test_skill_dependency_validation():
    from nanoagent.skills.loader import SkillWrapper, SkillContext

    code = """
def execute(context, **kwargs):
    if 'missing_tool' not in context.tools:
        return "dependency missing"
    return "ok"
"""
    ctx = SkillContext(tools={})
    wrapper = SkillWrapper(name="dep_check", code=code, context=ctx)
    result = wrapper()
    assert "dependency missing" in result


def test_skill_wrapper_callable():
    from nanoagent.skills.loader import SkillWrapper, SkillContext

    code = """
def execute(context, **kwargs):
    return f"called with {kwargs}"
"""
    wrapper = SkillWrapper(name="testable", code=code, context=SkillContext())
    result = wrapper(x=42)
    assert "called with" in result
    assert "42" in result
