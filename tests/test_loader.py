"""Tests for SkillsLoader, SkillContext, SkillWrapper."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nanoagent.skills.loader import SkillContext, SkillWrapper, SkillsLoader


class TestSkillContext:
    def test_default_empty(self):
        ctx = SkillContext()
        assert ctx.tools == {}
        assert ctx.memory is None
        assert ctx.logger is None

    def test_with_values(self):
        tools = {"web": MagicMock()}
        memory = MagicMock()
        logger = MagicMock()
        ctx = SkillContext(tools=tools, memory=memory, logger=logger)
        assert ctx.tools == tools
        assert ctx.memory == memory
        assert ctx.logger == logger


class TestSkillWrapper:
    def test_execute_function(self):
        code = "def execute(context, x=1):\n    return x * 2\n"
        wrapper = SkillWrapper("double", code, SkillContext())
        assert wrapper.execute is not None
        assert wrapper(x=5) == 10

    def test_run_function(self):
        code = "def run(context, **kwargs):\n    return 'ran'\n"
        wrapper = SkillWrapper("runner", code, SkillContext())
        assert wrapper(name="test") == "ran"

    def test_no_entry_point(self):
        code = "def something(context):\n    return 'nope'\n"
        wrapper = SkillWrapper("noop", code, SkillContext())
        assert wrapper() == "Skill 'noop' has no callable entry point"
        assert wrapper.execute is None

    def test_invalid_code(self):
        code = "this is not valid python @@@"
        with pytest.raises(SyntaxError):
            SkillWrapper("invalid", code, SkillContext())

    def test_execute_property(self):
        code = "def execute(context):\n    return 42\n"
        wrapper = SkillWrapper("magic", code, SkillContext())
        assert wrapper.execute is not None
        assert wrapper() == 42

    def test_call_with_context(self):
        code = """
def execute(context, name):
    tools = context.tools
    return f"Hello {name}, tools: {list(tools.keys())}"
"""
        ctx = SkillContext(tools={"web": MagicMock()})
        wrapper = SkillWrapper("greeter", code, ctx)
        result = wrapper(name="World")
        assert "Hello World" in result
        assert "web" in result

    def test_description(self):
        wrapper = SkillWrapper("desc_test", "x=1", SkillContext())
        wrapper.description = "A test skill"
        assert wrapper.description == "A test skill"


class TestSkillsLoader:
    def test_empty_sources(self):
        loader = SkillsLoader([])
        assert loader.names == []

    def test_nonexistent_directory(self):
        loader = SkillsLoader(["/nonexistent/path"])
        assert loader.names == []

    def test_load_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "test_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: test_skill\ndescription: A test skill\n---")
            loader = SkillsLoader([str(tmp)])
            assert "test_skill" in loader.names

    def test_get_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "found_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: found_skill\ndescription: found\n---")
            loader = SkillsLoader([str(tmp)])
            meta = loader.get("found_skill")
            assert meta is not None
            assert meta.name == "found_skill"

    def test_get_skill_not_found(self):
        loader = SkillsLoader([])
        assert loader.get("nonexistent") is None

    def test_get_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "code_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: code_skill\ndescription: code\n---\nprint('hello')")
            loader = SkillsLoader([str(tmp)])
            code = loader.load_content("code_skill")
            assert code is not None
            assert "hello" in code

    def test_get_code_not_found(self):
        loader = SkillsLoader([])
        assert loader.load_content("nonexistent") is None

    def test_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "cat_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: cat_skill\ndescription: catalog test\n---")
            loader = SkillsLoader([str(tmp)])
            catalog = loader.catalog
            assert "cat_skill" in catalog
            assert "catalog test" in catalog

    def test_names_property(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ["skill_a", "skill_b"]:
                d = Path(tmp) / name
                d.mkdir()
                (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---")
            loader = SkillsLoader([str(tmp)])
            assert "skill_a" in loader.names
            assert "skill_b" in loader.names
