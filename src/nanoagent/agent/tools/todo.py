from .base import BaseTool
from typing import List, Dict, Any
import json
import os

class TodoTool(BaseTool):
    def __init__(self, storage_file: str = "todos.json"):
        super().__init__(
            name="todo",
            description="Manages a todo list: add, list, complete tasks with priority and due date"
        )
        self.storage_file = storage_file
        self._ensure_storage_file()

    def _ensure_storage_file(self):
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump([], f)

    def _load_todos(self) -> List[Dict[str, Any]]:
        with open(self.storage_file, 'r') as f:
            return json.load(f)

    def _save_todos(self, todos: List[Dict[str, Any]]):
        with open(self.storage_file, 'w') as f:
            json.dump(todos, f, indent=2)

    def execute(self, action: str, task: str = None, task_id: int = None, 
                priority: int = None, due_date: str = None, 
                completed: bool = None, list_all: bool = False,
                list_completed: bool = False, list_pending: bool = False) -> Any:
        """
        Perform actions on the todo list.
        Actions: add, list, complete, update, delete
        For add: task is required, priority and due_date are optional
        For list: can specify list_all, list_completed, list_pending
        For complete: task_id is required
        For update: task_id is required, and at least one of task, priority, due_date, completed
        For delete: task_id is required
        """
        todos = self._load_todos()
        if action == "add":
            if task is None:
                return "Error: task description is required for add action"
            # Determine the next ID
            next_id = 1
            if todos:
                next_id = max(todo["id"] for todo in todos) + 1
            todo = {
                "id": next_id,
                "task": task,
                "completed": False,
                "priority": priority if priority is not None else 2,  # default medium
                "due_date": due_date
            }
            todos.append(todo)
            self._save_todos(todos)
            return f"Added todo: {task}"
        elif action == "list":
            # Filter todos based on flags
            filtered = todos
            if list_completed:
                filtered = [todo for todo in todos if todo["completed"]]
            elif list_pending:
                filtered = [todo for todo in todos if not todo["completed"]]
            # If none of the flags are set, list all
            if not (list_all or list_completed or list_pending):
                filtered = todos

            if not filtered:
                return "No todos"
            result = []
            for todo in filtered:
                status = "✓" if todo["completed"] else " "
                priority_str = ["!", "!!", "!!!"][todo["priority"]-1] if 1 <= todo["priority"] <= 3 else "??"
                due_str = f" (due: {todo['due_date']})" if todo["due_date"] else ""
                result.append(f"[{status}] {priority_str} {todo['id']}: {todo['task']}{due_str}")
            return "\n".join(result)
        elif action == "complete":
            if task_id is None:
                return "Error: task_id is required for complete action"
            for todo in todos:
                if todo["id"] == task_id:
                    todo["completed"] = True
                    self._save_todos(todos)
                    return f"Completed todo {task_id}: {todo['task']}"
            return f"Error: todo with id {task_id} not found"
        elif action == "update":
            if task_id is None:
                return "Error: task_id is required for update action"
            for todo in todos:
                if todo["id"] == task_id:
                    if task is not None:
                        todo["task"] = task
                    if priority is not None:
                        if 1 <= priority <= 3:
                            todo["priority"] = priority
                        else:
                            return "Error: priority must be 1, 2, or 3"
                    if due_date is not None:
                        # We could validate the date format, but for now we'll just store it
                        todo["due_date"] = due_date
                    if completed is not None:
                        todo["completed"] = completed
                    self._save_todos(todos)
                    return f"Updated todo {task_id}"
            return f"Error: todo with id {task_id} not found"
        elif action == "delete":
            if task_id is None:
                return "Error: task_id is required for delete action"
            for i, todo in enumerate(todos):
                if todo["id"] == task_id:
                    del todos[i]
                    self._save_todos(todos)
                    return f"Deleted todo {task_id}"
            return f"Error: todo with id {task_id} not found"
        else:
            return f"Error: unknown action '{action}'. Valid actions: add, list, complete, update, delete"