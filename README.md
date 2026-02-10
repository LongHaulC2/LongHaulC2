# LongHaulC2: Persistent Access Management

**Project Goal:** To replace existing C2 frameworks for long-haul, Red Team/Offensive management scenarios. This tool serves as a "guardian" or "maintain access" solution—the failsafe when primary access methods are detected or neutralized.

While it is not designed to surpass Cobalt Strike or similar C2 tooling as a day-to-day operations tool, LongHaulC2 aims to outperform all of them as a low-overhead management and persistence solution.

## Objectives

* **Malleable C2 Interoperability:** Leverage existing CS Malleable C2 capabilities and scripts.
* **Robust Management:** Provide a comprehensive API and a user-friendly frontend for operator management.

## Design Choices & Key Features

So, what actually makes this suitable for long-haul operations? The entire architecture was built around the idea of surviving for months, years, etc, not just days. This drove a few key design choices:

- **Granular Profile Binding:** Supports distinct Malleable C2 profiles per listener, enabling various traffic signatures across a single campaign infrastructure. No need for multiple servers, one will do it all.
- **Dynamic Profile Switching:** Implants support multiple communication profiles. Operators can "hot-swap" strategies inline (e.g., changing protocols, or MalleableC2 profiles) without spawning new artifacts, significantly reducing the detection surface.
  - *Note:* This allows for complex emulation scenarios. Via the API, you could script a "workday" rotation: mimic Spotify traffic in the morning, switch to a Slack profile at noon, and switch to a Windows Update profile at night.

## Images




## Dev Table of Contents

1. [Introduction](#longhaulc2-persistent-access-management)
2. [Objectives](#objectives)
3. [Implementation Details](#implementation-details)
   - [Communication](#communication)
   - [Implant Design](#implant-design)
   - [Server Architecture](#server-architecture)
   - [Data Management](#data-management)
   - [Encryption](#encryption)
   - [Management Features](#management-features)
4. [Malleable C2 Support](#malleable-c2-support)
   - [Supported Blocks](#supported-blocks)
     - [http-get](#http-get)
     - [http-post](#http-post)
     - [http-config](#http-config)
   - [Unsupported Features](#unsupported-features)
   - [Global Options](#global-options)

---

## Implementation Details

### Communication & Data Flow

* **Data Serialization:** Uses **MessagePack** for binary data encoding. It offers the structure of JSON but is significantly smaller and faster to parse. 

 - Task Structure:
    `{task_uuid: 1234, implant_uuid: 9999, "task":{"task_name":"cmd" "args":{"cli":"whoami"}}}`

 - Task Response Structure:
    `{"task_uuid":"", "implant_uuid": 9999, "result":{command_output:{"type":"text", "value":"somedata"}, other_value:{"type":"text", "value":"abcd"}}}`

 - Metadata strucutre:
    `{"implant_uuid":"1234", other....}`


* **Two-Stage Comm Logic:** To minimize noise, the implant separates "status checks" from "data transfer":
  * **Beacon (The Heartbeat):** A lightweight, minimal packet sent periodically just to ask, *"Is there work for me?"*
  * **Check-in (The Heavy Lift):** A full data connection that opens **only** when the server confirms tasks are pending. This prevents sending large, suspicious packets when the implant is idle

### Implant Design

* **Language:** C++
* **Platform Support:** Windows-first, with Linux support planned for long-term versatility.

### Server Architecture

* **Language:** Python (chosen for dynamic restarts, rapid development, and library support).
* **Management Layer:**

  * API with JSON responses.
  * Built using `REST` / `Flask-RestX`.
* **Listeners:**

  * **[http]** FastAPI: Traffic defined by Malleable C2 profiles.
  * **[NTP]** Custom Socket: Planned implementation for NTP tunneling (Not yet implemented).

### Data Management

The backend utilizes a containerized approach for caching and persistent storage.

* **[Container or external] Redis:** Acts as a high-performance cache layer.

  * Stores queued commands.
  * Caches responses destined for implants.
* **[Container or external] MySQL:** Handles long-term storage and structured data.
* **Task Logs:** Long-term archival of executed tasks.
* Various other imporant operational storage

### Encryption

* **Status:** Not Implemented.
* **Plan:** Implement the Cobalt Strike model: Asymmetric PKI for initial key exchange, followed by symmetric encryption for session traffic.

### Management Features

* **Payload Store:** A server-side repository for payloads to facilitate rapid "re-access" or spawning of new sessions on compromised hosts.
* ...

---

# Malleable C2 Support

LongHaul currently implements the network communication layer of Malleable C2 profiles. It focuses on traffic shaping and indicators (http-get, http-post, etc.), while omitting Cobalt Strike-specific payload and artifact configurations.

See (link file here) MalleableC2 Support
