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
| `http` | **Implemented** | HTTP/HTTPS via FastAPI. Traffic shape controlled by the `[http.*]` sections of the network profile. |
| `raw` | **Implemented** | Plain TCP or UDP. The profile's `[raw.*]` body templates define the complete wire format — no framing is added. Use for NTP, DNS, FTP, or any custom binary protocol. |
| `pivot_smb` | Placeholder | No process is started. Used as an internal marker for implants that connect via SMB chains rather than direct egress. |

---

## Creating a Listener

Listeners are created through the UI (**Listeners** page) or via the API (`POST /api/v1/listeners/`).

### Required Fields

| Field | Type | Description |
|---|---|---|
| `listener_name` | string | Human-readable name. Used to identify the listener and to derive strategy names in the implant. |
| `listener_type` | string | One of: `http`, `raw`, `ntp`, `pivot_smb` |
| `listener_host` | string | IP or hostname the listener binds to (e.g., `0.0.0.0`) |
| `listener_port` | integer | Port to listen on (e.g., `443`, `80`, `123`) |
| `listener_profile_name` | string | Filename of the network profile (e.g., `profile_def.toml`) |
| `listener_profile_contents` | string | Full TOML text of the network profile |
| `listener_notes` | string | Optional operator notes |

### Example API Call

```bash
curl -s -X POST http://localhost:45045/api/v1/listeners/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "listener_name": "http_corp_traffic",
    "listener_type": "http",
    "listener_host": "0.0.0.0",
    "listener_port": 443,
    "listener_profile_name": "amazon",
    "listener_profile_contents": "...",
    "listener_notes": "Mimics Amazon browsing traffic"
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

## Network Profiles

Each listener is paired with a **network profile** (a TOML file) that controls exactly what bytes go on the wire. See [Network Profiles](../06%20Network%20Profiles/Overview.md) for full documentation.

Each listener gets one profile. Implants can be built with multiple listeners/profiles baked in and can switch between them at runtime with `strat set get` / `strat set post`.

### Strategy Naming

When a listener is created, strategy names are automatically derived from the listener's metadata and baked into built implants. Strategy names follow the pattern:

```
http_get_<host>_<port>_<profile_suffix>
http_post_<host>_<port>_<profile_suffix>
```

You can see available strategy names by running `strat list` in the implant terminal.

---

## HTTP Listener

The HTTP listener is built on **FastAPI** and runs as a daemon process. It handles:

- **Beacon (GET):** Implant checks in, provides metadata, receives pending tasks as a msgpack array.
- **Exfil (POST):** Implant delivers task results as a msgpack array.

Traffic shape is fully controlled by the network profile assigned at listener creation time.

---

## Raw Listener

The raw listener sends and receives arbitrary bytes over TCP or UDP. The network profile's `[raw.*]` section defines the complete wire format — the listener adds no framing beyond what the profile specifies.

Use this listener type to mimic any protocol: NTP, DNS, FTP, custom binary, etc. A working NTP example profile ships at `client/user/profiles/raw_ntp_profile.toml`.

See [Raw Profiles](../06%20Network%20Profiles/Raw%20Profiles.md) for full documentation.

---

## SMB Pivot Listener (`pivot_smb`)

The `pivot_smb` type is a marker — no network process is started. It exists to represent implants in the graph that communicate via SMB named pipes through a parent implant, rather than reaching the server directly.

When you create a `pivot_smb` listener, the server registers it in Neo4j and makes it available as a build target so you can generate an implant that is configured to communicate over the SMB chain. The parent implant (with an `http` listener) acts as the egress node.

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
