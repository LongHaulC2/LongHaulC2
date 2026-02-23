# LongHaulC2: Development Standards

To keep our C2 framework maintainable and forensic-friendly, we enforce strict formatting and structured logging.

If this is your first time working with pre-commit hooks, formatters, and other CICD BS, don't worry, I've tried to make it as easy as possible to understand. 

## 1. The Tooling Stack

* **Ruff:** A python all-in-one checker tool. It handles logic errors, import sorting, formatting and **enforces structured logging**. 
    - RUFF is ran in VScode if configured (see `Local Environment Setup`), and again on pre-commit.

* **Pre-commit:** The annoying *ackchyually* asshole of the project. It runs `Ruff`, `trailing-whitespace`, and `end-of-file-fixer` automatically before every commit to enforce a few codebase rules 



## 2. Configuration (`pyproject.toml`)

Our `pyproject.toml` is the source of truth for the project. It sets the line length to **120** and tells Ruff which loggers to watch. This has nothing to do with pre-commit hooks, it's just a big
settings file for python, and associated tools.

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

## 4. Exclusions:

Sometimes, Ruff will flag code that is intentional (like "side-effect" imports for NiceGUI/Flask, `client/src/client/main.py`, or debugging variables). You can use a `# noqa` comment to tell the linter to ignore a specific line.

You can check each err with: `ruff rule <rule_code>`

### Common Suppression Codes

| Code | Violation | Description |
| --- | --- | --- |
| **`F401`** | Unused Import | Module is imported but never used in the code. |
| **`F841`** | Unused Variable | A local variable is defined but never used. |
| **`G004`** | Logging f-string | Using an f-string instead of extra arguments in a log. |
| **`E402`** | Import Not at Top | An `import` statement is not at the very beginning of the file. |
| **`S101`** | Assert Used | Use of the `assert` keyword (which can be optimized away). |
| **`S110`** | `try-except-pass` | Catching an exception and doing nothing with it. |

Apply these like this:
`import client.src.client.pages.docs # noqa: F401`

and please include a comment above why:

```
# Nicegui registers pages on import, this is not "unused"
import client.src.client.pages.docs # noqa: F401
```

Or, you can apply them to the whole file, but this gets messy, so please avoid:
```
# ruff: noqa: E402, F401
```

### Project specific error messages
There are a few project specific messages I've updated to reflect the fixes properly:

```
# recommend user use structlog instead of the usual % formatter  
"G004" = "Use structlog format: server_logger.debug('message', error=e)"
```
---

## 5. Quick Commands

* **Install Hooks:** `pip install pre-commit && pre-commit install`
* **Manual Check:** `pre-commit run --all-files`
* **Skip Hooks (Emergency only):** `git commit -m "msg" --no-verify`
* **Run ruff manually**: `ruff check --fix .`
