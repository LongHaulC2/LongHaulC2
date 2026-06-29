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

Strategies are the name of the profiles after they are baked into an implant. The strategy names are derived from the listener data that said strategy corresponds to. 

For example:

```
raw_<host>_<port>_<profile_name>
```

Where `<profile_name>` is taken from the `[profile] name = "..."` field in the TOML, with non-alphanumeric characters replaced by underscores. For example, a listener on `0.0.0.0:80` using a profile named `"HTTP Mimicry"` produces the strategy name `raw_0_0_0_0_80_HTTP_Mimicry` in the binary. 

You can see available strategy names for the current implant by running `strat list` in the implant terminal:

```
--- SESSION ESTABLISHED ---
019f101d > strat list
--- Ingress (GET) ---
  > raw_10_0_0_30_9021_new_ftp_dev_422_9021
--- Egress (POST) ---
  > raw_10_0_0_30_9021_new_ftp_dev_422_9021
```

> Dev note - "Strategies" sounded cool when designing the switching/profile split logic, so I stuck with that naming. Feel free to call them "Profiles/Network Profiles/Mimicry Profiles, etc" as well. i.e. "I'm moving the implant to the FTP profile from the HTTP profile". 

---

## Raw Listener

The raw listener is the only "real" listener type in LongHaul. It sends and receives arbitrary bytes over TCP or UDP. The network profile's `[raw.*]` section defines the **complete wire format** — the listener adds no framing beyond what the profile specifies. Not a byte more, not a byte less.

What protocol your traffic looks like is entirely your decision. Default profiles ship in `client/user/profiles/`:

| Profile | Looks like |
|---|---|
| `raw_http_profile.toml` | HTTP/1.1 (default starting point) |
| `raw_ntp_profile.toml` | NTPv4 over UDP |
| `raw_ftp_profile.toml` | FTP RETR/STOR |
| `raw_dns_profile.toml` | DNS EDNS0 over UDP |
| `raw_snmp_profile.toml` | SNMPv1/v2c |
| `raw_debug_profile.toml` | Bare msgpack (no transforms, intended for debugging) |

Again, see [Mimicry](../06%20Network%20Profiles/Overview.md) for full documentation.

---

## SMB Pivot Listener (`pivot_smb`)

The `pivot_smb` type is a placeholder only — no listener/network process is started. It exists to represent implants in the graph that communicate via SMB named pipes through a parent implant, rather than reaching the server directly.

When you create a `pivot_smb` listener, the server registers it in Neo4j and makes it available as a build target so you can generate an implant that is configured to communicate over the SMB chain. The parent implant (with a `raw` listener) acts as the egress node.

---