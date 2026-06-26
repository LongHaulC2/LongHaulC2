# Network Profiles

A **network profile** is a TOML file that controls exactly what bytes an implant sends and receives. Profiles define packet structure, token placement, and transform chains for beacon (GET) and exfil (POST) traffic.

> **Note for operators familiar with Cobalt Strike:** LongHaul network profiles serve the same general purpose as Malleable C2 profiles, but are an independent implementation. The TOML schema, transform operations, and raw socket support are specific to LongHaul — do not expect syntax compatibility.

---

## Profile Types

| Type | Description |
|---|---|
| **HTTP** | Defines URI patterns, headers, query parameters, and body templates for HTTP/HTTPS traffic. The HTTP listener handles framing (status codes, Content-Length, etc.) automatically — the profile controls the shape of the content within that frame. |
| **Raw** | Defines the complete wire format for any TCP or UDP protocol. No framing is added by the listener. Whatever is in the `body` template is exactly what goes on the wire. Use this to mimic NTP, DNS, FTP, or any other protocol. See [Raw Profiles](./Raw%20Profiles.md) for full documentation. |

A single profile file can contain both `[http.*]` and `[raw.*]` sections, giving one implant multiple transport options it can switch between at runtime.

---

## File Location

Profiles are stored at:

```
/var/lib/longhaulc2/profiles/
```

Files must have a `.toml` extension. The **Profile Preview** page (`/profile-preview` in the UI) scans this directory and lets you load any profile directly into the previewer. Example profiles ship in `client/user/profiles/`.

---

## Tokens

Three tokens are replaced by the implant at runtime. **These are the only things in a profile that get substituted — everything else is sent literally.**

| Token | Replaced with |
|---|---|
| `<METADATA>` | Encoded beacon metadata (implant ID, host info, sleep settings, etc.). Used in GET requests. |
| `<CLIENT_ID>` | The implant's unique UUID. Used in POST requests. |
| `<OUTPUT>` | Task results going out (exfil), or server task payload coming in (response). Used in POST requests and server response bodies. |

If you put `<ANYTHING_ELSE>` in a body template, header value, or URI, it will be sent to the target **as-is, angle brackets and all.** There is no variable substitution beyond the three tokens above.

### Quick Example

```toml
# This URI sends literally: /api/v2/search?q=<METADATA>
# The implant replaces <METADATA> with the encoded beacon data.
uri = "/api/v2/search?q=<METADATA>"

# This URI sends literally: /api/v2/search?session_id=<session_id>
# <session_id> is NOT a recognized token — the angle brackets go on the wire.
uri = "/api/v2/search?session_id=<session_id>"   # WRONG: not a token
```

---

## Transform Chains

Transforms encode or modify the **data payload** (the token content) before it is injected into the template. They are applied in order. The template structure itself is never modified by transforms — only the bytes that replace a token.

### Supported Operations

| Op | Description | `val` field |
|---|---|---|
| `base64` | Standard Base64 encode | — |
| `base64url` | URL-safe Base64 encode, no padding (RFC 4648 §5) | — |
| `prepend` | Prepend a string or binary sequence | Required |
| `append` | Append a string or binary sequence | Required |
| `netbios` | NetBIOS encode (lowercase) | — |
| `netbiosu` | NetBIOS encode (uppercase) | — |

### Transform Order Matters

```toml
[http.get.client.metadata]
transforms = [
    { op = "base64" },
    { op = "prepend", val = "session-token=" }
]
```

Given input `HELLO`:
```
1. base64   →  SEVMTE8=
2. prepend  →  session-token=SEVMTE8=
```

The server **reverses** this chain automatically when it receives the packet. Swapping the order would produce different (wrong) results.

---

## HTTP Profile

### Sections

| Section | Description |
|---|---|
| `[http.get]` | HTTP GET (beacon check-in) |
| `[http.get.client]` | Outbound request: headers, body, token location |
| `[http.get.client.metadata]` | Transform chain applied to beacon metadata |
| `[http.get.server]` | Server response: headers, body |
| `[http.get.server.output]` | Transform chain applied to server task output |
| `[http.post]` | HTTP POST (exfil) |
| `[http.post.client]` | Outbound request: headers, parameters, body |
| `[http.post.client.id]` | Transform chain applied to `<CLIENT_ID>` |
| `[http.post.client.output]` | Transform chain applied to exfil output |
| `[http.post.server]` | Server response: headers, body |
| `[http.post.server.output]` | Transform chain applied to server response |

### Wire Contract for HTTP

The HTTP listener adds standard HTTP framing around your profile content. What you control:

- **`uri`** — the request path and query string, verbatim
- **`useragent`** — the User-Agent header value
- **`headers`** — additional headers, added exactly as specified
- **`parameters`** — query parameters appended to the URI
- **`body`** — the HTTP request body, verbatim

What the HTTP listener handles automatically: HTTP method line, `Content-Length`, status codes (200 for tasks, 204 for no-tasks), and basic connection management.

### Token Placement in HTTP

The `<METADATA>` token can appear in:
- A header value: `{ "Cookie" = "<METADATA>" }`
- The request body: `body = "<METADATA>"`
- The URI: `uri = "/search?q=<METADATA>"`

