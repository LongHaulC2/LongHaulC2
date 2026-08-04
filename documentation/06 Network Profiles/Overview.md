# Mimicry

**Mimicry** is LongHaul's traffic-shaping feature. Define exactly what your C2 traffic looks like on the wire. You define *every* byte, so nearly every protocol can be created. This allows for rapid development/deployment of profiles without a server restart, or waiting for version updates. 

Mimicry has two core components:

- **Network Profiles** — TOML files that define the complete wire format: body templates, transform chains, and the tokens the implant substitutes at runtime. One profile = one protocol shape. The listener sends exactly what the profile specifies, nothing more.
- **Strategies** — how profiles are represented inside a built implant. Each listener+profile pair becomes a named strategy baked into the binary (e.g., `raw_0_0_0_0_80_HTTP_Mimicry`). Implants can carry multiple strategies and switch between them at runtime without redeployment.

> Why is this feature called mimicry?
> 1. It sounds cool
> 2. Nature does it: [Dictionary Definion](https://www.merriam-webster.com/dictionary/mimicry)

---

## Default Profiles

Several reference profiles ship out of the box:

| Profile | Looks like |
|---|---|
| `raw_http_profile.toml` | HTTP/1.1 |
| `raw_ntp_profile.toml` | NTPv4 over UDP |
| `raw_ftp_profile.toml` | FTP RETR/STOR |
| `raw_dns_profile.toml` | DNS EDNS0 over UDP |
| `raw_snmp_profile.toml` | SNMPv1/v2c |
| `raw_encrypted_http_profile.toml` | Encrypted HTTP/1.1 (symcrypt + base64url) |
| `raw_debug_profile.toml` | Bare msgpack (no transforms, for debugging only) |

---

## Profile Storage

Profiles are stored **server-side** in a database and managed through the API. The UI reads and writes profiles exclusively through the server.

- **Creation/Modification/Upload:** You can Create, Modify, and Upload profiles via the **Profile Editor** page. 
- **Auto-save:** When you create a listener, its profile is automatically saved to the server, specifically in the listener instances DB entry. This means that if a profile gets modified, it **does NOT** affect the already existing listeners. 
    > For example, if "Listener X" uses "Profile X", and "Profile X" gets modified and saved in place, Listener X will use the version of "Profile X" it was spawned with.
- **Seed Defaults:** On a fresh install, use the "Seed Defaults" button on the Profile Preview page to populate the server with the reference profiles that ship with LongHaul.
- **Multi-operator:** Because profiles live on the server, all operators on the team see the same profile library.

See the [API Reference](../04%20API%20Reference/Overview.md#profiles--apiv1profiles) for the full CRUD API if you want to manage profiles programmatically.

---

## Profile Type

There is one profile type: **Raw**. Raw profiles define the complete wire format for any TCP or UDP protocol — body templates, transforms, tokens. The listener adds zero framing beyond what the TOML specifies.

Transform operations include: `base64`, `base64url`, `prepend`, `append`, `netbios`, `netbiosu`, and `symcrypt` (AES-256-GCM encryption).

See [Profile Technical Reference](./Raw%20Profiles.md) for the full reference.

---

