# Tool Schema Contracts

## LLM-Facing Tool Schemas

These are the JSON Schemas generated automatically via the `@tool` decorator and presented to LLM providers (OpenAI/Anthropic).

### run_shell

```json
{
  "type": "function",
  "function": {
    "name": "run_shell",
    "description": "Execute a shell command and return stdout, stderr, and exit code",
    "parameters": {
      "type": "object",
      "properties": {
        "command": {
          "type": "string",
          "description": "Shell command to execute"
        },
        "timeout": {
          "type": "integer",
          "description": "Timeout in seconds",
          "default": 30
        },
        "workdir": {
          "type": "string",
          "description": "Working directory (empty for project root)",
          "default": ""
        }
      },
      "required": ["command"]
    }
  }
}
```

### read_file

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a file's contents from an absolute path",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Absolute path to the file"
        }
      },
      "required": ["path"]
    }
  }
}
```

### write_file

```json
{
  "type": "function",
  "function": {
    "name": "write_file",
    "description": "Write content to a file at an absolute path. Validates path is within project directory.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Absolute path to the file"
        },
        "content": {
          "type": "string",
          "description": "Content to write"
        }
      },
      "required": ["path", "content"]
    }
  }
}
```

### glob_file

```json
{
  "type": "function",
  "function": {
    "name": "glob_file",
    "description": "Find files matching a glob pattern",
    "parameters": {
      "type": "object",
      "properties": {
        "pattern": {
          "type": "string",
          "description": "Glob pattern (e.g., '**/*.py')"
        },
        "path": {
          "type": "string",
          "description": "Directory to search from",
          "default": "."
        }
      },
      "required": ["pattern"]
    }
  }
}
```

### grep_file

```json
{
  "type": "function",
  "function": {
    "name": "grep_file",
    "description": "Search file contents for a regex pattern",
    "parameters": {
      "type": "object",
      "properties": {
        "pattern": {
          "type": "string",
          "description": "Search pattern (regex)"
        },
        "path": {
          "type": "string",
          "description": "Directory to search",
          "default": "."
        },
        "context": {
          "type": "integer",
          "description": "Lines of context before/after match",
          "default": 0
        }
      },
      "required": ["pattern"]
    }
  }
}
```

### git_status

```json
{
  "type": "function",
  "function": {
    "name": "git_status",
    "description": "Show the working tree status (equivalent to 'git status --short')",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Repository path",
          "default": "."
        }
      },
      "required": []
    }
  }
}
```

### git_diff

```json
{
  "type": "function",
  "function": {
    "name": "git_diff",
    "description": "Show unstaged changes (equivalent to 'git diff')",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Repository path",
          "default": "."
        }
      },
      "required": []
    }
  }
}
```

### git_log

```json
{
  "type": "function",
  "function": {
    "name": "git_log",
    "description": "Show recent commit history",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Repository path",
          "default": "."
        },
        "max_count": {
          "type": "integer",
          "description": "Maximum number of commits to show",
          "default": 10
        }
      },
      "required": []
    }
  }
}
```
