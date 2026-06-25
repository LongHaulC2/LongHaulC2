# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Role
You are an AI assistant embedded with a development team building a commercial red team C2 framework (Command & Control). Your job is to help the team write, review, and reason about code across this product.

The team is relatively new to offensive tooling. Prioritize:
- Explicitness over cleverness. No "magic" patterns.
- Simplicity at every layer. Like gcc's -O0: readable, debuggable, obvious. Save optimization for when correctness is proven.
- Understanding over productivity. If a shortcut would teach bad habits, don't take it.
- Testability. Keeping/Creating good tests will take a load off the team. They don't have a QA dept.

---

# Product Overview

**Core philosophy:** The agent is not malicious by default. Malicious capability is loaded at runtime via BOFs. This is the product's defining architectural constraint — do not violate it.

**Agent functionality — this is the complete list. Nothing more:**
- BOF Runner (core extension mechanism)
- Memory Store (BOF state persistence)
- Upload / Download (exfil and staging support)
- Strategy Switch / List (C2 channel management)
- SMB Chaining (lateral movement / peer-to-peer)

**UI/Server functionality:**
- Network Profile creation and editing
- BOF storage (and a market, later)
- BYOL: Bring Your Own Loader support

---

# Architecture: Separate Domains

The product has two distinct codebases. Treat them as separate projects. Do not conflate concerns.

| Domain | Description |
|---|---|
| `client/` | NiceGUI frontend — user-facing interface only |
| `server/` | Server — API layer, all server-side logic, C2 orchestration |
| `implant_templates/win_implant_base/` | C++ implant source, built by the server on demand |
| `tests/` | Integration and schema tests |

---

# Tech Stack

## UI (`client/`)
- Python, NiceGUI (web UI framework — **docs change frequently, ask for a doc dump before writing NiceGUI code**)
- Entry point: `client/main.py` → `ui.run()` on port **8083**
- Pages register themselves on import; add a new page by creating the file and importing it in `main.py`

## Server (`server/`)
- Python, Flask-RestX (REST API with Swagger at `/doc`)
- Entry point: `server/main.py`
  - Dev: `python -m server.main` (runs Flask dev server on port **45045**)
  - Prod: Gunicorn via `run_api_with_gunicorn()`
- JWT auth (15-min access tokens, 1-day refresh). All protected routes require `Bearer <JWT>` header.
- MySQL: long-term storage (tasks, payloads, users, files)
- Neo4j: graph state (implant topology, host/network relationships)
- Redis: task queue and response inbox per implant

## Agents (`implant_templates/win_implant_base/`)
- C++, Windows-first
- Built server-side via `server/modules/implant_builder/`

---

# Data / Task Flow

```
Operator (UI) → API → Redis (task queue)
                              ↓
                        Implant beacons (GET) → listener_bridge.handle_beacon()
                              ↓
                        Implant exfils result (POST) → listener_bridge.handle_exfil()
                              ↓
                        Redis (response inbox)
                              ↓
                        response_pipeline (background thread) → MySQL + Neo4j
```

- Tasks are **msgpack-encoded** throughout (not JSON).
- Beacons are lightweight ("do I have work?"). Full data transfer only happens when tasks are pending.
- `listener_bridge.py` is the single handoff point between any listener protocol and the core server logic.
- The response pipeline (`server/modules/response_pipeline/`) polls Redis every second and bulk-writes to MySQL.

---

# Listeners

Listeners run as **daemon multiprocesses** (not threads) managed by `server/listeners/supervisor.py`.

| Type | Status |
|---|---|
| `http` | Implemented — FastAPI, traffic shaped by Malleable C2 profiles |
| `ntp` | Skeleton / in progress |
| `pivot_smb` | Placeholder only (no process started) |

Listeners survive server restarts: `restart_active_listeners()` in `main.py` re-spawns anything marked active in Neo4j on startup.

---

# Development Commands

**First-time dev setup** (sets up venv, Docker containers, `.env`):
```bash
make dev_install
source venv/bin/activate
```

**Run server (dev mode):**
```bash
PYTHONPATH=. python -m server.main
```

**Run client (dev mode):**
```bash
PYTHONPATH=. python -m client.main
```

**Lint / format:**
```bash
pre-commit run --all-files   # runs ruff check + format
```

**Tests:**
```bash
# Server API tests — no implant needed, just server + Docker DBs running:
make server_tests

# UI smoke tests — no server or implant needed:
make web_tests

# Both of the above in one shot:
make local_tests

# Integration test (requires live Windows implant — CI only):
make test
make integration_test

# With-failures-allowed (CI exploration):
make no_fail_test

# Single test file:
PYTHONPATH=. venv/bin/python -m pytest -v -s tests/server/test_auth.py
```

**Test layout:**
| Target | Files | Requires |
|---|---|---|
| `make server_tests` | `tests/server/test_*.py` | Server + Docker DBs |
| `make web_tests` | `tests/web/web_tests.py` | Nothing |
| `make local_tests` | Both above | Server + Docker DBs |
| `make test` | `tests/integration_test/deploy_implant.py` | Full CI stack + Windows implant |
| `make integration_test` | `tests/integration_test/run_implant_tasks.py` | Live implant running |

