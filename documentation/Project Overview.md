# Project Overview

**Project Goal:** A minimal, plugin/flexible C2 framework that is **not malicious by default**. The implant ships with only a small set of built-ins — filesystem operations, file transfer, memory store, strategy switching, and SMB chaining. Everything else is operator-loaded at runtime via Beacon Object Files (BOFs). The implant is a tool, not a threat, until you make it one.

---

## Objectives

- **Not Malicious by Default:** The implant ships with little to no traditional offensive capability. All offensive actions are loaded at/during runtime via BOFs. Bring your own.
- **Minimal Signature:** Intentionally small built-in feature set. Less code in the implant means less to detect, less to go wrong, and less to maintain.
- **Network Profiles:** Leverage adjustable network profiles for varied network communication
- **Robust Management:** Comprehensive REST API and a web-based frontend for operator management.
- **Automation-first:** Everything accessible via the UI is also accessible via the API, enabling full scripted operations.

---

## Design Choices & Key Features

The entire architecture was built around surviving for months or years, not just days:

- **Granular Profile Binding:** Each listener can use a distinct Network profile. A single server can serve multiple campaigns with different traffic signatures simultaneously.
- **Dynamic Strategy Switching:** Implants support multiple communication profiles baked in at build time. Operators can hot-swap the active GET or POST strategy at runtime without spawning new artifacts.
- **Automated Rotation:** Via the API, operators can script rotation schedules (e.g., Spotify traffic in the morning, Windows Update profile at night).
- **BOF-first Extension Model:** The implant ships with minimal built-in capability. All offensive actions are loaded at runtime as Beacon Object Files (BOFs), keeping the implant's static footprint small.
- **SMB Chaining:** Implants can be linked peer-to-peer over named pipes, routing traffic through a chain without each node requiring direct egress.

---

## Architecture

### Domain Separation

The product has two completely separate codebases. They communicate only via the REST API.

| Domain | Path | Description |
|---|---|---|
| Server | `server/` | Python/Flask-RestX REST API, all C2 orchestration logic |
| Client (UI) | `client/` | Python/NiceGUI web frontend |
| Implant | `implant_templates/win_implant_base/` | C++ Windows implant, compiled server-side on demand |
| Tests | `tests/` | Integration and schema tests |

### Data & Task Flow

```
Operator (UI/Script) → API → Redis (task queue)
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
- `listener_bridge.py` is the single handoff point between any listener protocol and the server core.

### Databases

| Database | Container | Purpose |
|---|---|---|
| **MySQL** | `C2_mysql` | Long-term storage: task history, payloads, users, files |
| **Redis** | `C2_redis-stack` | Task queue and response inbox per implant |
| **Neo4j** | `C2_neo4j-stack` | Graph state: implant topology, host/network relationships, listener state |

### Listeners

Listeners run as **daemon multiprocesses** managed by `server/listeners/supervisor.py`. They survive server restarts — anything marked active in Neo4j is re-spawned on startup.

| Type | Status | Notes |
|---|---|---|
| `http` | Implemented | FastAPI, traffic shape controlled by network profile |
| `raw` | Implemented | Plain TCP/UDP, complete wire format defined by profile `[raw.*]` sections |
| `pivot_smb` | Placeholder | Registered as a type but no process is started — used as an internal marker for SMB-linked chains |

### Ports

| Service | Port | Notes |
|---|---|---|
| API (server) | `45045` | Flask REST API |
| UI (client) | `8083` | NiceGUI web interface |
| MySQL | `3306` | |
| Redis | `6379` | |
| Redis Insight | `8001` | Web GUI — restrict in prod |
| Neo4j (web) | `7474` | Browser UI |
| Neo4j (bolt) | `7687` | Driver connection |

---

## Command Reference

Full command documentation: [Commands](02%20Implants/1.%20Commands.md)

```text
------
System
------
exit                 : Kill the implant process on the host.
sleep                : Update the implant's sleep interval. Ex: `sleep 60`

