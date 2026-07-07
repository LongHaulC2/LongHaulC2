# Listeners

A **listener** is a network process that handles inbound implant traffic. Each listener is bound to a port and a network profile that defines the traffic shape. Multiple listeners can run simultaneously with different profiles.

---

## How Listeners Work

Listeners run as **daemon multiprocesses** managed by a supervisor system. They are separate OS processes (not threads) so a crash in one listener does not affect the server or other listeners.

On server startup, previously running listeners get respawned. This allows listeners to survive server restarts automatically.

---

## Listener Types

| Type | Status | Transport |
|---|---|---|
| `raw` | **Implemented** | Plain TCP or UDP. The profile's `[raw.*]` body templates define the **complete wire format** — the listener adds nothing beyond what the TOML specifies. HTTP/1.1 mimicry, NTP, DNS, FTP, any binary protocol — all defined by the profile. `raw_http_profile.toml` ships as a ready-to-use HTTP/1.1 example. |
| `pivot_smb` | Placeholder | No process is started. Used as an internal marker for implants that connect via SMB chains rather than direct egress. |

> **This is different than most C2 suites. The raw listener is the only C2 channel.** Protocols/Traffic are defined by Network Profiles, see [Mimicry](../06%20Network%20Profiles/Overview.md) for more details.

---

## Creating a Listener

Listeners are created through the UI (**Listeners** page) or via the [API](../04%20API%20Reference/Overview#listeners--apiv1listeners)

...link to creating a listener video here...

### Field Reference

| Field | Type | Description |
|---|---|---|
| `listener_name` | string | Human-readable name. Used to identify the listener and to derive strategy names in the implant. |
| `listener_type` | string | One of: `raw`, `pivot_smb` |
| `listener_host` | string | IP or hostname the listener binds to (e.g., `0.0.0.0`) |
| `listener_port` | integer | Port to listen on (e.g., `80`, `123`, `53`) |
| `listener_profile_name` | string | Filename of the network profile (e.g., `raw_http_profile.toml`) |
| `listener_profile_contents` | string | Full TOML text of the network profile |
| `listener_notes` | string | Optional operator notes |



## Mimicry

Each listener is paired with a **network profile** that controls exactly what bytes go on the wire. See [Mimicry](../06%20Network%20Profiles/Overview.md) for more details. For now, just think of these profiles as malleable c2 on steroids.

Each listener gets **one** profile. Implants can be built with **multiple** profiles (aka strategies) and can switch between them at runtime with `strat set get` / `strat set post`.

### Strategies

Strategies are the name of the profiles after they are baked into an implant. The strategy names are derived from the **callback host** (set at build time), the listener port, and the profile name.

The naming pattern is:

```
raw_<callback_host>_<port>_<profile_name>
```

Where `<callback_host>` is the IP or hostname from the **Callback Host** field in the implant builder, `<port>` is the listener's port, and `<profile_name>` is taken from the `[profile] name = "..."` field in the TOML (non-alphanumeric characters replaced by underscores).

For example, building with callback host `60.1.1.1` and a listener on port `80` using a profile named `"HTTP Mimicry"` produces:

```
raw_60_1_1_1_80_HTTP_Mimicry
```

You can see available strategy names for the current implant by running `strat list` in the implant terminal:

```
--- SESSION ESTABLISHED ---
019f101d > strat list
--- Ingress (GET) ---
  > raw_60_1_1_1_80_HTTP_Mimicry
--- Egress (POST) ---
  > raw_60_1_1_1_80_HTTP_Mimicry
```

> Dev note - "Strategies" sounded cool when designing the switching/profile split logic, so I stuck with that naming. Feel free to call them "Profiles/Network Profiles/Mimicry Profiles, etc" as well. i.e. "I'm moving the implant to the FTP profile from the HTTP profile".

### Callback Host

The **Callback Host** field in the implant builder controls where the implant sends its traffic. This is intentionally decoupled from the listener's bind address to support common operational setups:

- **CDNs** — listener binds to `10.0.0.2`, implant calls back to `cdn.example.com`
- **Redirectors** — listener binds to `10.0.0.2`, implant calls back to `redirector.example.com` or a redirector's public IP
- **NAT / cloud** — listener binds to `0.0.0.0` on a private subnet, implant calls back to the public IP `203.0.113.50`

The callback host accepts an IP address or a hostname. The port is still determined by the listener — if the listener runs on port `443`, the implant calls back to `<callback_host>:443`.

**Example: CDN fronting**

| | Value |
|---|---|
| Listener bind address | `10.0.0.2` |
| Listener port | `443` |
| Callback Host (build field) | `cdn.example.com` |
| Strategy name in implant | `raw_cdn_example_com_443_HTTP_Mimicry` |
| Implant calls back to | `cdn.example.com:443` |

**Example: Redirector with public IP**

| | Value |
|---|---|
| Listener bind address | `10.0.0.2` |
| Listener port | `80` |
| Callback Host (build field) | `60.1.1.1` |
| Strategy name in implant | `raw_60_1_1_1_80_HTTP_Mimicry` |
| Implant calls back to | `60.1.1.1:80` |

**Example: Multiple strategies with shared callback host**

When building an implant with multiple listeners, each strategy gets the same callback host but keeps its own port:

| Listener | Bind | Port | Strategy Name |
|---|---|---|---|
| HTTP listener | `10.0.0.2` | `80` | `raw_60_1_1_1_80_HTTP_Mimicry` |
| NTP listener | `10.0.0.2` | `123` | `raw_60_1_1_1_123_NTP_Mimicry` |

The implant can switch between these at runtime with `strat set get` / `strat set post`.

---

## Raw Listener

The raw listener is the only "real" listener type in LongHaul. It sends and receives arbitrary bytes over TCP or UDP. The network profile's `[raw.*]` section defines the **complete wire format** — the listener adds no framing beyond what the profile specifies. Not a byte more, not a byte less.

What protocol your traffic looks like is entirely your decision. Profiles are stored on the server and managed through the UI or API. On a fresh install, use "Seed Defaults" on the Profile Preview page to load the reference profiles:

| Profile | Looks like |
|---|---|
| `raw_http_profile.toml` | HTTP/1.1 (default starting point) |
| `raw_ntp_profile.toml` | NTPv4 over UDP |
| `raw_ftp_profile.toml` | FTP RETR/STOR |
| `raw_dns_profile.toml` | DNS EDNS0 over UDP |
| `raw_snmp_profile.toml` | SNMPv1/v2c |
| `raw_encrypted_http_profile.toml` | Encrypted HTTP/1.1 (AES-256-GCM + base64url) |
| `raw_debug_profile.toml` | Bare msgpack (no transforms, intended for debugging) |

You can upload your own profiles from the Listeners page or the Profile Preview page. See [Mimicry](../06%20Network%20Profiles/Overview.md) for full documentation.

---

## SMB Pivot Listener (`pivot_smb`)

The `pivot_smb` type is a placeholder only — no listener/network process is started. It exists to represent implants in the graph that communicate via SMB named pipes through a parent implant, rather than reaching the server directly.

When you create a `pivot_smb` listener, the server registers it in Neo4j and makes it available as a build target so you can generate an implant that is configured to communicate over the SMB chain. The parent implant (with a `raw` listener) acts as the egress node.

---