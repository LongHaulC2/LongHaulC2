# Raw Profiles

A **raw profile** defines the complete wire format for a TCP or UDP connection. The body template is the packet. The listener adds nothing beyond what the profile specifies — not a byte more, not a byte less.

Unlike C2 frameworks where the wire format is fixed or partially controlled, here you own every byte. What protocol your traffic looks like — HTTP, NTP, DNS, FTP, custom binary — is an operator decision made in the TOML, not a capability baked into the implant. The shipped `raw_http_profile.toml` provides HTTP/1.1 mimicry as a starting point, but it is just one profile among many you can define or create.

---

## The Fundamental Rule

> **Whatever you put in `body` is what gets sent. The only substitutions are the three recognized tokens. Everything else is literal.**

This is what makes raw profiles powerful and what makes mistakes operationally dangerous. There is no implicit framing, no length prefix, no magic. The listener takes your body template, replaces the token with the transformed payload, and writes the resulting bytes to the socket.

If your body template for NTP contains a valid 48-byte NTP header structure, the packet looks like NTP. If it contains garbage, the packet contains garbage. **The profile preview tool is your only safety net before going live — use it.**

---

> **New to C2 beaconing?** See [Beaconing](../00%20Intro/Beaconing.md) for an explanation of the GET/POST communication loop before reading this section.

## Profile Structure

### Simple (one protocol per file)

```toml
[profile]
name = "Test Profile"

[raw.get]
proto = "udp"         # "tcp" or "udp"
body  = "<METADATA>"  # complete wire template for outbound beacon

[raw.get.client.metadata] # actions on the implant metadata
transforms = [ # transforms done to the inbound metadata
    { op = "base64url" }
]

[raw.get.server]
body = "<OUTPUT>"     # complete wire template for server response

[raw.get.server.output]
transforms = []

[raw.post]
proto = "udp"
body  = "<OUTPUT>"    # complete wire template for exfil

[raw.post.client.output]
transforms = [
    { op = "base64url" }
]

[raw.post.server]
body = ""             # ACK sent back (empty = no response)
```

---

## What Goes on the Wire

### Tokens

The same three tokens work in raw profiles:

| Token | Used in | Replaced with |
|---|---|---|
| `<METADATA>` | `[raw.get]` body | Encoded beacon metadata |
| `<OUTPUT>` | `[raw.post]` body and server response bodies | Encoded exfil data / encoded tasks |
| `<CLIENT_ID>` | `[raw.post]` body (optional) | Implant UUID |

No other substitution happens. `<ANYTHING_ELSE>` goes on the wire literally, including the angle brackets.

### TCP vs UDP

