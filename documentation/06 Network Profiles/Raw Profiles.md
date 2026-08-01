# Profile Technical Reference

A **raw profile** defines the complete wire format for a TCP or UDP connection. The listener adds nothing beyond what the profile specifies.

Unlike most C2 frameworks where the wire format is fixed or partially controlled, here you own every byte. See [Mimicry Profiles](06%20Network%20Profiles/Overview) for a high level overview on this.

This doc will go into the technical specifics of profiles, and limitations around them. 

---

## The Fundamental Rule

> **Whatever you put in the profile is what gets sent. The only substitutions are the two recognized tokens. Everything else is literal.**

This is what makes raw profiles powerful and what makes mistakes operationally dangerous. There is no implicit framing, no length prefix, no magic. The listener takes your body template, replaces the token with the transformed payload, and writes the resulting bytes to the socket.

If your profile for NTP contains a valid NTP packet structure, the packet will look like NTP to network tooling (i.e., Wireshark). If it contains garbage, the packet will contain garbage, and likely won't be recognized. 

> The Profile Editor tool is meant to minimize mistakes and confusion, so be sure to use it.

---

<!-- >> **New to C2 beaconing?** See [Beaconing](../00%20Intro/Beaconing.md) for an explanation of the GET/POST communication loop before reading this section. -->

## Profile Structure

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

> Note: Don't worry about memorizing this structure. The Profile Editor tool has a GUI that builds the profiles for you

---

## Tokens

Tokens are placeholders for implant data. They are represented via `<` and `>`.

| Stage | Direction | Payload (The data that tokens represent) | Profile token |
|---|---|---|---|
| GET (beacon) | implant → server | Implant metadata: UUID, hostname, external IP, sleep interval, etc | `<METADATA>` in `[raw.get]` |
| GET (response) | server → implant | Pending tasks (msgpack-encoded), or empty if none | `<OUTPUT>` in `[raw.get.server]` |
| POST (exfil) | implant → server | Task results: output, error code, task UUID | `<OUTPUT>` in `[raw.post]` |
| POST (response) | server → implant | ACK, or empty | `[raw.post.server]` body |

---

## Transforms

Transforms are what is used to "transform" the implant data in various ways, which is extremely beneficial for data smuggling.

If you've ever worked with MalleableC2, this concept will be familiar. 

### Available Transform Operations

| Operation | TOML syntax | Description |
|---|---|---|
| `base64` | `{ op = "base64" }` | Standard Base64 encode/decode |
| `base64url` | `{ op = "base64url" }` | URL-safe Base64 (no padding) |
| `prepend` | `{ op = "prepend", val = '\xAA\xBB' }` | Prepend literal bytes before the data |
| `append` | `{ op = "append", val = '\xCC\xDD' }` | Append literal bytes after the data |
| `netbios` | `{ op = "netbios" }` | NetBIOS encoding (lowercase a-p) |
| `netbiosu` | `{ op = "netbiosu" }` | NetBIOS encoding (uppercase A-P) |
| `symcrypt` | `{ op = "symcrypt", key = '\x...' }` | AES-256-GCM symmetric encryption (32-byte key required) |


### Body

`body` is a section used to make framing data a bit easier. For example:

If you don't want to use a `prepend` operation a million times to build a profile (i.e., an HTTP header), you can use the `body=` section of the profile to frame it out:

```
[raw.get]
proto = "tcp"
body = "GET /update?data=<METADATA> HTTP/1.1\r\nHost: example.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0\r\nAccept: */*\r\nConnection: close\r\n\r\n"

[raw.get.client.metadata]
transforms = [
    { op = "symcrypt", key = '\x83\x82\x28\x7f\xd1\x22\xc5\x64\x95\x26\xcc\x6a\x0d\xd0\x5c\xa6\xdf\x27\x46\x7f\xd5\xe8\x6d\xb8\x33\xc6\x40\xca\x09\xcb\x14\xa6' },
    { op = "base64" }
]
```

