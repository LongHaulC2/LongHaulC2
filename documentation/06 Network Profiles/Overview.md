# Network Profiles

A **network profile** is a TOML file that controls how an implant's traffic looks on the wire. Profiles define URI templates, HTTP headers, query parameters, body formats, and transform chains for beacon (GET) and exfil (POST) traffic. The concept is similar to Cobalt Strike's Malleable C2 profiles, but focused on the network layer only — LongHaul does not implement payload-staging or process-injection configuration.

Each listener is paired with one profile at creation time. An implant can hold multiple listener/profile combinations and switch between them at runtime with `strat set get` / `strat set post`.

---

## File Location

Profiles are stored at:

```
/var/lib/longhaulc2/profiles/
```

Files must have a `.toml` extension. The **Profile Preview** page (`/profile-preview` in the UI) scans this directory and lets you load any profile directly into the previewer.

---

## File Format

Profiles are plain TOML. The top-level sections are:

| Section | Description |
|---|---|
| `[profile]` | Metadata: name and author |
| `[http.get]` | HTTP GET (beacon check-in) configuration |
| `[http.get.client]` | Headers, body template, and transform chains for the outbound beacon request |
| `[http.get.server]` | Headers, body template, and transform chains for the server's response |
| `[http.post]` | HTTP POST (exfil) configuration |
| `[http.post.client]` | Headers, parameters, body template, and transform chains for the exfil request |
| `[http.post.server]` | Headers, body, and transform chains for the server's response to an exfil |
| `[smb]` | SMB named pipe names for lateral movement (optional) |

### Minimal Example

```toml
[profile]
name   = "Example Profile"
author = "@operator"

[http.get]
method = "GET"
uri    = "/api/v1/data"

[http.get.client]
headers = [
    { "Accept" = "*/*" },
    { "Cookie" = "<METADATA>" }
]
body = ""

[http.get.client.metadata]
transforms = [
    { op = "base64" },
    { op = "prepend", val = "session=" }
]

[http.get.server]
headers = [{ "Content-Type" = "application/json" }]
body    = "<OUTPUT>"

[http.get.server.output]
transforms = []

[http.post]
method = "POST"
uri    = "/api/v1/submit"

[http.post.client]
headers    = [{ "Content-Type" = "application/x-www-form-urlencoded" }]
parameters = [{ id = "<CLIENT_ID>" }]
body       = "<OUTPUT>"

[http.post.client.id]
transforms = []

[http.post.client.output]
transforms = [{ op = "base64" }]

[http.post.server]
headers = [{ "Content-Type" = "text/plain" }]
body    = "<OUTPUT>"

[http.post.server.output]
transforms = []
```

---

## Token Placeholders

Three special tokens are replaced by the implant at runtime:

| Token | Replaced with | Used in |
|---|---|---|
| `<METADATA>` | Beacon metadata (sleep time, implant ID, host info, etc.) | `[http.get.client]` headers, body, or URI |
| `<CLIENT_ID>` | The implant's unique identifier | `[http.post.client]` headers, parameters, body, or URI |
| `<OUTPUT>` | Task results (exfil) or server task payload (response) | `[http.post.client]` body; server response bodies |

The profile preview tool shows you exactly which header, parameter, or body field each token lands in.

---

## Transform Chains

Transforms encode or modify a data payload before it is injected into the request or response. They are applied in order, one step at a time.

### Supported Operations

| Op | Description | `val` field |
|---|---|---|
| `base64` | Standard Base64 encode | — |
| `base64url` | URL-safe Base64 encode (RFC 4648 §5) | — |
| `prepend` | Prepend a string | Required — the string to prepend |
| `append` | Append a string | Required — the string to append |
| `mask` | XOR each byte with the bytes of `val` (cyclic) | Required — the XOR key string |
| `netbios` | NetBIOS encode (lowercase) | — |
| `netbiosu` | NetBIOS encode (uppercase) | — |

### Example

```toml
[http.get.client.metadata]
transforms = [
    { op = "base64" },
    { op = "prepend", val = "session-token=" },
    { op = "append",  val = "; path=/" }
]
```

Applied to `PREVIEW_PAYLOAD`:

