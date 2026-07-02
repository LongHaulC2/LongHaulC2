# Mimicry

**Mimicry** is LongHaul's traffic-shaping feature. Define what your C2 traffic looks like on the wire — HTTP, NTP, DNS, FTP, or a custom binary protocol — without touching the implant or the server. New protocol in minutes, not a developer update.

Mimicry has two core components:

- **Network Profiles** — TOML files that define the complete wire format: body templates, transform chains, and the tokens the implant substitutes at runtime. One profile = one protocol shape. The listener sends exactly what the profile specifies, nothing more.
- **Strategies** — how profiles are represented inside a built implant. Each listener+profile pair becomes a named strategy baked into the binary (e.g., `raw_0_0_0_0_80_HTTP_Mimicry`). Implants can carry multiple strategies and switch between them at runtime without redeployment.

> **Note for operators familiar with Cobalt Strike:** LongHaul network profiles serve the same general purpose as Malleable C2 profiles, but are an independent implementation. The TOML schema, transform operations, and wire format model are specific to LongHaul — do not expect syntax compatibility.

---

## Default Profiles

Several reference profiles ship out of the box:

| Profile | Looks like |
|---|---|
| `raw_http_profile.toml` | HTTP/1.1 (default starting point) |
| `raw_ntp_profile.toml` | NTPv4 over UDP |
| `raw_ftp_profile.toml` | FTP RETR/STOR |
| `raw_dns_profile.toml` | DNS EDNS0 over UDP |
| `raw_snmp_profile.toml` | SNMPv1/v2c |
| `raw_encrypted_http_profile.toml` | Encrypted HTTP/1.1 (symcrypt + base64url) |
| `raw_debug_profile.toml` | Bare msgpack (no transforms, for debugging only) |

---

## Profile Storage

Profiles are stored **server-side** in a database and managed through the API. The UI reads and writes profiles exclusively through the server — there is no local filesystem dependency.

- **Upload:** Use the upload button on the **Listeners** or **Profile Preview** page to upload `.toml` files from your machine to the server.
- **Auto-save:** When you create a listener, its profile is automatically saved to the server. No manual upload needed for profiles already attached to a listener.
- **Seed Defaults:** On a fresh install, use the "Seed Defaults" button on the Profile Preview page to populate the server with the reference profiles that ship with LongHaul.
- **Multi-operator:** Because profiles live on the server, all operators on the team see the same profile library. Upload once, available everywhere.

See the [API Reference](../04%20API%20Reference/Overview.md#profiles--apiv1profiles) for the full CRUD API if you want to manage profiles programmatically.

---

## Profile Type

There is one profile type: **Raw**. Raw profiles define the complete wire format for any TCP or UDP protocol — body templates, transforms, tokens. The listener adds zero framing beyond what the TOML specifies.

Transform operations include: `base64`, `base64url`, `prepend`, `append`, `mask` (XOR), `netbios`, `netbiosu`, and `symcrypt` (AES-256-GCM encryption). The `symcrypt` transform provides authenticated encryption of token data — the key is shared between the profile and the compiled implant.

See [Raw Profiles](./Raw%20Profiles.md) for the full reference: structure, tokens, transforms, body template scope, encryption, binary encoding, disambiguation, examples, and common mistakes.

---

