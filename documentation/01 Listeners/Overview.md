# Listeners

A **listener** is a network process that handles inbound implant traffic. Each listener is bound to a port and a network profile that defines the traffic shape. Multiple listeners can run simultaneously with different profiles.

---

## How Listeners Work

Listeners run as **daemon multiprocesses** managed by `server/listeners/supervisor.py`. They are separate OS processes (not threads) so a crash in one listener does not affect the server or other listeners.

On server startup, `restart_active_listeners()` queries Neo4j and re-spawns any listener marked as active — listeners survive server restarts automatically.

All listener types share the same bridge into the server core:

```
Implant (GET/POST)
      ↓
  Listener Process
      ↓
  listener_bridge.py
      ↓
  handle_beacon()  /  handle_exfil()
      ↓
  Redis (task queue / response inbox)
```

`listener_bridge.py` is protocol-agnostic — any listener calls the same two functions regardless of transport.

---

## Listener Types

| Type | Status | Transport |
|---|---|---|
| `raw` | **Implemented** | Plain TCP or UDP. The profile's `[raw.*]` body templates define the **complete wire format** — the listener adds nothing beyond what the TOML specifies. HTTP/1.1 mimicry, NTP, DNS, FTP, any binary protocol — all defined by the profile. `raw_http_profile.toml` ships as a ready-to-use HTTP/1.1 example. |
| `pivot_smb` | Placeholder | No process is started. Used as an internal marker for implants that connect via SMB chains rather than direct egress. |

> **The raw listener is the only C2 channel.** You own every byte that goes on the wire — the listener is a conduit, not a protocol. What your traffic looks like is entirely an operator decision made in the profile TOML.

---

## Creating a Listener

Listeners are created through the UI (**Listeners** page) or via the API (`POST /api/v1/listeners/`).

### Required Fields

| Field | Type | Description |
|---|---|---|
| `listener_name` | string | Human-readable name. Used to identify the listener and to derive strategy names in the implant. |
| `listener_type` | string | One of: `raw`, `pivot_smb` |
| `listener_host` | string | IP or hostname the listener binds to (e.g., `0.0.0.0`) |
| `listener_port` | integer | Port to listen on (e.g., `80`, `123`, `53`) |
| `listener_profile_name` | string | Filename of the network profile (e.g., `raw_http_profile.toml`) |
| `listener_profile_contents` | string | Full TOML text of the network profile |
| `listener_notes` | string | Optional operator notes |

### Example API Call

```bash
curl -s -X POST http://localhost:45045/api/v1/listeners/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "listener_name": "http_mimicry",
    "listener_type": "raw",
    "listener_host": "0.0.0.0",
    "listener_port": 80,
    "listener_profile_name": "raw_http_profile.toml",
    "listener_profile_contents": "<contents of raw_http_profile.toml>",
    "listener_notes": "HTTP/1.1 mimicry via raw profile"
  }'
```

---

## Managing Listeners

| Action | API |
|---|---|
| List all listeners | `GET /api/v1/listeners/` |
| Get one listener | `GET /api/v1/listeners/<uuid>` |
| Create listener | `POST /api/v1/listeners/` |
| Start / Stop listener | `PATCH /api/v1/listeners/<uuid>` with `{"active": true/false}` |
| Delete listener | `DELETE /api/v1/listeners/<uuid>` |

### Start/Stop Example

```bash
# Stop a listener
curl -X PATCH http://localhost:45045/api/v1/listeners/<uuid> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"active": false}'

# Restart it
curl -X PATCH http://localhost:45045/api/v1/listeners/<uuid> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

---

## Mimicry

Each listener is paired with a **network profile** (a TOML file) that controls exactly what bytes go on the wire. See [Mimicry](../06%20Network%20Profiles/Overview.md) for full documentation.

Each listener gets one profile. Implants can be built with multiple listeners/profiles baked in and can switch between them at runtime with `strat set get` / `strat set post`.

### Strategy Naming

When a listener is created, strategy names are automatically derived from the listener's metadata and baked into built implants. For raw listeners, names follow the pattern:

```
raw_<host>_<port>_<profile_name>
```

Where `<profile_name>` is taken from the `[profile] name = "..."` field in the TOML, with non-alphanumeric characters replaced by underscores. For example, a listener on `0.0.0.0:80` using a profile named `"HTTP Mimicry"` produces the strategy name `raw_0_0_0_0_80_HTTP_Mimicry`.

You can see available strategy names by running `strat list` in the implant terminal.

---

## Raw Listener

The raw listener sends and receives arbitrary bytes over TCP or UDP. The network profile's `[raw.*]` section defines the **complete wire format** — the listener adds no framing beyond what the profile specifies. Not a byte more, not a byte less.

What protocol your traffic looks like is entirely your decision. Example profiles ship in `client/user/profiles/`:

| Profile | Looks like |
|---|---|
| `raw_http_profile.toml` | HTTP/1.1 (default starting point) |
| `raw_ntp_profile.toml` | NTPv4 over UDP |
| `raw_ftp_profile.toml` | FTP RETR/STOR |
| `raw_dns_profile.toml` | DNS EDNS0 over UDP |
| `raw_snmp_profile.toml` | SNMPv1/v2c |
| `raw_debug_profile.toml` | Bare msgpack (no transforms — dev only) |

See [Raw Profiles](../06%20Network%20Profiles/Raw%20Profiles.md) for full documentation.

---

## SMB Pivot Listener (`pivot_smb`)

The `pivot_smb` type is a marker — no network process is started. It exists to represent implants in the graph that communicate via SMB named pipes through a parent implant, rather than reaching the server directly.

When you create a `pivot_smb` listener, the server registers it in Neo4j and makes it available as a build target so you can generate an implant that is configured to communicate over the SMB chain. The parent implant (with a `raw` listener) acts as the egress node.

---

## Supervisor & Process Management

`server/listeners/supervisor.py` maintains an in-memory dictionary of `listener_uuid → Process`. Thread-safe access is enforced with a lock.

| Function | Description |
|---|---|
| `start_listener(listener_data)` | Spawns the appropriate process for the listener type |
| `stop_listener(listener_uuid)` | Terminates and joins the process |
| `stop_all()` | Terminates all running listeners |
| `restart_active_listeners()` | Called at server startup — re-spawns anything marked active in Neo4j |

Listener processes are `daemon=True`, so they are automatically killed when the server process exits.