This then shows up on the wire as:

```
GET /update?data=2E1JwywbJdYFA8veshirRSYjUc2V1NGfl713v/sCyYQK03wArG2WV9BtfQ== HTTP/1.1
Host: example.com
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0
Accept: */*
Connection: close

```


### Body Template Scope

SUPER IMPORTANT: **Transforms apply only to the token value, not the surrounding body template.**

When you write:

```toml
body = "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n<METADATA>"

[raw.get.client.metadata]
transforms = [
    { op = "symcrypt", key = '\xDE\xAD\xBE\xEF...' },
    { op = "base64" }
]
```

The transform chain operates on the raw metadata bytes *before* they replace the `<METADATA>` token:

1. Raw metadata (msgpack bytes) → `symcrypt` encrypts → encrypted bytes
2. Encrypted bytes → `base64` encodes → printable ASCII string
3. The ASCII result replaces `<METADATA>` in the body template
4. Final wire payload: `GET / HTTP/1.1\r\nHost: example.com\r\n\r\n<base64 string here>`

The `GET / HTTP/1.1\r\nHost: example.com\r\n\r\n` framing stays **plaintext**. Only the token's content is transformed. This is by design:

- Protocol framing must remain readable by network devices and the listener's disambiguation logic. Otherwise, it would be impossible to mimic a protocol.
- The payload within the framing is the sensitive data that needs protection
- Mixing framing and payload in the same encryption would break protocol mimicry

The same applies to the `<OUTPUT>` token.

---

## What Goes on the Wire

Now that we have Profile structure, Tokens, and Transforms covered, lets talk about how it all works together.

### Tokens

