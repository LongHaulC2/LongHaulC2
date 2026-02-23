# Logging Guides:

Please follow the logging guides for consistent logging

## 1. Getting the Logger

**Never** use `logging.getLogger(__name__)`. Always use `structlog` to ensure keyword arguments and context binding work.

```python
import structlog
logger = structlog.get_logger(__name__)

```

## 2. The Golden Rule: Key-Value Pairs

Avoid f-strings or `%` formatting in log messages. Use a static message and pass data as keyword arguments.

* **BAD:** `logger.info(f"User {user_id} logged in from {ip}")`
* **GOOD:** `logger.info("user logged in", user_id=user_id, ip=ip)`

*Reasoning: Static messages allow for easy log grouping/filtering, and keys allow for precise searching in log aggregators.*

---

## 3. Using Contextual Binding

If you are performing multiple operations for a specific task (e.g., a Neo4j update or an upload), **bind** the context once to a local logger. This keeps loggers local, and WAY easier to track/keep clean.

```python
def process_task(task_name, task_id):
    # This 'log' instance now carries these keys for every subsequent call
    log = logger.bind(task=task_name, task_id=task_id)

    log.info("starting process")
    try:
        # ... logic ...
        log.info("step 1 complete")
    except Exception as e:
        log.error("task failed", error=e)

```

---

## 4. Error Handling

When logging exceptions, pass the exception object directly to the `error` key. Our pipeline is configured to format these automatically. 

```python
try:
    result = 1 / 0
except Exception as e:
    # Do not use f-string for 'e'
    logger.error("math_error", error=e)

```

---

## 5. Log Levels

| Level | Use Case |
| --- | --- |
| **DEBUG** | High-volume data (e.g., raw hex bytes, packet dumps, loop iterations). |
| **INFO** | General milestones (e.g., "Implant connected", "Task dispatched"). |
| **WARNING** | Non-fatal issues (e.g., "Retrying connection", "Deprecated command used"). |
| **ERROR** | Serious issues that stop a specific task but not the whole server. |
| **CRITICAL** | System-wide failure (e.g., Neo4j DB is down, Port 80 is blocked). |

---


## 6. Helpful Tips

* **Keep keys consistent:** Always use `task_id`, not sometimes `tid` or `taskID`.
* **Don't log secrets:** Never log API keys, passwords, or raw session tokens.
* **Watch object sizes:** Avoid logging massive lists or full file contents; log `len(list)` or a `preview[:20]` instead.
* **Local Overrides:** Use `log.new()` to clear bound variables or `log.unbind("key")` to drop a specific one.