-----------
File System
-----------
cd                   : Change the working directory. Ex: `cd C:\Users\`
ls                   : List directory contents. Ex: `ls C:\Users\`
file download        : Pull a file from the host. Ex: `file download C:\Users\user\file.txt`
file upload          : Push a file to the host. Ex: `file upload C:\Temp\file.txt <base64>`

------------
Memory Store
------------
memstore list        : List all file names in the memstore.
memstore upload      : Upload a file to the implant memstore. Ex: `memstore upload <name> <base64>`
memstore download    : Download a file from the memstore. Ex: `memstore download <name>`
memstore delete      : Delete a file from the memstore. Ex: `memstore delete <name>`
memstore clear       : Wipe all files from the memstore.

-----------
C2 Strategy
-----------
strat active         : Show the active GET and POST strategies.
strat list           : List all strategies compiled into the implant.
strat set post       : Set the POST (exfil) strategy. Ex: `strat set post <strategy_name>`
strat set get        : Set the GET (tasking) strategy. Ex: `strat set get <strategy_name>`
strat set both       : Set both GET and POST in one command.
                       Ex (same): `strat set both <name>`
                       Ex (split): `strat set both <get_name> <post_name>`

---------
Execution
---------
bof                  : Execute a BOF. Ex: `bof <base64_bof> [args]`
                       From memstore: `bof *<name> [args]`

-----------
SMB Linking
-----------
link smb             : Link to a child implant via SMB pipes. Ex: `link smb <host> <inbox> <outbox>`
link list            : List all linked child implants.
unlink smb           : Sever link to a child. Ex: `unlink smb <child_uuid>`

```

---

## Implementation Details

### Communication & Serialization

All data between the server and implant uses **MessagePack** encoding — structured like JSON but significantly smaller and faster to parse.

**Task structure** (what the server sends the implant):
```json
{
  "task_uuid": "01932ba4-...",
  "implant_uuid": "01932ba4-...",
  "task": {
    "task_name": "file download",
    "args": {
      "file_path": "C:\\Users\\user\\file.txt"
    }
  }
}
```

**Response structure** (what the implant sends back):
```json
{
  "task_uuid": "01932ba4-...",
  "implant_uuid": "01932ba4-...",
  "result": {
    "message": { "type": "text", "value": "Success" },
    "data":    { "type": "bytes", "value": "<file bytes>" },
    "windows_error_code": { "type": "text", "value": "0" }
  }
}
```

**Beacon/check-in metadata** (sent by implant on every GET):
```json
[
  {
    "implant_uuid": "01932ba4-...",
    "system_hostname": "DESKTOP-ABC123",
    "external_ip": "10.0.0.5"
  }
]
```

Beacons are arrays to support SMB chaining — a chain's egress node sends metadata for itself and all children in a single beacon.

### Two-Stage Communication

To minimize traffic noise:

1. **Beacon (GET heartbeat):** A lightweight packet sent on each sleep cycle asking "do I have tasks?"
2. **Check-in (POST with results):** A full data connection opened only when the implant is returning task results.

### Implant Design

- **Language:** C++ (Windows-first)
- **Extension model:** BOFs loaded at runtime. The implant ships with zero offensive capability — everything is operator-loaded.
- **Build system:** Docker cross-compilation (`win_x64` image, CMake + Ninja). Produces `.exe` and `.dll` artifacts stored in MySQL.
- **Memory store:** In-process key-value store (RAM only). XOR-obfuscated at rest to hinder memory scanning.

### Network Profile Support

LongHaul network profiles control `http-get`, `http-post`, URI patterns, headers, transforms, and raw socket wire formats. Payload-staging and artifact configurations specific to other C2 frameworks are not supported.

### Encryption

Not currently implemented. Plan: standard asymmetric PKI for initial key exchange, then symmetric session encryption.

---

## Related Docs

- [Quickstart](QuickStart.md)
- [Advanced Setup](00%20Intro%20%26%20Setup/LongHaul%20C2%20-%20Advanced%20Setup.md)
- [Commands](02%20Implants/1.%20Commands.md)
- [Listeners](01%20Listeners/Overview.md)
- [Scripting / API](03%20Scripting/Overview.md)
