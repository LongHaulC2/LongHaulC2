# API Reference

**Base URL:** `http://<server>:45045/api/v1`

**Interactive docs (Swagger):** `http://<server>:45045/doc`

All endpoints (except `/authentication/`) require a JWT `Bearer` token. See [Scripting Overview](../03%20Scripting/Overview.md) for authentication examples.

---

## Standard Response Envelope

```json
{
  "status": "200",
  "message": "Success",
  "data": { ... }
}
```

Error responses use standard HTTP status codes. Common ones:

| Code | Meaning |
|---|---|
| `400` | Bad request / missing or invalid parameters |
| `401` | Unauthorized — missing or expired token |
| `404` | Resource not found |
| `429` | Rate limit exceeded |
| `500` | Internal server error |

---

## Authentication — `/api/v1/authentication/`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/authentication/` | None | Login. Returns access + refresh tokens. |
| `POST` | `/authentication/refresh` | Refresh token | Exchange a refresh token for a new access token. |
| `POST` | `/authentication/register` | Bearer | Register a new operator account. |

### POST `/authentication/`

**Request body:**
```json
{ "username": "longhaul", "password": "P@ssw0rd1!" }
```

**Response `data`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

Tokens expire: access = **15 minutes**, refresh = **1 day**.

---

### POST `/authentication/refresh`

Supply the refresh token as the Bearer token header.

**Response `data`:**
```json
{ "access_token": "eyJ..." }
```

---

### POST `/authentication/register`

Requires an existing valid access token.

**Request body:**
```json
{ "username": "new_operator", "password": "SecurePass1!" }
```

---

## Implants — `/api/v1/implants/`

| Method | Path | Description |
|---|---|---|
| `GET` | `/implants/` | List all implants |
| `POST` | `/implants/` | Create a blank implant entry (returns a UUID) |
| `GET` | `/implants/<uuid>` | Get a single implant |
| `PUT` | `/implants/<uuid>` | Update implant metadata |
| `DELETE` | `/implants/<uuid>` | Delete an implant from the graph |
| `POST` | `/implants/<uuid>/task` | Queue a task for an implant |
| `GET` | `/implants/<uuid>/tasks` | Peek at currently queued (pending) tasks |
| `DELETE` | `/implants/<uuid>/tasks` | Clear all pending tasks for an implant |
| `GET` | `/implants/<uuid>/task/<task_uuid>` | Get the status/result of a specific task |
| `GET` | `/implants/<uuid>/tasks/history` | Get full task history from MySQL |
| `POST` | `/implants/search` | Search implants by a term |
| `POST` | `/implants/history/search` | Search task history by a term |

---

### GET `/implants/`

Returns all implants known to the server.

**Response `data`:** Array of implant objects:
```json
[
  {
    "implant_uuid": "01932ba4-...",
    "system_hostname": "DESKTOP-ABC123",
    "external_ip": "10.0.0.5",
    "listener_uuid": "01932ba4-...",
    ...
  }
]
```

---

### POST `/implants/<uuid>/task`

Queue a command for an implant. The implant picks it up on its next beacon.

Accepts `application/json` or `application/msgpack`.

**Request body:**
```json
{
  "implant_uuid": "01932ba4-...",
  "task": {
    "task_name": "ls",
    "args": { "directory": "C:\\Users\\" }
  }
}
```

**Response `data`:**
```json
{ "task_uuid": "01932ba4-yyyy-..." }
```

Use the returned `task_uuid` to poll for the result.

#### Task Names Reference

| Task Name | Args |
|---|---|
| `exit` | *(none)* |
| `sleep` | `sleep_time` (int, seconds) |
| `cd` | `directory` (string) |
| `ls` | `directory` (string) |
| `file download` | `file_path` (string) |
| `file upload` | `file_path` (string), `file_contents` (bytes) |
| `memstore list` | *(none)* |
| `memstore upload` | `file_name` (string), `file_contents` (bytes) |
| `memstore download` | `file_name` (string) |
| `memstore delete` | `file_name` (string) |
| `memstore clear` | *(none)* |
| `strat active` | *(none)* |
| `strat list` | *(none)* |
| `strat set post` | `strategy_name` (string) |
| `strat set get` | `strategy_name` (string) |
| `strat set both` | `get_strategy_name` (string), `post_strategy_name` (string) |
| `bof` | `bof_contents` (bytes), `bof_args` (string) |
| `link smb` | `protocol` (`"smb"`), `target` (string), `inbox_pipe` (string), `outbox_pipe` (string) |
| `unlink smb` | `child_uuid` (string) |
| `link list` | *(none)* |