```
INPUT          →  PREVIEW_PAYLOAD
base64         →  UFJFVklFV19QQVlMT0FE
prepend        →  session-token=UFJFVklFV19QQVlMT0FE
append         →  session-token=UFJFVklFV19QQVlMT0FE; path=/
```

---

## SMB Configuration

The optional `[smb]` section sets named pipe names for SMB pivot implants:

```toml
[smb]
inbox_pipe_name  = "msrpc_svr"
outbox_pipe_name = "msrpc_svc"
```

These names are baked into implants built with an `smb` listener target. The parent implant (with HTTP egress) connects to the child over the named pipe.

---

## Profile Preview Tool

The **Profile Preview** page (`/profile-preview`) lets you visualize what a profile produces before attaching it to a live listener.

### Loading a Profile

- **From disk:** Select a `.toml` file from the dropdown (scans `/var/lib/longhaulc2/profiles/`). Use the refresh button to pick up newly added files.
- **Manual paste:** Type or paste TOML directly into the textarea.

### Rendering

Click **RENDER** to send the profile to the server. The right panel shows:

- A tab per protocol section present in the profile (`HTTP_GET`, `HTTP_POST`, `SMB`)
- A **VALIDATION** tab with parse status, missing fields, and warnings
- For each HTTP section:
  - Method, URI, User-Agent
  - CLIENT REQUEST: headers, query parameters, body, token locations
  - Step-by-step transform chain with intermediate output at each step
  - SERVER RESPONSE: headers, body, response transforms

The preview uses a sample payload (`PREVIEW_PAYLOAD`) so you can see exactly what the transform chain produces.

### Saving

| Button | Behavior |
|---|---|
| Save (`save` icon) | Overwrites the file currently loaded from disk. If content was pasted manually (no file selected), opens Save As. |
| Save As (`save_as` icon) | Opens a dialog — enter a filename, saves to `/var/lib/longhaulc2/profiles/`. Auto-appends `.toml` if omitted. Refreshes the dropdown after saving. |

---

## API — Profile Preview

### `POST /api/v1/profiles/preview`

Parse and render a profile. Always returns HTTP 200 — parse failures are returned as data, not API errors.

**Request body:**
```json
{ "profile_contents": "<raw TOML string>" }
```

**Response shape (success):**
```json
{
  "status": "200",
  "data": {
    "profile_name": "Amazon Browsing",
    "profile_author": "@harmj0y",
    "http_get": {
      "method": "GET",
      "uri": "/s/ref=nb_sb_noss_1/...",
      "useragent": "",
      "client": {
        "headers": [{ "Cookie": "<METADATA>" }],
        "body": "",
        "metadata_token_location": "header:Cookie",
        "metadata_transforms": [
          { "op": "base64", "result_display": "UFJFVklFV19QQVlMT0FE" },
          { "op": "prepend", "val": "session-token=", "result_display": "session-token=UFJFVklFV19QQVlMT0FE" }
        ]
      },
      "server": {
        "headers": [{ "Server": "Server" }],
        "body": "<OUTPUT>",
        "output_transforms": []
      }
    },
    "http_post": { "...": "same structure" },
    "smb": null,
    "validation": {
      "parse_ok": true,
      "parse_error": null,
      "missing_fields": [],
      "warnings": []
    }
  }
}
```

**Response shape (parse failure):**
```json
{
  "status": "200",
  "data": {
    "http_get": null,
    "http_post": null,
    "smb": null,
    "validation": {
      "parse_ok": false,
      "parse_error": "Invalid TOML: ...",
      "missing_fields": [],
      "warnings": []
    }
  }
}
```

**curl example:**

```bash
curl -s -X POST http://localhost:45045/api/v1/profiles/preview \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"profile_contents\": $(jq -Rs . < /var/lib/longhaulc2/profiles/my_profile.toml)}"
```

---

## Adding a New Protocol

The preview endpoint is designed to be additive. When a new transport (e.g., NTP) is ready:

1. Add a new model in `server/api_models/profile.py`
2. Add a nullable `fields.Nested` field for the new protocol to `PROFILE_PREVIEW_DATA_MODEL`
3. Add an extraction block in `server/routes/v1/profile_resource.py`
4. The UI tab appears automatically — the frontend builds tabs dynamically from non-null keys in the response

No structural changes are needed in existing code.