Only **one occurrence per request** is meaningful. If `<METADATA>` appears in multiple places, the Profile Preview tool will report which location it finds first.

### Minimal HTTP Example

```toml
[profile]
name   = "Example HTTP Profile"
author = "@operator"

[http.get]
method    = "GET"
uri       = "/api/v1/data"
useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

[http.get.client]
headers = [
    { "Accept"     = "*/*" },
    { "Cookie"     = "<METADATA>" }
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
method    = "POST"
uri       = "/api/v1/submit"
useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

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

## SMB Configuration

The optional `[smb]` section sets named pipe names for SMB pivot implants:

```toml
[smb]

[smb.get]
pipe_name = "msrpc_svr"

[smb.post]
pipe_name = "msrpc_svc"
```

These names are baked into implants built with an SMB listener target. The parent implant (with HTTP or raw egress) connects to the child over the named pipe.

---

## Profile Preview Tool

The **Profile Preview** page (`/profile-preview`) visualizes what a profile produces before attaching it to a live listener.

### Loading a Profile

- **From disk:** Select a `.toml` file from the dropdown.
- **Manual paste:** Type or paste TOML directly into the textarea.

### Rendering

Click **RENDER**. The right panel shows a tab per protocol section present in the profile (`HTTP_GET`, `HTTP_POST`, `SMB`, `RAW`) plus a **VALIDATION** tab.

For each section, the preview shows:
- The template structure (headers, URI, body)
- The token location (`header:Cookie`, `body`, `uri`, etc.)
- A step-by-step transform chain with intermediate output after each step, using the sample payload `PREVIEW_PAYLOAD`

Use the preview to confirm the transform chain produces what you expect before deploying.

### Saving

| Button | Behavior |
|---|---|
| Save | Overwrites the file currently loaded from disk. Opens Save As if no file is selected. |
| Save As | Enter a filename, saves to `/var/lib/longhaulc2/profiles/`. Auto-appends `.toml` if omitted. |

---

## API — Profile Preview

### `POST /api/v1/profiles/preview`

Parses and renders a profile. Always returns HTTP 200 — parse failures are returned as structured data, not 4xx errors.

**Request:**
```json
{ "profile_contents": "<raw TOML string>" }
```

**Response (success):**
```json
{
  "status": "200",
  "data": {
    "profile_name": "Example",
    "profile_author": "@operator",
    "http_get": { "..." : "..." },
    "http_post": { "..." : "..." },
    "smb": null,
    "raw_profiles": [],
    "validation": {
      "parse_ok": true,
      "parse_error": null,
      "missing_fields": [],
      "warnings": []
    }
  }
}
```

**Response (parse failure):**
```json
{
  "status": "200",
  "data": {
    "http_get": null, "http_post": null, "smb": null, "raw_profiles": [],
    "validation": {
      "parse_ok": false,
      "parse_error": "Invalid TOML at line 7: ...",
      "missing_fields": [], "warnings": []
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

## Common Mistakes

These mistakes are operationally dangerous — they cause the implant to send wrong bytes silently, with no error.

### 1. Using an unrecognized token

```toml
# WRONG — <session_id> is not a token. Sent literally on the wire:
#   Cookie: session_id=<session_id>
headers = [{ "Cookie" = "session_id=<session_id>" }]

# CORRECT — <METADATA> is the recognized token:
headers = [{ "Cookie" = "session_id=<METADATA>" }]
```

### 2. Putting static data in the wrong place

Transforms modify the *data inside the token*. They do not modify the template structure.

```toml
# WRONG — the word "Bearer" goes inside the base64'd metadata:
[http.get.client.metadata]
transforms = [{ op = "prepend", val = "Bearer " }, { op = "base64" }]
# Result in Cookie header: Cookie: <base64 of "Bearer " + metadata>

# CORRECT — put the static prefix in the header, base64 just the data:
[http.get.client]
headers = [{ "Authorization" = "Bearer <METADATA>" }]

[http.get.client.metadata]
transforms = [{ op = "base64" }]
# Result: Authorization: Bearer <base64 of metadata>
```

### 3. Forgetting that `append` adds to the token content, not the header

```toml
# You want:  Cookie: session=<base64>; path=/
# WRONG — the semicolon ends up inside the base64 value:
transforms = [{ op = "base64" }, { op = "append", val = "; path=/" }]

# CORRECT — put the static suffix outside the token in the header value:
headers = [{ "Cookie" = "<METADATA>; path=/" }]
transforms = [{ op = "base64" }]
```

### 4. Raw profiles: `\x` escapes in double-quoted TOML strings

TOML **basic strings** (double-quoted `"..."`) do not support `\x` hex escapes. They only support `\uXXXX` and standard escapes (`\n`, `\t`, `\\`, etc.). Using `\x` in a double-quoted string causes a TOML parse error.

```toml
# WRONG — TOML rejects \x in double-quoted strings:
{ op = "prepend", val = "\x23\x00\x06" }

# CORRECT — use TOML literal strings (single-quoted) for \xNN sequences:
{ op = "prepend", val = '\x23\x00\x06' }

# Also correct — use \uXXXX in double-quoted strings:
{ op = "prepend", val = "# " }
```

See [Raw Profiles](./Raw%20Profiles.md) for full details on binary encoding.