The same two tokens mentioned in [Tokens](#tokens) work in raw profiles:

| Token | Used in | Replaced with |
|---|---|---|
| `<METADATA>` | `[raw.get]` body | Encoded beacon metadata |
| `<OUTPUT>` | `[raw.post]` body and server response bodies | Encoded exfil data / encoded tasks |

No other substitution happens. For example, `<ANYTHING_ELSE>` goes on the wire literally, including the angle brackets.

### TCP vs UDP

You can choose between TCP and UDP for your profile. Each have a few considerations to keep in mind.

| Protocol | Framing |
|---|---|
| **TCP** | One message per connection. Implant connects → sends complete packet → closes write end → server reads until EOF → server responds → connection closes. |
| **UDP** | One datagram per transaction. Implant sends → server receives → server responds (or doesn't). |

> Note: For UDP with no pending tasks, the server sends nothing. The implant's recvfrom times out (5-second timeout) and the implant treats an empty response as "no tasks." This is correct and expected — do not add an ACK round-trip unless your protocol requires it.

> Note 2: UDP inherently has a size limit. See the [UDP size constraint section](#udp-size-constraint).

### Binary & Text values 

Profiles support both Binary, and Text based inputs. 

In a nutshell, use `\xNN` for direct binary, and `normal text` to have the data be encoded as ASCII, for text based protocols. 

| Input | Type | Wire Output (Shown as hex here) |
| --- | --- | --- |
| `AABB` | Text | `0x41,0x41,0x42,0x42` |
| `\x00\x00` | Bytes | `0x00,0x00` |

#### Encoding

Currently ASCII is the only supported text encoding. If you really wanted to mimic another encoding, just input that data as bytes.

For example, an emoji in a social media profile `😀`:

| Input | Type | Wire Output (Shown as hex here) |
| --- | --- | --- |
| `\xf0\x9f\x98\x80` (`😀` in hex) | Bytes (UTF-8 Emoji) | `0xf0,0x9f,0x98,0x80` |

> Note: TOML has some input quirks, see [Encoding Binary Values in TOML](#encoding-binary-values-in-toml) for more info. 
>
> If you use the Profile Editor, this is handled for you. 


<!-- ### Loose overview of each step? May not be for here. 

### GET (REQ TO SERVER)

```
...
```

### GET (RESP FROM SERVER)
```
...
```

### POST (REQ TO SERVER)
```
...
```

### POST (RESP FROM SERVER)
```
...
``` -->

<!-- 
### Server Response (Cut?)

The server response body is defined in `[raw.get.server]`. 

If `body = "<OUTPUT>"` and the server has tasks, it replaces `<OUTPUT>` with the encoded tasks and sends the full body. If `body = ""` or the server has nothing to send, nothing is transmitted. -->

---


## Example: NTP Mimicry

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

---

## Gotcha's

### UDP Size Constraint

UDP datagrams have a hard size limit of approximately **65,507 bytes** (IPv4 max payload minus IP and UDP headers). There is currently no application-layer chunking or reassembly, each GET/POST is a single datagram. If the payload (after all transforms are applied) exceeds this limit, the send will fail and the data is lost.

**Transform amplification makes this smaller than you'd expect.** Transforms expand the raw payload before it hits the wire:

| Transform | Size multiplier |
|---|---|
| `base64` / `base64url` | ~1.33x |
| `netbios` / `netbiosu` | 2x |
| `symcrypt` | +28 bytes (nonce + tag) |
| `prepend` / `append` | +N bytes |

With a `base64url` + `prepend` chain (like the NTP profile), the practical raw payload limit is roughly **48KB** before the encoded datagram exceeds 64KB. Chaining `base64` + `netbios` drops the effective limit to around **24KB**.

---


### Encoding Binary Values in TOML

This is the most common source of mistakes in profiles written outside of the Profile Editor.

#### The Problem

TOML **basic strings** (double-quoted `"..."`) only allow a limited set of escape sequences: `\b \t \n \f \r \" \\ \uXXXX \UXXXXXXXX`. The `\x` hex escape is not valid in a basic string — TOML will reject the file with a parse error.

```toml
# PARSE ERROR — \x is not valid in a TOML basic string:
{ op = "prepend", val = "\x23\x00\x06\xEC" }
```

#### Solution: TOML Literal Strings

TOML **literal strings** (single-quoted `'...'`) pass every character through unchanged, with no escape processing. The server then interprets `\xNN` sequences at runtime, converting each one to the corresponding byte.

```toml
# CORRECT — single quotes, \xNN interpreted as hex bytes at runtime:
{ op = "prepend", val = '\x23\x00\x06\xEC' }
```

The character sequence `\x23` in a TOML literal string is four characters (backslash, x, 2, 3), not byte `0x23`. The server reads those four characters and converts them to the single byte `0x23` before the prepend is applied.

> Why? The TLDR is this approach was easier, and gives explicit control to make sure that all \xNN values actually show up as bytes.

#### Rules

| TOML string type | Syntax | `\xNN` supported? | Use for |
|---|---|---|---|
| Basic string | `"..."` | **No** (parse error) | Simple ASCII values |
| Literal string | `'...'` | **Yes** (interpreted as bytes at runtime) | Binary sequences with null bytes and high bytes |
| Basic multi-line | `"""..."""` | No | Multi-line ASCII (not useful for transform vals) |
| Literal multi-line | `'''...'''` | Yes, but cannot use in inline tables | Not useful for inline table values |

#### Complete Binary Encoding Example

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


### Important - GET vs POST disambiguation

The raw listener has no separate port or path for GET (beacon) vs POST (exfil) traffic. All packets arrive on the same socket. The listener uses a two-layer approach to tell them apart.

> TLDR: Make your GET and POST implementation in a profile *slighty* different or the server cannot tell them apart. 

#### Layer 1: binary prefix matching (primary)

If the GET and POST transform chains each end with a `prepend` operation that produces **distinct** byte sequences, the server reads the leading bytes of the incoming packet and routes directly:

- Packet starts with GET prepend bytes → handled as beacon (POST decode is never attempted)
- Packet starts with POST prepend bytes → handled as exfil (GET decode is never attempted)

This is fast, deterministic, and requires no parsing. The NTP profile demonstrates the correct pattern: GET uses extension type `0xF001` and POST uses `0xF002` — two distinct 52-byte prepend values that differ at byte 48.

> **If both GET and POST use a `prepend` transform, the prepend byte sequences MUST be distinct.** Identical values force the fallback path.

#### Layer 2: msgpack shape guard (secondary, fallback only)

When no distinct prepend exists (prefixes absent or identical), the server falls back to trying GET then POST. Before calling the beacon handler, it peeks at the decoded msgpack: if the first element contains `task_uuid`, it's obviously exfil data and the GET path is rejected immediately.

This guard exists as a safety net for the fallback path. It is not a replacement for distinct prefixes — it catches the most common mistake but cannot handle every encoding edge case.

#### Fallback: try-GET-then-POST

Reached only when prefix matching can't discriminate:

1. Apply the secondary shape guard (reject if `task_uuid` found)
2. If guard passes → attempt full beacon decode → call `handle_beacon`
3. If that fails at any step → try the POST decode chain

No type byte is added to the wire in either case — the protocol format stays clean.

**Bottom line:** Design your protocol so GET and POST are unambiguous at the byte level. Use the protocol's own type field (NTP extension type, DNS QR bit, etc.) as the differentiator and put it in the prepend value. Do not rely on the secondary guard as your primary disambiguation strategy.


---

## Common Mistakes

### Treating the body template as anything other than literal bytes

```toml
# You want to send a 48-byte NTP packet followed by data.
# WRONG — this puts the ascii encoded text "NTP_HEADER" on the wire, not bytes:
body = "NTP_HEADER<METADATA>"

# CORRECT — put the binary header in a prepend transform, or in the body as delimited bytes. (\xNN\xNN)
body = "<METADATA>"

[raw.get.client.metadata]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = '\x23\x00\x06\xEC...' }  # actual NTP header bytes
]
```

### Forgetting that `\xNN` requires single-quoted strings

```toml
# PARSE ERROR — TOML rejects \x in double-quoted strings:
transforms = [{ op = "prepend", val = "\x23\x00" }]

# CORRECT:
transforms = [{ op = "prepend", val = '\x23\x00' }]
```

> Again, not an issue if you use the Profile Editor. It will handle this for you.

### Identical GET and POST prepend values (silent exfil loss)

If GET and POST both use a `prepend` transform with the **same** byte sequence, binary prefix matching cannot distinguish them. The server falls back to try-GET-then-POST. In this fallback, exfil packets (which contain `implant_uuid`) can pass the secondary shape guard and be accepted by `handle_beacon` as a check-in with no tasks, the exfil result is silently discarded and never stored.

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

You can also do this at the body level:

```
[raw.get]
body = "\x01<METADATA>"

[raw.post]
body = "\x02<OUTPUT>"

```

Use the protocol's own type/opcode/flag field as the differentiator. NTP does this with extension field types. DNS uses the QR bit in the flags field. FTP uses different command strings. Whatever the protocol provides, encode it in your prepend so the server can route without guessing.

<!-- ### 4. No prepend transform at all (relies entirely on fallback)

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
 -->


---

### Expecting the listener to handle protocol-specific concerns automatically

The raw listener does not:
- Compute checksums (NTP, UDP, TCP, IP)
- Set IP TTL or other IP-layer fields
- Handle protocol-level fragmentation
- Manage connection state beyond a single connect/send/receive cycle

### Multi-line body templates

The `body` field is a TOML string. Use `\r\n` escapes in a basic string to embed carriage-return/line-feed bytes directly:

```toml
body = "GET /api HTTP/1.1\r\nHost: example.com\r\n\r\n<METADATA>"
```

> Note: When using the Profile Editor, the body text field allows for enter key based newlines, or literal `\r\n`. 
>
> Both are rendered as `\r\n` in the final profile.

---
