# Testing Overview

LongHaulC2 has three tiers of tests. Run them in order of dependency: UI smoke first (no stack needed), server API second (stack needed, no implant), integration last (full stack + Windows implant, CI only).

---

## Quick Reference

| Make target | What it runs | Requires |
|---|---|---|
| `make web_tests` | UI smoke tests (NiceGUI pages render, auth guards fire) | Nothing — no server, no implant |
| `make server_tests` | API tests — all endpoints, auth, CRUD, task queuing | Server + Docker containers running |
| `make local_tests` | Both of the above in one shot | Server + Docker containers running |
| `make integration_test` | Full E2E with a real implant checking in | Full CI stack + live Windows implant |
| `make no_fail_test` | Integration tests, failures allowed | Full CI stack |

---

## Tier 1 — UI Smoke Tests

```bash
make web_tests
```

**No server, no implant needed.**

These tests run against a real in-process NiceGUI app — no browser, no network calls. They verify pages render without crashing and key static labels are present.

**What they test:**
- `/login` — key labels render (LONGHAULC2, USERNAME, PASSWORD, LOGIN)
- `/scripts` — editor, file picker, terminal sections render
- `/filestore` — page renders
- `/status` — SYSTEM STATUS, CORE, LISTENERS labels present
- `/comms` — page renders
- `/settings` — USER SETTINGS, Element Auto Refresh Rate present
- `/operations`, `/listeners`, `/payloads` — **auth guard is active**: since no session is set, `setup_menu()` redirects to `/login`. Tests verify the redirect fires by asserting login page labels appear.

**Pages excluded from smoke tests:**

Graph (`/graph`) and all node detail pages (`/implant/`, `/listener/`, `/payload/`, `/host/`) make unconditional API calls on page load. Without a running server they throw an unhandled exception and return a 500. They are commented out in `tests/web/web_tests.py`. Use the integration test suite to exercise these pages.

**Rule for new pages:** If a page makes API calls on load without first checking `app.storage.user.get("api_host")`, it will crash `make web_tests`. Add an auth guard (same pattern as `setup_menu()`) or the page cannot be smoke-tested without a running server.

---

## Tier 2 — Server API Tests

```bash
make server_tests
```

### Prerequisites

1. **Docker containers running:**
   ```bash
   make start_docker_images
   ```
2. **Server running** (separate terminal):
   ```bash
   PYTHONPATH=. python -m server.main
   ```
3. **Port 19099 must be free** — listener tests bind a real HTTP listener to `127.0.0.1:19099`. If another process holds that port the listener fixture fails and the entire listener test file errors out. Check with `ss -tlnp | grep 19099`.

If tests fail immediately with a connection error, the server isn't running or isn't reachable.

### Environment overrides

Default target is `http://localhost:45045` with the dev credentials from `.env`. Override at runtime:

```bash
SERVER_URL=http://myhost:45045 TEST_API_USER=admin TEST_API_PASS=hunter2 make server_tests
```

### Run a single file

```bash
PYTHONPATH=. venv/bin/python -m pytest -v -s tests/server/test_auth.py
```

### How authentication works in tests

`tests/server/conftest.py` defines a session-scoped `api_client` fixture that authenticates on first use and injects `Authorization: Bearer <token>` into every subsequent request for that session. Individual tests that need to test unauthenticated behavior use a plain `requests` call with no headers.

### What each test file covers

| File | Tests | Description |
|---|---|---|
| `test_auth.py` | 8 | Login success/failure, token refresh, register (authed and unauthed), malformed/expired token rejection |
| `test_health.py` | 2 | Health check returns 200; returns 401 without a token |
| `test_implants.py` | 12 | Full CRUD, task queuing, task history retrieval, implant search, history search |
| `test_listeners.py` | 10 | Full CRUD, start/stop via PATCH `{"active": true/false}`, 400 on missing `active` field |
| `test_filestore.py` | 7 | Upload, download (binary), delete, missing-field 400, nonexistent UUID handling |
| `test_build.py` | 5 | Submit a build job and verify acceptance (HTTP 200 + `build_uuid`). Does **not** poll for completion — the cross-compiler toolchain is not present on dev machines. Use the integration test for build validation. |

### Shared fixtures (`tests/server/conftest.py`)

All fixtures are function-scoped (except `api_client`) and clean up after themselves even on failure:

| Fixture | Scope | What it does |
|---|---|---|
| `api_client` | session | Authenticates once, yields an authenticated `FullC2APIClient` |
| `listener_uuid` | function | Creates a listener on `127.0.0.1:19099`, yields its UUID, deletes it on teardown |
| `implant_uuid` | function | Creates a blank implant entry, yields its UUID, deletes it on teardown |
| `file_uuid` | function | Uploads a small test file, yields its UUID, deletes it on teardown |

`FullC2APIClient` is a subclass of the integration-test `C2APIClient` that adds the methods not present in the base: `post_authentication`, `post_authentication_refresh`, `post_authentication_register`, `patch_listener`, `get_health`, `post_filestore`, `get_filestore`, `get_file`, `delete_file`, `get_graph`, `post_graph_search`.

---

## Tier 3 — Integration Tests (CI only)

```bash
make integration_test
```

Requires a full running stack and a live Windows implant checked in. These only run in CI. See `tests/integration_test/` for details.

```bash
make no_fail_test   # same, but exits 0 even on failure — useful for exploring CI state
```

---

## Test Infrastructure Notes

- **pytest version:** 9.0.2
- **pytest-asyncio version:** 1.4.0 (required — earlier versions in lock file were nonexistent on PyPI and caused silent failures for async fixtures)
- **NiceGUI testing plugin:** loaded via `addopts = -p nicegui.testing.user_plugin` in `pytest.ini`
- `asyncio_mode = auto` in `pytest.ini` — all `async def` test functions and fixtures are automatically treated as asyncio
- `@pytest.mark.nicegui_main_file('client/main.py')` — must point to the real entry point; NiceGUI raises `FileNotFoundError` if the path doesn't exist
