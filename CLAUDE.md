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
- Network Profile creation, editing, and preview/rendering
- BOF storage (and a market, later)
- BYOL: Bring Your Own Loader support
- User Management (operator accounts, TOTP 2FA via `pyotp`)
- Operator Chat (server-backed team messaging)

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
- Beacons carry full metadata (including current `get_strategy` / `post_strategy`). Strategy fields are updated in Neo4j on every checkin, not just first registration.
- `listener_bridge.py` is the single handoff point between any listener protocol and the core server logic.
- The response pipeline (`server/modules/response_pipeline/`) polls Redis every second and bulk-writes to MySQL. After writing to MySQL, it calls `correlate_task_results()` which dispatches to task-specific handlers in `neo4j_correlator.py`.
- **File download auto-capture:** When a `file download` task completes successfully, the response pipeline automatically saves the downloaded file to the server filestore with `uploaded_by=implant:<uuid>` and `source_implant` set. The operator still sees the result in the UI, but the file is also persisted without manual intervention.
- **Callback host is decoupled from listener bind address.** The build dialog has a `callback_host` field (IP or hostname) that specifies where the implant sends traffic. This supports CDNs, redirectors, and NAT — the listener can bind to a private IP while the implant calls back to a public one. The port still comes from the listener. Strategy names use the callback host, not the bind address (e.g., `raw_60_1_1_1_80_mylistener` instead of `raw_10_0_0_2_80_mylistener`).

---

# Listeners

Listeners run as **daemon multiprocesses** (not threads) managed by `server/listeners/supervisor.py`.

| Type | Status |
|---|---|
| `raw` | Implemented — plain Python `socket`, wire format fully defined by profile TOML |
| `pivot_smb` | Placeholder only (no process started) |

HTTP/1.1 traffic mimicry is handled by `raw_http_profile.toml` — there is no separate HTTP listener type. The WinINet-based HTTP implant and FastAPI HTTP listener have been removed.

Listeners survive server restarts: `restart_active_listeners()` in `main.py` re-spawns anything marked active in Neo4j on startup.

## Raw Listener

The `raw` listener type sends and receives arbitrary bytes over TCP or UDP. The profile TOML defines the exact wire format — no bytes are added outside what the profile specifies. This is the forward-looking path for new protocol mimicry (NTP, DNS, FTP, etc.).

**Profile schema:**
```toml
# Simple (unnamed) — one get/post pair
[raw.get]
proto = "tcp"          # or "udp"
body = "<METADATA>"    # wire body template; <METADATA> replaced with encoded beacon

[raw.get.client.metadata]
transforms = [{ op = "base64" }]

[raw.get.server.output]
transforms = []

[raw.post]
proto = "tcp"
body = "<OUTPUT>"      # <CLIENT_ID> and <OUTPUT> tokens available

[raw.post.client.output]
transforms = [{ op = "base64" }]

[raw.post.server]
body = ""              # ACK sent back to implant
```

**Wire format:** `body_template` with tokens replaced by (un)transformed payload bytes. No framing overhead. For TCP: one message per connection (connect → send all bytes in a loop → EOF → server responds → close). For UDP: one datagram. **UDP has a hard ~64KB datagram limit with no application-layer chunking** — large payloads (especially after transform expansion like base64/netbios) will fail. Use TCP profiles for file downloads and large exfil. See `documentation/06 Network Profiles/Raw Profiles.md` for size details.

**Disambiguation (beacon vs exfil):** Primary method: the server reads the outermost `prepend` value from each transform chain and checks whether the incoming packet's leading bytes match the GET or POST prepend. If they're distinct (as in the NTP profile, where GET ends with `\xF0\x01` and POST ends with `\xF0\x02`), the packet is routed directly. Fallback: if no distinct prepend exists, the server tries the GET decode chain first, then the POST decode chain. **Do not rely on msgpack shape to disambiguate** — both beacon and exfil payloads are lists of dicts with `implant_uuid`, so `handle_beacon` will not raise on exfil data.

