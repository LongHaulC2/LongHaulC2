# LongHaulC2: Development Standards

To keep our C2 framework maintainable and forensic-friendly, we enforce strict formatting and structured logging.

If this is your first time working with pre-commit hooks, formatters, and other CICD BS, don't worry, I've tried to make it as easy as possible to understand. 

## 1. The Tooling Stack

* **Ruff:** A python all-in-one checker tool. It handles logic errors, import sorting, formatting and **enforces structured logging**. 
    - RUFF is ran in VScode if configured (see `Local Environment Setup`), and again on pre-commit.

* **Pre-commit:** The annoying *ackchyually* asshole of the project. It runs Ruff automatically before every commit to enforce a few codebase rules 



## 2. Configuration (`pyproject.toml`)

Our `pyproject.toml` is the source of truth for the project. It sets the line length to **120** and tells Ruff which loggers to watch. This has nothing to do with pre-commit hooks, it's just a big
settings file for python, and associated tools.

```toml
# hi! This configures the python global settings for the project.

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
    "*.h",    # exclude implant source
    "*.hpp",  # exclude implant source
    "*.c",    # exclude implant source
    "*.cpp",  # exclude implant source
    "*.md"    # exclude docs
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

## 3. Local Environment Setup

Set this up once, and you'll almost never see a pre-commit error because your editor will fix the code every time you hit Save.

Install the **Ruff** extension from the Marketplace.

Open your settings.json (Ctrl+Shift+P -> Open User Settings (JSON)).

Add/Update this block:

"[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports.ruff": "explicit",
        "source.fixAll.ruff": "explicit"
    },
    "editor.rulers": [120]
}


### Pre-commit Hooks

These run when commiting your files, to enforce code standards. 

The hooks run in this order:

2. **Ruff** fixes imports and checks for f-strings in logs, and formats
3. **Hooks** check for trailing whitespace and large files.

**If a hook modifies a file:** Git will abort the commit. You must `git add .` the changes and commit again.

---

## 5. Quick Commands

* **Install Hooks:** `pip install pre-commit && pre-commit install`
* **Manual Check:** `pre-commit run --all-files`
* **Skip Hooks (Emergency only):** `git commit -m "msg" --no-verify`