| Protocol | Framing |
|---|---|
| **TCP** | One message per connection. Implant connects → sends complete packet → closes write end → server reads until EOF → server responds → connection closes. |
| **UDP** | One datagram per transaction. Implant sends → server receives → server responds (or doesn't). |

For UDP with no pending tasks, the server sends nothing. The implant's recvfrom times out (5-second timeout) and the implant treats an empty response as "no tasks." This is correct and expected — do not add an ACK round-trip unless your protocol requires it.

### Server Response

The server response body is defined in `[raw.get.server]`. If `body = "<OUTPUT>"` and the server has tasks, it replaces `<OUTPUT>` with the encoded tasks and sends the full body. If `body = ""` or the server has nothing to send, nothing is transmitted.

---

## Transform Chains for Binary Data

Transforms work the same way as in HTTP profiles: they encode or modify the token data before it is placed into the body template. The critical difference for raw profiles is that the **transform output often contains binary bytes**, not printable ASCII.

### Recommended Encoding for Raw Protocols

| Use case | Recommended chain |
|---|---|
| Protocol mimicry where payload must fit in a specific field | `base64url` → `prepend <binary header>` |
| Protocol that already carries arbitrary binary | `prepend <binary header>` only |
| Protocol that requires printable payload | `base64` or `base64url` |

`base64url` is preferred over `base64` for raw profiles because it avoids `+`, `/`, and `=` characters that can appear semantically meaningful in text-based protocols.

---

## Encoding Binary Values in TOML

This is the most common source of mistakes in raw profiles.

### The Problem

TOML **basic strings** (double-quoted `"..."`) only allow a limited set of escape sequences: `\b \t \n \f \r \" \\ \uXXXX \UXXXXXXXX`. The `\x` hex escape is not valid in a basic string — TOML will reject the file with a parse error.

```toml
# PARSE ERROR — \x is not valid in a TOML basic string:
{ op = "prepend", val = "\x23\x00\x06\xEC" }
```

### Solution: TOML Literal Strings

TOML **literal strings** (single-quoted `'...'`) pass every character through unchanged — no escape processing. The server then interprets `\xNN` sequences at runtime, converting each one to the corresponding byte.

```toml
# CORRECT — single quotes, \xNN interpreted as hex bytes at runtime:
{ op = "prepend", val = '\x23\x00\x06\xEC' }
```

The character sequence `\x23` in a TOML literal string is four characters (backslash, x, 2, 3), not byte 0x23. The server reads those four characters and converts them to the single byte 0x23 before the prepend is applied.

### Rules

| TOML string type | Syntax | `\xNN` supported? | Use for |
|---|---|---|---|
| Basic string | `"..."` | **No** (parse error) | Simple ASCII values |
| Literal string | `'...'` | **Yes** (interpreted as bytes at runtime) | Binary sequences with null bytes and high bytes |
| Basic multi-line | `"""..."""` | No | Multi-line ASCII (not useful for transform vals) |
| Literal multi-line | `'''...'''` | Yes, but cannot use in inline tables | Not useful for inline table values |

### Complete Binary Encoding Example

NTP client request header (48 bytes) + private extension field (4 bytes):

```toml
[raw.get.client.metadata]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x23\x00\x06\xEC\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xF0\x01\x00\x04' }
]
```

The `\x00` bytes are literal null bytes. `\xEC` is byte 236 (Precision field = -20 as a signed byte). The prepend is applied after base64url encoding, so the final wire packet is:

```
[48-byte NTP header][4-byte extension header][base64url ASCII]
```

---

## Disambiguation: Beacon vs Exfil

The raw listener has no separate port or path for GET (beacon) vs POST (exfil) traffic. All packets arrive on the same socket. The listener uses a two-layer approach to tell them apart.

### Layer 1: binary prefix matching (primary)

If the GET and POST transform chains each end with a `prepend` operation that produces **distinct** byte sequences, the server reads the leading bytes of the incoming packet and routes directly:

- Packet starts with GET prepend bytes → handled as beacon (POST decode is never attempted)
- Packet starts with POST prepend bytes → handled as exfil (GET decode is never attempted)

This is fast, deterministic, and requires no parsing. The NTP profile demonstrates the correct pattern: GET uses extension type `0xF001` and POST uses `0xF002` — two distinct 52-byte prepend values that differ at byte 48.

> **If both GET and POST use a `prepend` transform, the prepend byte sequences MUST be distinct.** Identical values force the fallback path. See Common Mistake #6.

### Layer 2: msgpack shape guard (secondary, fallback only)

When no distinct prepend exists (prefixes absent or identical), the server falls back to trying GET then POST. Before calling the beacon handler, it peeks at the decoded msgpack: if the first element contains `task_uuid`, it's obviously exfil data and the GET path is rejected immediately.

This guard exists as a safety net for the fallback path. It is not a replacement for distinct prefixes — it catches the most common mistake but cannot handle every encoding edge case.

### Fallback: try-GET-then-POST

Reached only when prefix matching can't discriminate:

1. Apply the secondary shape guard (reject if `task_uuid` found)
2. If guard passes → attempt full beacon decode → call `handle_beacon`
3. If that fails at any step → try the POST decode chain

No type byte is added to the wire in either case — the protocol format stays clean.

**Bottom line:** Design your protocol so GET and POST are unambiguous at the byte level. Use the protocol's own type field (NTP extension type, DNS QR bit, etc.) as the differentiator and put it in the prepend value. Do not rely on the secondary guard as your primary disambiguation strategy.

---

## Example: NTP Mimicry

A working NTP profile ships at `client/user/profiles/raw_ntp_profile.toml`. Here is a walkthrough of how it works.

### Packet Design (RFC 5905)

The NTP packet is 48 bytes:

| Bytes | Field | Value |
|---|---|---|
| 0 | LI / VN / Mode | `0x23` — LI=0 (no leap warning), VN=4 (NTPv4), Mode=3 (client) |
| 1 | Stratum | `0x00` — unspecified (correct for client requests) |
| 2 | Poll | `0x06` — 2^6 = 64-second poll interval |
| 3 | Precision | `0xEC` — 2^-20 ≈ 1µs (−20 as a signed byte) |
| 4–7 | Root Delay | `0x00000000` |
| 8–11 | Root Dispersion | `0x00000000` |
| 12–15 | Reference Identifier | `0x00000000` (unset in client requests) |
| 16–47 | Timestamps (Reference / Origin / Receive / Transmit) | All zeros (exact time not required) |

After the 48-byte NTP header, a 4-byte private extension field header is appended (RFC 5905 §7.5):

| Bytes | Field | GET (beacon) | POST (exfil) |
|---|---|---|---|
| 48–49 | Field Type | `0xF001` (private, beacon) | `0xF002` (private, exfil) |
| 50–51 | Length | `0x0004` (header only) | `0x0004` |

The base64url-encoded payload follows directly after those 52 bytes. The extension field length is intentionally minimal (it does not include the payload length); this simplification is safe because our listener is the only consumer.

### Transform Flow

**Beacon (GET), implant → server:**
```
msgpack metadata
  → base64url
  → prepend 52-byte NTP client header (LI/VN/Mode=0x23, ext type=0xF001)
  → UDP datagram sent to listener
```

**Server response, server → implant:**
```
msgpack task array
  → base64url
  → prepend 52-byte NTP server header (LI/VN/Mode=0x24, Stratum=1, RefID="LOCL", ext type=0xF003)
  → UDP datagram sent to implant
```

**Exfil (POST), implant → server:**
```
msgpack task results
  → base64url
  → prepend 52-byte NTP client header (same as GET but ext type=0xF002)
  → UDP datagram sent to listener
  → (no ACK from server — NTP does not acknowledge a second packet)
```

### Creating the Listener

```bash
curl -s -X POST http://localhost:45045/api/v1/listeners/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "listener_name":             "ntp_egress",
    "listener_type":             "raw",
    "listener_host":             "0.0.0.0",
    "listener_port":             123,
    "listener_profile_name":     "raw_ntp_profile.toml",
    "listener_profile_contents": "<contents of raw_ntp_profile.toml>"
  }'
```

---

## ICMP

ICMP mimicry (RFC 792) is **not yet supported**. ICMP requires raw IP sockets (`SOCK_RAW` / `IPPROTO_ICMP`), which need elevated privileges (root on Linux, Administrator on Windows) on both the implant and the server. The raw listener currently supports TCP and UDP only. Extend with `proto = "icmp"` when that support is implemented.

---

## Common Mistakes

### 1. Treating the body template as anything other than literal bytes

```toml
# You want to send a 48-byte NTP packet followed by data.
# WRONG — this puts the literal text "NTP_HEADER" on the wire, not bytes:
body = "NTP_HEADER<METADATA>"

# CORRECT — put the binary header in a prepend transform, not in the body:
body = "<METADATA>"

[raw.get.client.metadata]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x23\x00\x06\xEC...' }  # actual NTP header bytes
]
```

### 2. Forgetting that `\xNN` requires single-quoted strings

```toml
# PARSE ERROR — TOML rejects \x in double-quoted strings:
transforms = [{ op = "prepend", val = "\x23\x00" }]

# CORRECT:
transforms = [{ op = "prepend", val = '\x23\x00' }]
```

### 3. Identical GET and POST prepend values (silent exfil loss)

If GET and POST both use a `prepend` transform with the **same** byte sequence, binary prefix matching cannot distinguish them. The server falls back to try-GET-then-POST. In this fallback, exfil packets (which contain `implant_uuid`) can pass the secondary shape guard and be accepted by `handle_beacon` as a check-in with no tasks — the exfil result is silently discarded and never stored.

```toml
# BROKEN — identical prepend on GET and POST; server cannot tell them apart
[raw.get.client.metadata]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x00\x01\x02\x03' }
]

[raw.post.client.output]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x00\x01\x02\x03' }   # same bytes — broken
]
```

```toml
# CORRECT — use the protocol's own type field to differentiate
[raw.get.client.metadata]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x00\x01\x02\xF0\x01' }   # type = 0xF001
]

[raw.post.client.output]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x00\x01\x02\xF0\x02' }   # type = 0xF002 — distinct
]
```

Use the protocol's own type/opcode/flag field as the differentiator. NTP does this with extension field types. DNS uses the QR bit in the flags field. FTP uses different command strings. Whatever the protocol provides, encode it in your prepend so the server can route without guessing.

### 4. No prepend transform at all (relies entirely on fallback)

If neither GET nor POST uses a `prepend` transform, binary prefix matching is skipped entirely. The server uses try-GET-then-POST with the secondary shape guard. This works only if the exfil data reliably contains `task_uuid` in the first element AND the msgpack decode of random GET data always fails. Both conditions usually hold, but this is fragile — any encoding edge case can break it.

**Always include a `prepend` transform** with distinct values for GET and POST. Even a 1-byte type tag is enough:

```toml
[raw.get.client.metadata]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x01' }   # type: beacon
]

[raw.post.client.output]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x02' }   # type: exfil
]
```

---

### 5. Expecting the listener to handle protocol-specific concerns automatically

The raw listener does not:
- Compute checksums (NTP, UDP, TCP, IP)
- Set IP TTL or other IP-layer fields
- Handle protocol-level fragmentation
- Manage connection state beyond a single connect/send/receive cycle

If the protocol you are mimicking requires correct checksums (e.g., IP-layer ICMP), you need either a raw socket implementation or a different approach.

### 6. Multi-line body templates

The `body` field is a TOML string. Use `\r\n` escapes in a basic string to embed carriage-return/line-feed bytes directly:

```toml
body = "GET /api HTTP/1.1\r\nHost: example.com\r\n\r\n<METADATA>"
```

Note: `\r` and `\n` ARE valid in TOML basic strings. For binary null bytes or other non-ASCII bytes, use a literal string with `\x00`.

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

These names are baked into implants built with an SMB listener target. The parent implant (with raw egress) connects to the child over the named pipe.

---

## Profile Preview Tool

The **Profile Preview** page (`/profile-preview`) visualizes what a profile produces before attaching it to a live listener.

### Loading a Profile

- **From disk:** Select a `.toml` file from the dropdown.
- **Manual paste:** Type or paste TOML directly into the textarea.

### Rendering

Click **RENDER**. The right panel shows a tab per protocol section present in the profile (`RAW`, `SMB`) plus a **VALIDATION** tab.

For each section, the preview shows:
- The body template and proto (tcp/udp)
- The token location (`body`, etc.)
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
    "profile_name": "HTTP Mimicry",
    "profile_author": "LongHaul Team",
    "smb": null,
    "raw_profiles": [
      {
        "name": "default",
        "get": {
          "proto": "tcp",
          "client": { "body": "<METADATA>", "metadata_token_location": "body", "metadata_transforms": [...] },
          "server": { "body": "<OUTPUT>", "output_transforms": [...] }
        },
        "post": {
          "proto": "tcp",
          "client": { "body": "<OUTPUT>", "output_token_location": "body", "output_transforms": [...] },
          "server": { "body": "HTTP/1.1 200 OK\r\n\r\n", "output_transforms": [] }
        }
      }
    ],
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
    "smb": null,
    "raw_profiles": [],
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