**One protocol per file:** Each raw profile file defines exactly one protocol via top-level `[raw.get]` / `[raw.post]`. To run multiple protocols, create multiple profile files and a listener for each. The profile name (from `[profile] name = "..."`) identifies what it is.

**Body template scope:** Transforms apply **only to the token value** (`<METADATA>`, `<OUTPUT>`, `<CLIENT_ID>`), not the surrounding body template. For example, with `body = "GET / HTTP/1.1\r\n\r\n<METADATA>"` and `transforms = [{ op = "symcrypt", key = '...' }, { op = "base64" }]`, the transform chain encrypts and then base64-encodes the raw metadata bytes. The result replaces the `<METADATA>` token — the `GET / HTTP/1.1\r\n\r\n` framing stays plaintext. This is by design: protocol framing must remain readable by network devices and the listener's disambiguation logic, while the payload within is protected.

**Available transform operations:**

| Operation | TOML | Description |
|---|---|---|
| `base64` | `{ op = "base64" }` | Standard Base64 encode/decode |
| `base64url` | `{ op = "base64url" }` | URL-safe Base64 (no padding) |
| `prepend` | `{ op = "prepend", val = '\xAA\xBB' }` | Prepend literal bytes |
| `append` | `{ op = "append", val = '\xCC\xDD' }` | Append literal bytes |
| `mask` | `{ op = "mask", val = '\xFF' }` | XOR with repeating key |
| `netbios` | `{ op = "netbios" }` | NetBIOS encoding (lowercase) |
| `netbiosu` | `{ op = "netbiosu" }` | NetBIOS encoding (uppercase) |
| `symcrypt` | `{ op = "symcrypt", key = '\x...' }` | AES-256-GCM encryption (32-byte key required) |

**symcrypt (AES-256-GCM):** Symmetric encryption transform. The `key` field must be exactly 32 bytes of hex escapes in a TOML literal string. Wire format: `[nonce (12 bytes)][auth tag (16 bytes)][ciphertext]`. A fresh random nonce is generated per encryption call. Server-side uses Python `cryptography` (AESGCM); implant-side uses Windows BCrypt (CNG). Place `symcrypt` **first** in the transform chain (before base64/prepend/append) so it encrypts the raw payload and outer transforms handle encoding/framing.

**Binary values in transform `val`/`key` fields:** Use TOML literal strings (single-quoted) with `\xNN` hex escapes. The server's `malleable_string_to_bytes` processes them. Example: `{ op = "prepend", val = '\x23\x00\x06\xEC' }` prepends 4 bytes. Do NOT use TOML basic string (double-quoted) `\xNN` — TOML rejects `\x` as an invalid escape. Use `\uXXXX` in basic strings only if you prefer Unicode escaping.

**Profile storage:** Profiles are stored server-side in MySQL (`artifact_store` table) and managed via the `/api/v1/profiles/` CRUD API. The client reads profile lists and contents from the API. Default/seed profiles live in `client/user/profiles/` (git-tracked) and can be bulk-uploaded to the server via the "Seed Defaults" button on the profile preview page or the `POST /api/v1/profiles/seed` endpoint. Profiles are also auto-saved to the artifact store when a listener is created.

**Default profiles (`client/user/profiles/`):**

| File | Protocol | Transport | Port | Notes |
|---|---|---|---|---|
| `raw_http_profile.toml` | HTTP/1.1 mimicry | TCP | 80 | GET/POST with full HTTP headers; Wireshark-visible as HTTP |
| `raw_ntp_profile.toml` | NTP (RFC 5905) | UDP | 123 | 48-byte header + private extension field (0xF001/0xF002) + base64url |
| `raw_ntp_profile_but_tcp.toml` | NTP over TCP | TCP | any | Same as above, proto changed to tcp |
| `raw_ftp_profile.toml` | FTP (RFC 959, simplified) | TCP | 21 | RETR/STOR command verbs + 150/226 replies; no 220 banner or auth phase |
| `raw_dns_profile.toml` | DNS EDNS0 (RFC 1035 + RFC 6891) | UDP | 53 | TXT query for `data.c2.local`; payload in private OPT option 0xFFFE/0xFFFF |
| `raw_snmp_profile.toml` | SNMP (RFC 1157 / RFC 3416) | UDP | 161 | Payload in community string; GET=SNMPv1 GetRequest, POST=SNMPv2c InformRequest |
| `raw_encrypted_http_profile.toml` | Encrypted HTTP/1.1 | TCP | 80 | Same as HTTP mimicry but with AES-256-GCM (`symcrypt`) on all payloads |
| `raw_debug_profile.toml` | None (bare msgpack) | TCP | any | Zero transforms; for pipeline testing only, not operational use |

