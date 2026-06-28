# Scripting Overview

LongHaul exposes all of its functionality through a RESTful API, enabling full automation of C2 operations. Everything you can do in the UI, you can script.

The built-in **Scripts** page (`/scripts` in the UI) provides an in-browser editor and terminal for running Python scripts directly against the server — no separate tools needed.

---

## API Basics

- **Base URL:** `http://<server>:45045/api/v1/`
- **Auth:** JWT Bearer tokens (see below)
- **Content-Type:** `application/json` for most endpoints. `application/msgpack` accepted for task submission.
- **Swagger UI:** `http://<server>:45045/doc` (full interactive docs, always up to date)

### API Response Envelope

All successful responses follow this structure:

```json
{
  "status": "200",
  "message": "Success",
  "data": { ... }
}
```

Error responses use standard HTTP status codes (400, 401, 404, 429, 500) with a `message` field explaining the error.

---

## Authentication

All protected endpoints require a JWT `Bearer` token in the `Authorization` header.

### 1. Login

```bash
curl -s -X POST http://localhost:45045/api/v1/authentication/ \
  -H "Content-Type: application/json" \
  -d '{"username": "longhaul", "password": "P@ssw0rd1!"}'
```

**Response:**
```json
{
  "status": "200",
  "message": "Login Successful",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ..."
  }
}
```

- **Access tokens** expire after **15 minutes**.
- **Refresh tokens** expire after **1 day**.

### 2. Use the Token

```bash
TOKEN="eyJ..."
curl -s http://localhost:45045/api/v1/implants/ \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Refresh the Token

Exchange a valid refresh token for a new access token without re-logging in:

```bash
curl -s -X POST http://localhost:45045/api/v1/authentication/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN"
```

---

## API Namespaces

| Namespace | Base Path | Description |
|---|---|---|
| Authentication | `/api/v1/authentication/` | Login, refresh, register users |
| Implants | `/api/v1/implants/` | Manage implants, queue tasks, retrieve history |
| Listeners | `/api/v1/listeners/` | Create, start, stop, delete listeners |
| Build | `/api/v1/build/` | Build implant payloads, download artifacts |
| Filestore | `/api/v1/filestore/` | Upload/download staging files |
| Graph | `/api/v1/graph/` | Implant topology and network graph data |
| Health | `/api/v1/health/` | Server health check |

For the full endpoint reference, see [API Reference](../04%20API%20Reference/Overview.md).

---

## The Scripts Page

The `/scripts` page in the UI provides:

- **File browser** — reads scripts from `/var/lib/longhaulc2/` (configured at deploy time)
- **Code editor** — syntax-highlighted Python editor with save/save-as/reload
- **Inline terminal** — run `.py` scripts and stream stdout/stderr in real time

This lets you write and execute automation scripts without leaving the browser. Scripts run as subprocesses using the same Python environment as the client.

### Default Script Location

```
/var/lib/longhaulc2/
├── scripts/
│   ├── list_implants.py
│   ├── demo.py
│   └── ...
```

---

## Example Scripts

### List All Implants

```python
import requests

api_url = "http://localhost:45045"

# Login
r = requests.post(f"{api_url}/api/v1/authentication/", json={
    "username": "longhaul",
    "password": "P@ssw0rd1!"
})
token = r.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get implants
r = requests.get(f"{api_url}/api/v1/implants/", headers=headers)
implants = r.json().get("data", [])

for implant in implants:
    print(f"UUID: {implant['implant_uuid']} | Host: {implant.get('system_hostname', 'N/A')} | IP: {implant.get('external_ip', 'N/A')}")
```

### Queue a Task

```python
import requests

api_url = "http://localhost:45045"
implant_uuid = "01932ba4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

r = requests.post(f"{api_url}/api/v1/authentication/", json={
    "username": "longhaul", "password": "P@ssw0rd1!"
})
token = r.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Queue a directory listing
task = {
    "implant_uuid": implant_uuid,
    "task": {
        "task_name": "ls",
        "args": {"directory": "C:\\Users\\"}
    }
}
r = requests.post(f"{api_url}/api/v1/implants/{implant_uuid}/task", json=task, headers=headers)
task_uuid = r.json()["data"]["task_uuid"]
print(f"Queued task: {task_uuid}")
```

### Poll Task Result

```python
import time, requests

api_url = "http://localhost:45045"
implant_uuid = "01932ba4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
task_uuid    = "01932ba4-yyyy-yyyy-yyyy-yyyyyyyyyyyy"

# ... (auth omitted, same as above)
headers = {"Authorization": f"Bearer {token}"}

# Poll until the result arrives
for _ in range(30):
    r = requests.get(f"{api_url}/api/v1/implants/{implant_uuid}/task/{task_uuid}", headers=headers)
    data = r.json().get("data", {})
    response = data.get("task_response")
    if response:
        print(response)
        break
    time.sleep(5)
```

### Rotate Strategy on All Implants

```python
import requests

api_url = "http://localhost:45045"
new_profile = "raw_10_0_0_30_80_HTTP_Mimicry"

r = requests.post(f"{api_url}/api/v1/authentication/", json={
    "username": "longhaul", "password": "P@ssw0rd1!"
})
token = r.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

implants = requests.get(f"{api_url}/api/v1/implants/", headers=headers).json()["data"]

for implant in implants:
    uuid = implant["implant_uuid"]
    task = {
        "implant_uuid": uuid,
        "task": {
            "task_name": "strat set get",
            "args": {"strategy_name": new_profile}
        }
    }
    requests.post(f"{api_url}/api/v1/implants/{uuid}/task", json=task, headers=headers)
    print(f"Queued strat rotation for {uuid}")
```

---

## Rate Limiting

The API enforces a default rate limit of **5000 requests/minute per IP**. This is designed to accommodate high-frequency implant beacons while still protecting against abuse.

To disable rate limiting in dev mode:
```bash
PYTHONPATH=. python -m server.main --no-ratelimit
```

---

## Tips

- Use `?since=<task_uuid>` on the history endpoint to only fetch tasks newer than a given UUID (they're UUIDv7, so chronologically sortable).
- The Swagger UI at `/doc` always reflects the live API — useful for exploring endpoints and testing.
- The task queue is Redis-backed and volatile. If the server restarts, in-flight queued tasks (not yet picked up by the implant) are lost. Completed tasks are persisted in MySQL and Neo4j.
