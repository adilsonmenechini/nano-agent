"""Tests for TodoTool branch coverage."""

from __future__ import annotations

import json

import pytest

from nanoagent.agent.tools.todo import TodoTool


@pytest.fixture()
def tmp_tool(tmp_path):
    """TodoTool backed by a temp file (actual file exists after _ensure_storage_file)."""
    path = tmp_path / "todos.json"
    return TodoTool(storage_file=str(path)), path


class TestTodoToolStorage:
    def test_creates_file_on_init(self, tmp_path):
        path = tmp_path / "new.json"
        assert not path.exists()
        TodoTool(storage_file=str(path))
        assert path.exists()
        with open(path) as f:
            assert json.load(f) == []


class TestTodoToolAdd:
    def test_add_task_returns_message(self, tmp_tool):
        tool, path = tmp_tool
        result = tool.execute("add", task="buy milk")
        assert result == "Added todo: buy milk"
        with open(path) as f:
            todos = json.load(f)
        assert len(todos) == 1
        assert todos[0]["task"] == "buy milk"
        assert todos[0]["id"] == 1
        assert todos[0]["completed"] is False
        assert todos[0]["priority"] == 2
        assert todos[0]["due_date"] is None

    def test_add_auto_increments_id(self, tmp_tool):
        tool, path = tmp_tool
        # Pre-populate
        with open(path, "w") as f:
            json.dump(
                [
                    {
                        "id": 3,
                        "task": "x",
                        "completed": False,
                        "priority": 1,
                        "due_date": None,
                    }
                ],
                f,
            )
        result = tool.execute("add", task="new task")
        assert result == "Added todo: new task"
        with open(path) as f:
            todos = json.load(f)
        assert todos[-1]["id"] == 4

    def test_add_missing_task_returns_error(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("add")
        assert "task description" in result

    def test_add_with_priority_and_due(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="urgent", priority=1, due_date="2025-01-01")
        with open(path) as f:
            todos = json.load(f)
        assert todos[0]["priority"] == 1
        assert todos[0]["due_date"] == "2025-01-01"

    def test_add_default_priority_is_2(self, tmp_tool):
        tool, _ = tmp_tool
        # task + no priority → priority=2
        tool.execute("add", task="x")
        # Force list to see outcome indirectly
        todos = tool._load_todos()
        assert todos[0]["priority"] == 2


class TestTodoToolList:
    def test_list_empty(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("list")
        assert result == "No todos"

    def test_list_all(self, tmp_tool):
        tool, path = tmp_tool
        for t in ["a", "b", "c"]:
            tool.execute("add", task=t)
        result = tool.execute("list")
        assert "1:" in result
        assert "3:" in result

    def test_list_pending(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="pending")
        tool.execute("add", task="done")
        todos = tool._load_todos()
        todos[1]["completed"] = True
        tool._save_todos(todos)
        result = tool.execute("list", list_pending=True)
        assert "pending" in result
        assert "done" not in result

    def test_list_completed(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="done1")
        tool.execute("add", task="todo")
        todos = tool._load_todos()
        todos[0]["completed"] = True
        tool._save_todos(todos)
        result = tool.execute("list", list_completed=True)
        assert "done1" in result
        assert "todo" not in result

    def test_list_all_includes_all_when_no_flags(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="x")
        todos = tool._load_todos()
        todos[0]["completed"] = True
        tool._save_todos(todos)
        result = tool.execute("list")
        assert "x" in result

    def test_list_format_priority_and_due(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="report", priority=1, due_date="2025-03-01")
        tool.execute("add", task="note", priority=3)
        result = tool.execute("list")
        assert "!!!" in result  # priority 3
        assert "(due: 2025-03-01)" in result
        # priority 1 → "!"
        assert "!" in result

    def test_list_completed_checkbox(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="done")
        todos = tool._load_todos()
        todos[0]["completed"] = True
        tool._save_todos(todos)
        result = tool.execute("list")
        assert "✓" in result

    def test_list_priority_out_of_range(self, tmp_tool):
        tool, path = tmp_tool
        # Write directly to bypass validation
        with open(path, "w") as f:
            json.dump(
                [
                    {
                        "id": 1,
                        "task": "x",
                        "completed": False,
                        "priority": 99,
                        "due_date": None,
                    }
                ],
                f,
            )
        result = tool.execute("list")
        assert "??" in result


class TestTodoToolComplete:
    def test_complete_success(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="do it")
        result = tool.execute("complete", task_id=1)
        assert "Completed todo 1" in result
        with open(path) as f:
            todos = json.load(f)
        assert todos[0]["completed"] is True

    def test_complete_missing_id(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("complete")
        assert "task_id is required" in result

    def test_complete_not_found(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("complete", task_id=5)
        assert "not found" in result


class TestTodoToolUpdate:
    def test_update_task(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="old")
        tool.execute("update", task_id=1, task="new")
        with open(path) as f:
            todos = json.load(f)
        assert todos[0]["task"] == "new"

    def test_update_missing_id(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("update")
        assert "task_id is required" in result

    def test_update_priority_valid(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="x", priority=2)
        tool.execute("update", task_id=1, priority=1)
        with open(path) as f:
            todos = json.load(f)
        assert todos[0]["priority"] == 1

    def test_update_priority_out_of_range(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="x")
        result = tool.execute("update", task_id=1, priority=5)
        assert "priority" in result and "1, 2, or 3" in result

    def test_update_due_date(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="x")
        tool.execute("update", task_id=1, due_date="2025-06-01")
        with open(path) as f:
            todos = json.load(f)
        assert todos[0]["due_date"] == "2025-06-01"

    def test_update_completed(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="x")
        tool.execute("update", task_id=1, completed=True)
        with open(path) as f:
            todos = json.load(f)
        assert todos[0]["completed"] is True

    def test_update_not_found(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("update", task_id=9)
        assert "not found" in result


class TestTodoToolDelete:
    def test_delete_success(self, tmp_tool):
        tool, path = tmp_tool
        tool.execute("add", task="remove me")
        result = tool.execute("delete", task_id=1)
        assert "Deleted todo 1" in result
        with open(path) as f:
            todos = json.load(f)
        assert len(todos) == 0

    def test_delete_missing_id(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("delete")
        assert "task_id is required" in result

    def test_delete_not_found(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("delete", task_id=2)
        assert "not found" in result


class TestTodoToolUnknown:
    def test_unknown_action_returns_error(self, tmp_tool):
        tool, _ = tmp_tool
        result = tool.execute("foobar")
        assert "unknown action" in result
        assert "add" in result