> **Binary args:** For tasks that take binary data (`file upload`, `memstore upload`, `bof`), send raw bytes inside a msgpack payload. If using JSON, the client handles base64 decoding before serializing — the server and implant always work with raw bytes.

---

### GET `/implants/<uuid>/task/<task_uuid>`

Retrieve the status and result of a specific task.

**Response `data`:**
```json
{
  "task_uuid": "...",
  "implant_uuid": "...",
  "task_request": { "task_name": "ls", "args": { "directory": "C:\\" } },
  "task_response": {
    "message": { "type": "text", "value": "Success" },
    "data":    { "type": "text", "value": "file1.txt\nfile2.txt\n" },
    "windows_error_code": { "type": "text", "value": "0" }
  }
}
```

`task_response` is `null` until the implant has checked in and returned a result.

---

### GET `/implants/<uuid>/tasks/history`

Returns all completed tasks for an implant from MySQL.

**Query parameters:**

| Param | Type | Description |
|---|---|---|
| `since` | UUIDv7 string | Only return tasks with a `task_uuid` newer than this value. Use the last seen `task_uuid` to poll incrementally. |

---

### POST `/implants/search`

Search implants by hostname, IP, UUID, or any indexed field.

**Request body:**
```json
{ "search_term": "DESKTOP" }
```

---

## Listeners — `/api/v1/listeners/`

| Method | Path | Description |
|---|---|---|
| `GET` | `/listeners/` | List all listeners |
| `POST` | `/listeners/` | Create and start a new listener |
| `GET` | `/listeners/<uuid>` | Get a single listener |
| `PATCH` | `/listeners/<uuid>` | Start or stop a listener (`{"active": true/false}`) |
| `DELETE` | `/listeners/<uuid>` | Stop and permanently delete a listener |

---

### POST `/listeners/`

**Request body:**
```json
{
  "listener_name": "http_mimicry",
  "listener_type": "raw",
  "listener_host": "0.0.0.0",
  "listener_port": 80,
  "listener_profile_name": "raw_http_profile.toml",
  "listener_profile_contents": "<contents of raw_http_profile.toml>",
  "listener_notes": "Optional notes"
}
```

**Response `data`:** The created listener object, including its generated `listener_uuid`.

---

### PATCH `/listeners/<uuid>`

Start or stop an existing listener without deleting it.

```json
{ "active": true }
```

Returns `200` with a message — also returns `200` (not an error) if the listener is already in the requested state.

---

## Build — `/api/v1/build/`

| Method | Path | Description |
|---|---|---|
| `POST` | `/build/` | Submit a new implant build job |
| `GET` | `/build/` | List all builds (payloads) in the database |
| `GET` | `/build/jobs/<build_uuid>` | Get the status of a specific build job |
| `GET` | `/build/<hash>` | Download a compiled payload binary |
| `DELETE` | `/build/<hash>` | Delete a payload from the database |
| `GET` | `/build/<hash>/source` | Download the source code archive (ZIP) for a build |

---

### POST `/build/`

Submit a build. The build runs synchronously inside a Docker container.

**Request body:**
```json
{
  "implant_name": "my_implant",
  "listener_uuids": ["01932ba4-...", "01932ba4-..."],
  "initial_get_profile_listener_uuid": "01932ba4-...",
  "initial_post_profile_listener_uuid": "01932ba4-...",
  "options": {
    "debug": false,
    "clear_cache": false
  }
}
```

| Field | Description |
|---|---|
| `implant_name` | Name for the build / output artifacts |
| `listener_uuids` | List of listener UUIDs to bake strategies for into the implant |
| `initial_get_profile_listener_uuid` | Which listener's GET profile to use at first boot |
| `initial_post_profile_listener_uuid` | Which listener's POST profile to use at first boot |
| `options.debug` | Enable debug logging in the implant binary (`-DENABLE_IMPLANT_LOGS=ON`) |
| `options.clear_cache` | Clear the Docker build cache before compiling |

**Response `data`:**
```json
{
  "build_uuid": "01932ba4-...",
  "build_stats": { "build_time": 12.4 }
}
```

Artifacts (`.exe`, `.dll`) are stored in MySQL after a successful build. Use `GET /build/<hash>` to download them.

---

### GET `/build/jobs/<build_uuid>`

Check the status of a build.

**Response `data`:**
```json
{
  "build_uuid": "...",
  "payload_name": "my_implant",
  "build_status": "complete",
  "payload_hash": "a1b2c3d4..."
}
```

`build_status` values: `building`, `complete`, `failed`.

---

## Filestore — `/api/v1/filestore/`

Server-side file storage for staging files before pushing them to implants.