ICMP mimicry (RFC 792) is not yet supported — it requires `SOCK_RAW` / `IPPROTO_ICMP` and elevated privileges, which the raw listener doesn't implement yet.

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
| `make test_implant_responses` | `tests/integration_test/test_implant_responses.py` | Server + Docker DBs + live implant |

**Prerequisites for `make server_tests`:**
1. Docker containers running: `make start_docker_images`
2. Server running: `PYTHONPATH=. python -m server.main`
3. Ports **19099** and **19100** must be free on localhost — listener tests bind there and fail if either is in use

If you hit connection errors, that's almost always the server not running or a stale listener process holding 19099 or 19100.

**Environment overrides for `make server_tests`:**
```bash
SERVER_URL=http://myhost:45045 TEST_API_USER=admin TEST_API_PASS=hunter2 make server_tests
```
Defaults: `http://localhost:45045` / `longhaul` / `P@ssw0rd1!` (from `.env`).

**Server test file coverage (`tests/server/`):**
- `conftest.py` — `FullC2APIClient` (adds auth + missing methods on top of the integration-test base), session-scoped `api_client` fixture (auto-authenticates on startup), function-scoped `listener_uuid` / `raw_listener_uuid` / `implant_uuid` / `file_uuid` fixtures (create resource, yield UUID, delete on teardown)
- `test_auth.py` — login, token refresh, register (authed/unauthed), rejected/malformed tokens
- `test_health.py` — health check success and 401 on no token
- `test_implants.py` — full CRUD, task queuing, task history, search
- `test_listeners.py` — full CRUD, start/stop via PATCH, missing-field validation; raw listener create/start/stop on port 19100
- `test_filestore.py` — upload/download/delete, missing-field validation, nonexistent file handling
- `test_build.py` — submits a build job and verifies acceptance only (HTTP 200 + `build_uuid`); does **not** poll for completion since the cross-compiler toolchain is not present on dev machines
- `test_profiles.py` — profile preview endpoint: valid raw profile (`raw_http_profile.toml`, asserts `raw_profiles` populated), raw simple TOML (one `"default"` entry), minimal TOML with no `[raw]` section returns empty `raw_profiles`, malformed TOML (HTTP 200 with parse_ok=false), missing profile_contents (HTTP 400), unauthenticated (HTTP 401). Profile CRUD: upload, list, get-by-name, upsert-same-hash (no-op), upsert-different-content (hash changes), delete, bulk seed, unauthenticated list (401)
- `test_transforms.py` — symcrypt (AES-256-GCM) unit tests: encrypt/decrypt round-trip (basic, empty, 64KB), wire format layout verification, nonce uniqueness, wrong-key rejection, tampered-ciphertext detection, bad key/data length errors. Transform chain tests: `val` and `key` field support, symcrypt+base64 combo, symcrypt+prepend+append combo
- `test_audit.py` — pagination: default response shape, custom limit, offset, total_count consistency, limit clamping (min 1, max 1000), negative offset clamping, filter-by-action, filter-by-actor, newest-first ordering. Export: CSV format validation, filtered export, unauthenticated access (401). Auth: unauthenticated list (401)

**Implant response tests (`tests/integration_test/test_implant_responses.py`) — need to know:**

