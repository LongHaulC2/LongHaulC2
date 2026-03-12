# LongHaulC2: 20-Day Beta Sprint Plan
**Timeline:** March 10, 2026 – March 29, 2026
**Pace:** 4 Hours / Day

---
Find a place for:
- [ ] cleanup makefile
   > individual scripts in setup would be nice. 


> NOTE! 1 branch per day. Keeps us on track

## Phase 1: Security & API Stabilization 
*Goal: Lock down the API and fix tests before adding more features.*

### [X] Day 1: March 10 - Authentication & API Hardening
- [ ] Implement API Auth via JWT.
   - [X] DB table of users
   - JWT: https://blog.appsignal.com/2025/04/30/using-jwts-in-python-flask-rest-framework.html
   - [X] Auth endpoints
   - [X] Add jwt_required to every endpoint 
- [X] Set up the Login Page in the GUI (hook it to the JWT endpoint).

- [X] Enforce HTTPS on the API. 
   - [X] cert generation via makefile 
   - [X] Gunicorn
- [X] add a default user to db... 
  

### [ ] Day 2: March 11 - Schemathesis & Test Driven Fixes
<!-- - [ ] Fix the API to pass Schemathesis (squash NULL data issues).
   > ONLY expected response codes here, nothing crazy. BASIC validation.  -->
- [X] Implement proper Werkzeug error handling across API endpoints.
   > global level error handler
- [X] Fix the broken search endpoints (`POST /api/v1/search/implants` and history).
   > was client side
   > touching up searching in gui

### Day 3: March 12 - Core Service & Thread Management
- [ ] Implement the singleton pattern for threads (`start_thread_once`) to prevent worker chaos.
- [ ] Fix the active flag in the database (ensure listeners auto-start on boot if marked active).
- [ ] Move tasks/watchdogs to a dedicated service folder and wrap them in health monitors.

---

## Phase 2: The Graph & The Pipeline 
*Goal: Fix how data flows from the implant, through the server, and into Neo4j.*

### Day 4: March 13 - Neo4j Schema & Structuring
- [ ] Establish the strict structure for keys (e.g., `mac_address`, `ip_address`, `hostname`) for all node types so data is predictable.
- [ ] Review and modularize Neo4j functions.
- [ ] Add docstrings to every model and class.

### Day 5: March 14 - Response Pipeline Safety
- [ ] Add aggressive safety checks to `response_pipeline`.
- [ ] Implement the fail-fast mechanism (if task result != 0, return immediately to prevent poisoning the graph).
- [ ] Add local loggers to the pipeline using `structlog`.

### Day 6: March 15 - Deep Metadata Extraction
- [ ] Ensure the pipeline extracts maximum metadata from responses.
- [ ] Finalize file metadata extraction (file hash, size in KB, first X bytes for typing).
- [ ] Fix the issue where task history for a chained child gets assigned the parent's UUID.

---

## Phase 3: Implant Hardening & Evasion
*Goal: Making the C++ payload stealthy, stable, and decoupled from standard stdout.*

### Day 7: March 16 - Evasion & API Hiding
- [ ] Implement String Encryption (skCrypter) at compile time.
- [ ] Convert the rest of the project to `WinApi::FUNC` (target `c2.cpp`, HTTP calls, and Socket calls in the IAT).
- [ ] Strip out `#pragma` includes that map directly to used functions.

### Day 8: March 17 - Logging & Stability
- [ ] Move all standard `stdout` to a `DEBUG_LOG` macro that compiles out completely in release builds.
- [ ] Fix the fatal crash when the implant starts but there is no listener to connect to (implement a robust backoff/retry loop).

### Day 9: March 18 - Memory & Payload Ops
- [ ] Implement the Memstore output-to-pipe feature (take CLI output, write to named pipe, store in memstore).
- [ ] Finalize the `run` command (`CreateProcess` wrapper).

---

## Phase 4: Chaining, SMB & Templating 
*Goal: The most complex backend work. Getting parent/child payloads to communicate flawlessly.*

### Day 10: March 19 - SMB Integration
- [ ] Clean up SMB logic and integrate it as a standard, selectable listener type.
- [ ] Fix the deadlock issue where a child is stuck waiting for data in a task (ensure empty messages flow to keep the pipe alive).

### Day 11: March 20 - Task Routing for Chains
- [ ] Ensure the server correctly identifies linked implants in Neo4j.
- [ ] Update the task fetcher: when a parent checks in, bundle all tasks for the parent *and* its linked children into the MSGPack array.

### Day 12: March 21 - Malleable C2 & Profiles
- [ ] Fix the Mask issue (decide to omit or use the implant ID as the key).
- [ ] Add a global User-Agent option to the rendering process and set up global options handling.

### Day 13: March 22 - The Templating Engine (Part 1)
- [ ] Build the Python logic to select options and files dynamically.
- [ ] Format code blocks with injected data (callbacks, transforms).

### Day 14: March 23 - The Templating Engine (Part 2)
- [ ] Finish pasting templated blocks into build files.
- [ ] Template the SMB code (allowing for malleable pipe names).

---

## Phase 5: GUI Polish & Performance
*Goal: Making the operator experience snappy and intuitive.*

### Day 15: March 24 - Terminal & Task Display
- [ ] Finish task retrieval from the server to display in the UI terminal.
- [ ] Implement timestamp/UUID sorting to prevent duplicate fetches.
- [ ] Clean up terminal spacing, auto-focus, and add the "Enter to send" keybind.

### Day 16: March 25 - GUI Context & Workflows
- [ ] Add relationship names to the GUI visualizer.
- [ ] Create context menus/buttons for selected items in the graph (e.g., right-click to "Open Implant Page" or "Pop Shell").
- [ ] Split the Implant and Host pages logically (Implant = binary info; Host = OS info, all implants on it).

### Day 17: March 26 - Performance Throttling
- [ ] Implement pagination *everywhere* a list is returned.
- [ ] Add user-specified refresh intervals (1-60s) on the operations table to stop the client from choking on updates.
- [ ] Rip out spammy `ui.notify` calls for high-frequency events.

### Day 18: March 27 - New Operations Commands
- [ ] Implement the `--resolve` command (ARP only by default, toggle DNS resolution via the arg).
- [ ] Finish the deref operator assistance functions and hook them up to BOF and file uploads.

---

## Phase 6: Deployment & Launch Prep
*Goal: If it isn't documented, it doesn't exist. Final run-throughs.*

### Day 19: March 28 - Deployment Architecture
- [ ] Clean up old MC2 artifacts (files, dependencies).
- [ ] Review `/tmp` artifact cleanup and add a `docker system prune` hook to the uninstall script.
- [ ] Finalize the `structlog` implementation across the entire server.

### Day 20: March 29 - Documentation & Final Smoke Test
- [ ] Write the deployment documentation (explaining `make deploy`, `make undeploy`).
- [ ] Document the API.
- [ ] Run a full end-to-end smoke test: generate a payload, link an SMB child, pass a command, verify the Neo4j graph updates accurately.

---
**April 1st:** Beta Launch.