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
  - *Note:* This allows for complex emulation scenarios. Theoretically, you could script a "workday" rotation: mimic Spotify traffic in the morning, switch to a Slack profile at noon, and switch to a Windows Update profile at night.

## Table of Contents

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

### Communication

* **MessagePack:** Utilizes MessagePack for a simple, binary-encoded, JSON-like structure that is easy to parse.
* **Beacon vs. Checkin Logic:** Adopts the Cobalt Strike model of separating status checks from data transmission.
* **Beacon:** Minimal proof of life; checks for available tasks.
* **Checkin:** Bi-directional data transfer; occurs only if a task is available.

### Implant Design

* **Language:** C++
* **Platform Support:** Windows-first, with Linux support planned for long-term versatility.
* **Source Structure:** Designed for platform agnosticism with conditional compilation options (e.g., `win_func.cpp`, `lin_func.cpp`).

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

* **[Container] Redis:** Acts as a high-performance cache layer.

  * Stores queued commands.
  * Caches responses destined for implants.
* **[Container] MySQL:** Handles long-term storage and structured data.
* **Active Listener List**
* **Task Logs:** Long-term archival of executed tasks.
* **Implant Metadata:**

  * ID (Primary Key)
  * External IP / Internal IP
  * Listener ID
  * User / System Hostname
  * Process / PID / Arch
  * Last Checkin / Sleep Value

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