| Method | Path | Description |
|---|---|---|
| `POST` | `/filestore/` | Upload a file (base64-encoded in JSON body) |
| `GET` | `/filestore/` | List all stored files |
| `GET` | `/filestore/<file_uuid>` | Download a file |
| `DELETE` | `/filestore/<file_uuid>` | Delete a file |

### POST `/filestore/`

```json
{
  "file_name": "mimikatz.exe",
  "file_contents": "<base64_encoded_bytes>"
}
```

**Response `data`:**
```json
{ "file_uuid": "01932ba4-..." }
```

---

## Graph — `/api/v1/graph/`

Returns the implant topology and network graph data used to populate the **Graph** view in the UI.

| Method | Path | Description |
|---|---|---|
| `GET` | `/graph/` | Get all nodes and relationships in the graph |

---

## Profiles — `/api/v1/profiles/`

Profiles are stored server-side and managed through this API. The UI uses these endpoints for all profile operations — there is no filesystem dependency.

| Method | Path | Description |
|---|---|---|
| `GET` | `/profiles/` | List all stored profiles (metadata only, no contents) |
| `POST` | `/profiles/` | Upload or update a profile |
| `GET` | `/profiles/<name>` | Download a profile by name (full contents) |
| `DELETE` | `/profiles/<name>` | Delete a profile by name |
| `POST` | `/profiles/seed` | Bulk-upload default profiles |
| `POST` | `/profiles/preview` | Parse and render a profile TOML for visualization |

### GET `/profiles/`

Returns all profiles stored on the server. Contents are not included — use `GET /profiles/<name>` to fetch a specific profile's TOML.

**Response `data`:**
```json
{
  "profiles": [
    {
      "artifact_uuid": "01932ba4-...",
      "artifact_name": "raw_http_profile.toml",
      "content_hash": "a1b2c3...",
      "created_at": 1719700000000,
      "updated_at": 1719700000000
    }
  ]
}
```

---

### POST `/profiles/`

Upload a new profile or update an existing one. If a profile with the same name already exists and the content is identical (same SHA256 hash), the request is a no-op. If the content differs, the profile is updated.

**Request body:**
```json
{
  "profile_name": "raw_http_profile.toml",
  "profile_contents": "<full TOML string>"
}
```

**Response `data`:**
```json
{
  "artifact_uuid": "01932ba4-...",
  "artifact_name": "raw_http_profile.toml",
  "content_hash": "a1b2c3...",
  "created": true
}
```

`created` is `true` for new profiles, `false` for updates or no-ops.

---

### GET `/profiles/<name>`

Download a specific profile by filename.

**Response `data`:**
```json
{
  "artifact_uuid": "01932ba4-...",
  "artifact_name": "raw_http_profile.toml",
  "artifact_contents": "[profile]\nname = \"HTTP Mimicry\"\n...",
  "content_hash": "a1b2c3...",
  "created_at": 1719700000000,
  "updated_at": 1719700000000
}
```

---

### DELETE `/profiles/<name>`

Delete a profile from the server. Returns `404` if the profile does not exist.

---

### POST `/profiles/seed`

Bulk-upload multiple profiles in one request. Each profile follows upsert semantics (same as `POST /profiles/`).

**Request body:**
```json
{
  "profiles": [
    { "profile_name": "raw_http_profile.toml", "profile_contents": "..." },
    { "profile_name": "raw_ntp_profile.toml", "profile_contents": "..." }
  ]
}
```

**Response `data`:**
```json
{
  "seeded": 6,
  "profiles": ["raw_http_profile.toml", "raw_ntp_profile.toml", "..."]
}
```

---

### POST `/profiles/preview`

Parse and render a profile TOML, returning structured output with per-step transform chains. Always returns HTTP 200. Parse failures are returned as data (check `data.validation.parse_ok`), not as HTTP errors.

**Request body:**
```json
{ "profile_contents": "<raw TOML string>" }
```

**Response `data`:**
```json
{
  "profile_name": "HTTP Mimicry",
  "profile_author": "LongHaul Team",
  "smb": null,
  "raw_profiles": [
    {
      "name": "default",
      "get": { "proto": "tcp", "client": { ... }, "server": { ... } },
      "post": { "proto": "tcp", "client": { ... }, "server": { ... } }
    }
  ],
  "validation": {
    "parse_ok": true,
    "parse_error": null,
    "missing_fields": [],
    "warnings": []
  }
}
```

See [Mimicry](../06%20Network%20Profiles/Overview.md) for the full response shape and field descriptions.

---

## Health — `/api/v1/health/`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health/` | None | Returns server health status |