Requires a live implant beaconing against the server. Tests validate both success and response *content* — not just `error_code == 0`. Organized as 5 test classes:
- `TestStrategy` — strat list returns strategy names, strat active returns both channel fields
- `TestMemStore` — full lifecycle: clear → upload → list → download (round-trip verify) → delete → verify gone
- `TestFileSystem` — ls (CWD and C:\\), cd, file upload/download round-trip, memstore deref upload
- `TestBofExecution` — ARP BOF from base64 and from memstore, verifies output is non-empty
- `TestSystem` — sleep set/restore

Run with: `PYTHONPATH=. python -m pytest -v -s tests/integration_test/test_implant_responses.py`

Replaces the older `run_implant_tasks.py` which only asserted `error_code == 0` without checking response data. Does NOT run `exit` — leaves the implant alive for subsequent test runs.

**Web smoke tests (`tests/web/web_tests.py`) — need to know:**

These run against a real in-process NiceGUI app (no browser, no server needed). They verify pages render without crashing and key static labels are present.

Auth-gated pages (Operations, Listeners, Payloads, Profile Preview): `setup_menu()` redirects to `/login` when `app.storage.user["api_host"]` is unset. These tests verify the redirect fires by asserting the login page labels appear — they do **not** test page content directly.

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

**`fs:` prefix for filestore references:** Commands that accept base64 file content (`file upload`, `bof`, `memstore upload`) also accept `fs:<filename>` to reference files already in the server filestore. The resolver (`client/modules/fs_resolver.py`) lists all files, finds the UUID by name, downloads the bytes, and passes them to the command as raw bytes. Raw base64 and `*memstore_ref` still work — `fs:` is additive. Resolution is client-side and async (uses existing `get_all_files()` + `get_file_bytes()` API calls). Examples:
- `file upload C:\Temp\m.exe fs:mimikatz.exe`
- `bof fs:arp.o`
- `memstore upload mykey fs:somefile.bin`

**Filestore metadata:** Files in the filestore track provenance via three columns: `uploaded_by` (operator username or `implant:<uuid>`), `uploaded_at` (millisecond epoch), `source_implant` (nullable, set when file came from an implant download). These are set automatically by the API (operator uploads) and response pipeline (auto-captured downloads). The filestore table and file detail page display these fields.

**Environment config:** All secrets and service addresses come from `.env` via `dotenv_values(".env")` in `server/instance.py`. The `.env` is loaded at server startup — no runtime reloads.

**User preferences** are stored in `app.storage.user` and initialized in `client/pages/user_settings.py:initialize_default_settings()`. Known keys:
- `auto_refresh_rate` (int, default `1`) — polling interval in seconds for timers throughout the UI
- `notification_position` (str, default `"bottom"`) — where `ui.notify()` banners appear; valid values: `top-left`, `top-right`, `top`, `bottom-left`, `bottom-right`, `bottom`, `left`, `right`, `center`
- `username` (str) — set on login, used by chat and profile pages

**User Management API** (`server/routes/v1/user_resource.py`, namespace `users`):
- `GET /api/v1/users/` — list all users (returns `[{username, has_totp}, ...]`)
- `GET /api/v1/users/me` — current user profile (includes `has_totp`)
- `DELETE /api/v1/users/me` — delete own account
- `DELETE /api/v1/users/<username>` — delete a user (admin action)
- `PUT /api/v1/users/password` — change own password (requires `old_password` + `new_password`)
- `POST /api/v1/users/totp` — generate TOTP secret + provisioning URI
- `DELETE /api/v1/users/totp` — disable TOTP
- `POST /api/v1/users/totp/verify` — verify a 6-digit TOTP code

**Chat API** (`server/routes/v1/chat_resource.py`, namespace `chat`):
- `GET /api/v1/chat/?since_id=N` — fetch messages (optionally since a given ID)
- `POST /api/v1/chat/` — send a message (body: `{"message": "..."}`)

**User-related UI pages:**
- `/settings` (`client/pages/user_settings.py`) — tabbed settings: Preferences, Profile (password/TOTP 2FA/delete account), Users (create, table with 2FA status column, multi-select delete)
- `/settings/{tab}` — deep-link to a specific tab (e.g. `/settings/users`)
- `/profile` (`client/pages/profile.py`) — thin redirect to `/settings/profile`
- `/admin/users` (`client/pages/admin_users.py`) — thin redirect to `/settings/users`
- `/comms` (`client/pages/comms.py`) — operator chat, polls server for messages, uses `ui.markdown` for rendering
- Login page shows a soft warning popup when logging in as the default `longhaul` account; enforces TOTP at login if the user has it configured