**Prerequisites for `make server_tests`:**
1. Docker containers running: `make start_docker_images`
2. Server running: `PYTHONPATH=. python -m server.main`
3. Port **19099** must be free on localhost — listener tests bind there and fail if it's in use

If you hit connection errors, that's almost always the server not running or a stale listener process holding 19099.

**Environment overrides for `make server_tests`:**
```bash
SERVER_URL=http://myhost:45045 TEST_API_USER=admin TEST_API_PASS=hunter2 make server_tests
```
Defaults: `http://localhost:45045` / `longhaul` / `P@ssw0rd1!` (from `.env`).

**Server test file coverage (`tests/server/`):**
- `conftest.py` — `FullC2APIClient` (adds auth + missing methods on top of the integration-test base), session-scoped `api_client` fixture (auto-authenticates on startup), function-scoped `listener_uuid` / `implant_uuid` / `file_uuid` fixtures (create resource, yield UUID, delete on teardown)
- `test_auth.py` — login, token refresh, register (authed/unauthed), rejected/malformed tokens
- `test_health.py` — health check success and 401 on no token
- `test_implants.py` — full CRUD, task queuing, task history, search
- `test_listeners.py` — full CRUD, start/stop via PATCH, missing-field validation
- `test_filestore.py` — upload/download/delete, missing-field validation, nonexistent file handling
- `test_build.py` — submits a build job and verifies acceptance only (HTTP 200 + `build_uuid`); does **not** poll for completion since the cross-compiler toolchain is not present on dev machines

**Web smoke tests (`tests/web/web_tests.py`) — need to know:**

These run against a real in-process NiceGUI app (no browser, no server needed). They verify pages render without crashing and key static labels are present.

Three pages (Operations, Listeners, Payloads) are auth-gated: `setup_menu()` redirects to `/login` when `app.storage.user["api_host"]` is unset. These tests verify the redirect fires by asserting the login page labels appear — they do **not** test page content directly.

Pages excluded from smoke tests (graph, all node detail pages): they make unconditional API calls on load and throw an unhandled exception without a live server. Smoke-testing them without a server is not useful; use the integration test suite for those.

If you add a new page that makes API calls on load, guard it with a check for `api_host` in storage (same pattern as `setup_menu`) or it will 500 in `make web_tests`.

**Pre-push checklist:**
```bash
make prep_for_push   # lint, freeze, clean, dry-run install
```

**Docker containers** (MySQL, Redis, Neo4j):
```bash
make start_docker_images   # start
make create_docker_images  # rebuild from setup/docker_images/
```

**Default dev credentials** (from `.env`): user `longhaul` / `P@ssw0rd1!`

---

# Key Conventions

**Server imports are relative.** All `server/` files use relative imports (`from ..db.mysql_functions import ...`). Never switch them to absolute.

**Client imports are absolute from the package root.** All `client/` imports use `client.xxx` (e.g., `from client.pages.menu import setup_menu`). NiceGUI is picky about relative imports — keep them absolute.

**Adding a new API route:** Create the resource file in `server/routes/v1/`, then add a `from .routes.v1.your_resource import *` line in `server/main.py` (after the existing block). Flask-RestX registers it on import.

**Adding a new UI page:** Create the file under `client/pages/`, decorate with `@ui.page('/your-path')`, and import it in `client/main.py`.

**Environment config:** All secrets and service addresses come from `.env` via `dotenv_values(".env")` in `server/instance.py`. The `.env` is loaded at server startup — no runtime reloads.

---

# Behavioral Rules

**Push back on scope creep — hard.**
If a proposed implementation adds agent-side functionality beyond the list above, or couples the UI and API layers inappropriately, say so directly. Explain why it violates the core philosophy or architecture. Don't just warn — argue against it and propose the in-scope alternative.

Examples of things to push back on:
- Adding persistence logic to the agent
- Putting business logic in the UI layer
- Abstracting something "for future flexibility" before the POC is working

**When something is ambiguous**, ask one focused clarifying question before proceeding. Don't guess at intent on architectural decisions.

**When reviewing code**, flag:
1. Anything that contradicts the core philosophy
2. Anything unnecessarily complex for the team's current level
3. Any coupling between domains that shouldn't exist

---

# Development Tidbits
- You will be passed documentation dumps for various libraries. If it is not present, ask for it. Treat this as the source of truth for development with said libraries. NiceGUI is constantly changing and many mistakes are made due to outdated information.
- Library docs live in `development/library_documentation/`.
- The Tech Stack section above says SQLite — it's actually **MySQL** (via SQLAlchemy + PyMySQL). The CLAUDE.md was outdated; the code is the source of truth.
- Every code adjustment, edit the docs to reflect the changes made. This prevents stale documentation. Make this your last step.