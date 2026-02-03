# LongHaulC2: Persistent Access Management


**Project Goal:** To replace existing C2 frameworks for long-haul, Red Team/Offensive management scenarios. This tool serves as a "guardian" or "maintain access" solution—the failsafe when primary access methods are detected or neutralized.

While it is not designed to surpass Cobalt Strike or similar C2 tooling as a day-to-day operations tool, LongHaulC2 aims to outperform all of them as a low-overhead management and persistence solution.

## Objectives

* **Malleable C2 Interoperability:** Leverage existing CS Malleable C2 capabilities and scripts.
* **Robust Management:** Provide a comprehensive API and a user-friendly frontend for operator management.

---

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
* **Pivoting:**  Strategies for routing traffic (e.g., via a "final" IP) are under consideration but not yet finalized.

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

---

## Malleable C2 Support

LongHaul currently implements the network communication layer of Malleable C2 profiles. It focuses on traffic shaping and indicators (http-get, http-post, etc.), while omitting Cobalt Strike-specific payload and artifact configurations.

**Documentation Reference:** [Cobalt Strike Malleable Profile Docs](https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_profile-language.htm#_Toc65482837)

### Custom Extensions (Planned)

LongHaul plans to introduce custom blocks for non-traditional listeners:

    * `ntp-get`
    * `ntp-post`
    * `ntp-config`

### Known UNsupported components:
 - beacon specific config settings (ex, ...) - focus is on network portions of malc2
 - Multiple profiles in URI strings:
    - `set uri "/include/template/isx.php /include/template/abc.php";`


### Supported Blocks

#### http-get

Configuration for downloading tasks from the server.

**http-get.server**

* [x] Add on headers (e.g., `header "Content-Type" "image/gif";`)
* [x] Metadata Block (`metadata {}`)

**http-get.server.output**

* *Transform Operations:*
    * [x] `append "string"`
    * [x] `base64`
    * [x] `base64url`
    * [Untested] `mask`
    * [Untested] `netbios`
    * [Untested] `netbiosu`
    * [x] `prepend "string"`


* *Termination Options:*
    * [x] `header "header"` (Send data in HTTP header)
    * [x] `parameter "key"` (Send data as URI parameter)
    * [x] `print` (Send data in transaction body)
    * [x] `uri-append` (Append data to URI)



#### http-post

Configuration for submitting data/responses to the server.

**http-post.server**

    * [x] Add on headers (e.g., `header "Content-Type" "image/gif";`)
    * [x] Output Block (`output {}`)
    * [X] ID Block (`uuid {}`)

**http-post.server.output**

* *Transform Operations:*
    * [x] `append "string"`
    * [x] `base64`
    * [x] `base64url`
    * [Error] `mask` (Currently throws Key Error)
    * [x] `netbios`
    * [x] `netbiosu`
    * [x] `prepend "string"`


* *Termination Options:*
    * [x] `header "header"`
    * [x] `parameter "key"`
    * [x] `print`
    * [x] `uri-append`



#### http-config

Global configuration applied to every HTTP response served by the listener.
*Reference:* [http-server-config](https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/malleable-c2_http-server-config.htm#_Toc65482845)

* [x] `set headers` (e.g., `set headers "Date, Server, Content-Length, Keep-Alive, Connection, Content-Type"`)
* [x] `header "header"`
* [x] `block_useragents`
* [x] `allow_useragents`
* [Pending] `set trust_x_forwarded_for`

### Unsupported Features

* **http-stager:** Stagers are not supported and are out of scope for this project.

### Global Options

Status of global profile options:

* [ ] `data_jitter`
* [ ] `headers_remove`
* [ ] `jitter`
* [ ] `pipename`
* [ ] `sample_name`
* [ ] `sleep`
* [ ] `sleeptime`
* [ ] `smb_frame_header`
* [ ] `ssh_banner`
* [ ] `ssh_pipename`
* [ ] `steal_token_access_mask`
* [ ] `tasks_max_size`
* [ ] `tasks_proxy_max_size`
* [ ] `tasks_dns_proxy_max_size`
* [ ] `tcp_frame_header`
* [ ] `tcp_port`
* [ ] `useragent` (Global default)

**Removed/Out of Scope:**

* `host_stage`
* `pipename_stager`