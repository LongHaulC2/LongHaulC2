# LongHaulC2: Development Standards

To keep our C2 framework maintainable and forensic-friendly, we enforce strict formatting and structured logging.

## 1. The Tooling Stack

* **Black:** Our "Brush." It handles code layout (spacing, line wraps).
* **Ruff:** Our "Brain." It handles logic errors, import sorting, and **enforces structured logging**.
* **Pre-commit:** The "Gatekeeper." It runs these tools automatically before every commit.

---

## 2. Structured Logging Standards

**Rule:** Never use f-strings in log messages. Pass data as keyword arguments.

* **Bad:** `logger.info(f"Implant {uuid} connected")`
* **Good:** `logger.info("implant connected", uuid=uuid)`

### Contextual Binding

When working within a specific task (e.g., a Neo4j pipeline), bind the context to a local logger instance.

```python
def process_data(task_id):
    log = logger.bind(task_id=task_id)
    log.info("starting task") # Automatically includes task_id

```

---

## 3. Configuration (`pyproject.toml`)

Our `pyproject.toml` is the source of truth. It sets the line length to **120** and tells Ruff which loggers to watch.

```toml
# hi! This configures the python global settings for the project.

[tool.ruff]
target-version = "py312"
line-length = 120

exclude = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "build",
    "dist",
    "logs",
    ".h",    # exclude implant source
    ".hpp",  # exclude implant source
    ".c",    # exclude implant source
    ".cpp",  # exclude implant source
    ".md"    # exclude docs
]

[tool.ruff.lint]
# G = Logging, E/F = Syntax/Logic, I = Import Sorting
select = ["G", "E", "F", "I"]
# Tell Ruff which variable names are actually loggers
logger-objects = [
    "api_logger",
    "server_logger",
    "listener_logger",
    "neo4j_logger",
    "response_pipeline_logger"
]

[tool.ruff.format]
# This ensures Ruff's formatter behaves like Black
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
```

---

## 4. Local Environment Setup

### IDE (VS Code)

Ensure your `settings.json` is configured to **Format on Save**. This prevents "Pre-commit" from failing because the tools will have already fixed the code.

1. Install the **Black Formatter** and **Ruff** extensions.
2. Set `editor.formatOnSave: true`.
3. Set `editor.defaultFormatter: ms-python.black-formatter`.

Example:

```

"[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports.ruff": "explicit",
            "source.fixAll.ruff": "explicit"
        },
        "editor.rulers": [120]
    },

```


### Pre-commit Hooks

The hooks run in this order:

2. **Ruff** fixes imports and checks for f-strings in logs, and formats
3. **Hooks** check for trailing whitespace and large files.

**If a hook modifies a file:** Git will abort the commit. You must `git add .` the changes and commit again.

---

## 5. Quick Commands

* **Install Hooks:** `pip install pre-commit && pre-commit install`
* **Manual Check:** `pre-commit run --all-files`
* **Skip Hooks (Emergency only):** `git commit -m "msg" --no-verify`