**Audit Log API** (`server/routes/v1/audit_resource.py`, namespace `audit`):
- `GET /api/v1/audit/?actor=&action=&target_type=&since=&limit=&offset=` — retrieve audit entries with pagination. Returns `{entries, total_count, limit, offset}`. Default limit 50, max 1000. Offset and limit are clamped to valid ranges.
- `GET /api/v1/audit/export?actor=&action=&target_type=&since=` — download all matching audit entries as a CSV file (no limit). Returns `text/csv` with `Content-Disposition: attachment`.

Tracked actions: `login_success`, `login_failed`, `task_queued`, `implant_registered`, `implant_deleted`, `listener_created`, `listener_started`, `listener_stopped`, `listener_deleted`, `file_uploaded`, `file_deleted`, `user_registered`, `user_deleted`.

The audit helper (`server/db/audit.py`) exposes `log_audit(actor, action, target_type, target_uuid, detail)` — call it from any route handler to record an event. Entries are stored in MySQL (`audit_log` table) with millisecond timestamps.

**Audit UI page:**
- `/audit` (`client/pages/audit.py`) — filterable, paginated table of operator activity. Page controls at the bottom with configurable page size (25/50/100). Two export buttons: "CSV" exports the current page, "ALL" downloads the entire log via the `/export` endpoint.

**Database models added:**
- `AuditLog` (id, timestamp, actor, action, target_type, target_uuid, detail) — operator activity log
- `UserLogin.totp_secret` (nullable String) — stores TOTP secret for 2FA
- `ChatMessage` (id, sender, message, timestamp) — chat message storage
- `FileStore.uploaded_by` (nullable String) — operator username or `implant:<uuid>`
- `FileStore.uploaded_at` (nullable BigInteger) — millisecond epoch timestamp
- `FileStore.source_implant` (nullable String(36)) — implant UUID for auto-captured downloads

**Notifications:** Never call `ui.notify()` directly in `client/`. Use `notify()` from `client.utils.helpers` instead — it reads `notification_position` from user storage so the user's preference is applied everywhere.

**UI Design System (`client/static/theme.css`):** All buttons, empty states, and confirmation dialogs use semantic CSS classes:

| Class | Usage |
|---|---|
| `tech-btn-action` | Primary actions (start, create, save) — green border/bg |
| `tech-btn-action-2` | Toolbar/secondary actions (open page, terminal, upload) — muted green |
| `tech-btn-secondary` | Neutral actions (refresh, export, restart) — grey border |
| `tech-btn-destructive` | Destructive actions (delete, stop) — red border/bg |
| `tech-btn-ghost` | Invisible until hover (back button, subtle controls) |
| `tech-empty-state` | Empty table/list placeholder (centered icon + message) |
| `tech-confirm-dialog` | Destructive action confirmation dialog card |
| `tech-table-head` | Standardized table header row styling |
| `tech-table-base` | Base table class (no shadow, transparent bg, sticky headers) |

**Shared UI components (`client/pages/components/dashboard_widgets.py`):**
- `flat_stat(label, value, icon, color)` — inline stat pill for detail page headers
- `stat_widget(label, icon, color, key, stats_dict)` — reactive stat widget with `bind_text_from`
- `empty_state(icon, message, action_label, on_action)` — reusable empty state with optional CTA
- `confirm_action(title, message, on_confirm, confirm_label, icon)` — standardized destructive action confirmation dialog
- `info_row(key, value)` — key/value row for metadata panels
- `back_button()` — async back navigation button using tab storage

When adding destructive actions (delete, stop, remove), always wrap in `confirm_action()`. When adding tables, include a `no-data` slot using the `tech-empty-state` pattern. UUIDs and hashes must always be displayed in full — never truncate them.

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