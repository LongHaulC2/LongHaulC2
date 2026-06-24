# Project Overview

**Project Goal:** To replace existing C2 frameworks for long-haul, Red Team/Offensive management scenarios. This tool serves as a "guardian" or "maintain access" solution—the failsafe when primary access methods are detected or neutralized.

While it is not designed to surpass Cobalt Strike or similar C2 tooling as a day-to-day operations tool, LongHaulC2 aims to outperform all of them as a low-overhead management and persistence solution.

## Objectives

* **Malleable C2 Interoperability:** Leverage existing CS Malleable C2 capabilities and scripts.
* **Robust Management:** Provide a comprehensive API and a user-friendly frontend for operator management.

## Design Choices & Key Features

What makes this suitable for long-haul operations? The entire architecture was built around the idea of surviving for months or years, not just days. This drove a few key design choices:

* **Granular Profile Binding:** Supports distinct Malleable C2 profiles per listener, enabling various traffic signatures across a single campaign infrastructure. A single server can handle multiple disparate profiles.
* **Dynamic Profile Switching:** Implants support multiple communication profiles. Operators can "hot-swap" strategies inline (e.g., changing protocols or Malleable C2 profiles) without spawning new artifacts, significantly reducing the detection surface. 
* **Automated Rotation:** Via the API, operators can script a rotation schedule (e.g., mimic Spotify traffic in the morning, switch to a Slack profile at noon, and switch to a Windows Update profile at night).

## Images

*(Insert relevant architecture or UI screenshots here)*

## Command Tree

Below are the commands and capabilities pulled directly from the Web Client help menu:

[Command Documentation](https://longhaulc2.github.io/02%20Implants/Commands)

```text
------
System
------
exit                 : Exit the implant. This will kill the implant process on the host, don't expect a response back.
sleep                : Sleep for a specified number of seconds on the host. Ex: `sleep 5`

-----------
File System
-----------
cd                   : Change the current working directory on the host. Ex: `cd C:\Users\`
ls                   : List the contents of a directory on the host. Ex: `ls C:\Users\`
file download        : Get a file from the host the implant is running on. Ex: `file download C:\Users\user\file.txt`
file upload          : Upload a file to the host. Ex: `file upload C:\Users\user\file.txt <base64_contents>` (or use the UI)

------------
Memory Store
------------
memstore list        : List all file names in the memstore. Ex: `memstore list`
memstore upload      : Upload a file to the implant memstore. Ex: `memstore upload <file_name> <base64_contents>`
memstore download    : Download a file from the implant memory store. Ex: `memstore download <file_name>`
memstore delete      : Delete a file from the implant's memory store. Ex: `memstore delete <file_name>`
memstore clear       : Clear *all* files in the implant's memory store. Ex: `memstore clear`

-----------
C2 Strategy
-----------
strat active         : List the active strategy for the implant.
strat list           : List the available strategies for the implant.
strat post           : Set the post strategy for the implant. Ex: `strat post my_post_strategy`
strat get            : Set the get strategy for the implant. Ex: `strat get my_get_strategy`

---------
Execution
---------
bof                  : Run a BOF. Ex: `bof <base64_bof_object> <args>` OR from memstore: `bof *memstore_bof_name <args>`

```

## Dev Table of Contents

1. [Introduction](https://www.google.com/search?q=%23longhaulc2-persistent-access-management)
2. [Objectives](https://www.google.com/search?q=%23objectives)
3. [Implementation Details](https://www.google.com/search?q=%23implementation-details)
4. [Malleable C2 Support](https://www.google.com/search?q=%23malleable-c2-support)

---

## Implementation Details

### Communication & Data Flow

* **Data Serialization:** Uses **MessagePack** for binary data encoding. It offers the structure of JSON but is significantly smaller and faster to parse.

**Task Structure:**

```json
{
    "task_uuid": "1234",
    "implant_uuid": "9999",
    "task": {
        "task_name": "cmd",
        "args": {
            "cli": "whoami"
        }
    }
}

```

**Task Response Structure:**

```json
{
    "task_uuid": "1234",
    "implant_uuid": "9999",
    "result": {
        "data_type": "text",
        "data": "somedomain\\bob"
    }
}

```

**Metadata Structure:**

```json
{
    "implant_uuid": "1234"
}

```

* **Two-Stage Comm Logic:** To minimize noise, the implant separates "status checks" from "data transfer":
* **Beacon (The Heartbeat):** A lightweight, minimal packet sent periodically to check for pending tasks.
* **Check-in (The Heavy Lift):** A full data connection that opens **only** when the server confirms tasks are pending. This prevents sending large, suspicious packets when the implant is idle.



### Implant Design

* **Language:** C++
* **Platform Support:** Windows-first, with Linux support planned for long-term versatility.

### Server Architecture

* **Language:** Python (chosen for dynamic restarts, rapid development, and library support).
* **Management Layer:** Built using REST and Flask-RestX to provide a comprehensive API with JSON responses.
* **HTTP Listeners:** Built with FastAPI. Traffic is defined by Malleable C2 profiles.
* **NTP Listeners:** Custom socket implementation for NTP tunneling (Planned).

### Data Management

The backend utilizes a containerized approach for caching and persistent storage.

* **Redis (Container or External):** Acts as a high-performance cache layer. It stores queued commands and caches responses destined for implants.
* **MySQL (Container or External):** Handles long-term storage and structured data. This includes long-term archival of executed task logs and other critical operational data.

### Encryption

* **Status:** Not currently implemented.
* **Plan:** Implement the standard asymmetric PKI model for initial key exchange, followed by symmetric encryption for session traffic.

### Management Features

* **Payload Store:** A server-side repository for payloads to facilitate rapid "re-access" or the spawning of new sessions on compromised hosts.

---

## Malleable C2 Support

LongHaul currently implements the network communication layer of Malleable C2 profiles. It focuses on traffic shaping and indicators (http-get, http-post, etc.), while omitting payload and artifact configurations specific to other frameworks.

<!-- See the full breakdown here: [MalleableC2 Support](https://www.google.com/search?q=link_file_here)
 -->
