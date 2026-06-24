# Commenting Guidelines:

To maintain the **LongHaulC2** aesthetic, comments must be clean, intentional, and Ruff-compliant. Ruff enforces **E262** (exactly one space after the `#`) and **E265** (no leading/trailing space for block dividers).

### The "Better Comments" Hierarchy

We use specific tags for instant visual scanning. **Ruff Note:** Always ensure there is exactly one space between the `#` and the tag.

* **`# !` [WARNING]:** Warnings,
* **`# ?` [QUESTION]:** Logic you're unsure about or a temporary workaround.
* **`# TODO` [TODO]:** Stuff to do *later*
---

### Structural Headers

For large logical separations, use the **Technical Header** snippet. To satisfy Ruff’s formatting rules, ensure there are no trailing characters after the final `#` and the spacing is consistent.

```python
# ==============================================================================
# PAYLOAD GENERATION LOGIC
# ==============================================================================

```

You can add this to VSCODE by placing in the following file:

`.vscode/comment.code-snippets`:

```
{
  "Tech Header": {
    "prefix": "thdr",
    "body": [
      "# ========================================",
      "# ${1:HEADER_TITLE}",
      "# ========================================",
    ],
    "description": "Header"
  }
}

```

### General Principles

* **Space After Hash:** Ruff Rule `E262` requires `# comment`, not `#comment`.
* **Intent > Action:** Explain *why* (e.g., `# ! UI needs 100ms delay to prevent race conditions`).
* **High & Tight:** Keep it short. If it’s longer than 3 lines, use a docstring (`"""`).
* **Clarity:** Avoid ambiguity when possible. It sucks to come back to a comment that made sense yesterday, but is completely out of context today

---

### Code Examples

```python
# ! WARNING: Ensure encryption keys are never logged to console
def encrypt_payload(data: bytes):
    ...

# ? Do we need to increase this interval for high-latency implants?
ui.timer(5.0, check_health)

# TODO: Sanity check that old build files get removed
def compile_artifact():
    ...

```

### Suppression Comments (`noqa`)

When using `# noqa` to suppress a Ruff error, explain *why*

```python
import client.src.client.pages.listeners  # noqa: F401 (Registers pages on import)

```
or

```python
# Registers pages on import
import client.src.client.pages.listeners  # noqa: F401
```

