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
   - [X] Search w/ Lucene: Graph (ALL)
   - [X] Search (basic text): listener
   - [X] Search (basic text): Payload

- [x] gui terminal index fix

### Day 3: March 12 - Core Service & Thread Management

this is gonna be fun. TLDR, make api thread safe so we can crank the gunicorn workers

- [ ] Implement the singleton pattern for threads (`start_thread_once`) to prevent worker chaos.
- [X] Fix the active flag in the database (ensure listeners auto-start on boot if marked active).
   > should be fixed & good to go
- [ ] Move tasks/watchdogs to a dedicated service folder and wrap them in health monitors.
   > kinda done - double check

---

## Phase 2: The Graph & The Pipeline 
*Goal: Fix how data flows from the implant, through the server, and into Neo4j.*

### Day 4: March 13 - Neo4j Schema & Structuring
- [X] Establish the strict structure for keys (e.g., `mac_address`, `ip_address`, `hostname`) for all node types so data is predictable.
   > moved to structured nodes
   > [X] all non-critical data is in metadata, client parsing will need to be updated for this
- [X] Review and modularize Neo4j functions.
- [X] Add docstrings to every model and class.

### Day 5: March 14 - Response Pipeline Safety
- [X] split response pipeline into proper modules/files
- [X] host: ip/mac double check neo4j models, hosts show up without them. Likely a sideeffect of structured node switch
      >[X] update discover neighbors to link hosts to main network, it's arp, so it's safe to assume they are on that subnet [omg this was a rabbithole]
- [X] Add aggressive safety checks to `response_pipeline`.
- [X] Implement the fail-fast mechanism (if task result != 0, return immediately to prevent poisoning the graph).
- [X] Add local loggers to the pipeline using `structlog`.

### Day 6: March 15 - Deep Metadata Extraction
- [X] Ensure the pipeline extracts maximum metadata from responses.
- [X] Finalize file metadata extraction (file hash, size in KB, first X bytes for typing).
- [X] Fix the issue where task history for a chained child gets assigned the parent's UUID.

---

## Phase 3: Implant Hardening & Evasion
*Goal: Making the C++ payload stealthy, stable, and decoupled from standard stdout.*

### Day 7: March 16 - Evasion & API Hiding
- [X] Convert the rest of the project to `WinApi::FUNC` (target `c2.cpp`, HTTP calls, and Socket calls in the IAT).
- [ ] Implement String Encryption (skCrypter) at compile time.
 > https://github.com/skadro-official/skCrypter
- [X] Strip out `#pragma` includes that map directly to used functions.
- [X] properly get a strip call going for when the bin is not in debug mode (goes from 4mb -> 1.5mb)

### Day 8: March 17 - Logging & Stability
- [X] Move all standard `stdout` to a `DEBUG_LOG` macro that compiles out completely in release builds.
- [X] Fix the fatal crash when the implant starts but there is no listener to connect to (implement a robust backoff/retry loop).

### Day 9: March 18 - Memory & Payload Ops
- [ ] Implement the Memstore output-to-pipe feature (take CLI output, write to named pipe, store in memstore).
- [ ] Finalize the `run` command (`CreateProcess` wrapper).

---

## Phase 4: Chaining, SMB & Templating 
*Goal: The most complex backend work. Getting parent/child payloads to communicate flawlessly.*

### Day 10: March 19 - SMB Integration
- [ ] Clean up SMB logic and integrate it as a standard, selectable listener type.
   > move all variable that can be templated into transport.h (i.e., pipe names)
      > [X] need to edit c2.cpp. The strat for register pipe. needs to pass in pipe name. Allows for multiple pipe strats
   > [X] create templates for the needeed SMB items
   > [X] Create server side options/logic for templated items
   > [X] Add "smb" as a valid listener.  < here
   - [] Another bug:
         2026-03-14T21:18:44.288037Z [error    ] DB Write failed                [response_pipeline] error=KeyError('task_uuid') implant_uuid=019cee34-843f-7246-9e9e-b24826aa35cb

         looks like duplicated/not included task UUID? not sure what's up here. This is post link with the above way

      normal "start as smb and link to" works fine.
      Start as other protocol then switch to SMB has that task uuid bug

- [X] move strat command to `strat set <get|post|both> name`
   > add proper args, etc
- [X] smb compile bug, something name of namespace not right with smb_piv
- [X] make sure those await_client_connection calls aren't hardcoded (the inbox outbox arg...)
- [ ] add proper args/desc to smb link options on gui 
- [X] move link to link<method> for args, so it's not as brittle in the future
   > [X] rename in command tree to `link smb`, not just link
   
   > [X] do Unlink 
      > [x] getting "could not find child". Check that it's actually added in link.
         > stupid logic bug. Fixed.
         - [X] BUG - on unlink, if you tr to relink - you get a "231 pipes busy"
         Need to make sure pipes are properly closed/reset.

      > [ ] verify parser side
      > [ ] very client side

- [X] SMB broke somewhere. GET's are recieved, but POST's are seemignly not.
   > Child is stuck on readfile, so I wonder if it's not getting next task data.
   > Go check all logic, etc. and watch logs. Have 1 smb from the getgo, and one dedicated http
   > Fixed SMB bug. TLDR, response pipeline was not picking up the link, and registering the child under the parent, so no tasks got to it. 

~~- [ ] SMB profile, size of chunk read setting (just under SMB, as a global SMB setting)~~
   > not for beta - later

- [ ] Link list child functions that lists all children
 > option to expand JSON in the gui? for better & more visible reults
### Day 11: March 20 - Implant Docs Overhaul

- [ ] Doxygen testing
   - [ ] Add a BRIEF to each function in the template codebase, for faster docs with doxygen

- [X] Super docs builder? i.e., run like "make doc build" or something, which 
puts all the docs together into a docs folder. 
   Docs in mind:
      - API docs (from swagger)
         > subsection of the docusaurus
      - Doxygen Docs (from doxygen/implant)
         > seperate, like /implant-docs or something
      - main docs
   > tentatively here. it's fine, whatever. in docs repo
### Day 12: March 21 - Malleable C2 & Profiles
- [X] Add a global User-Agent option to the rendering process and set up global options handling.

### Day 13: March 22 - The Templating Engine (Part 1)
~~- [ ] Build the Python logic to select options and files dynamically.~~
~~- [ ] Format code blocks with injected data (callbacks, transforms).~~
- [ ] store source before compile, so debugging is easier
   > will take a few min to reworks to save first, then compile. 

### Day 14: March 23 - GUI - Node Pages
It would be cool if I could get a unified template goign for this, but 
tbh, per page is probably still easier/simpler/faster in the short term

- [X] Implant Page (1 hour)
- [X] Listener Page (1 hour)
   > on double click, open page
- [ ] Payload Page (1 hour)
- [ ] Network Page (1 hour)
   > Relevant network info
- [ ] File/memstore Page (1 hour)
   > HEX contents of file (if stored somewhere)

- [ ] Context menu for all of these, i.e., in operations, context menu over implant

Misc:
First:
 - [ ] Return button - make it point at actual previous link.
   Idea, store previous_page in cookie/storage, then on return, go to that link. Probably the easiest
   https://nicegui.io/documentation/storage
      app.storeage.tab may be best. tldr, per tab, which makes sense for a back button

   idea in place, now implement where navigates exist
---


## Phase 5: Auth & Context
*Goal: Adding core authentication mechanisms for user switching, etc.*
 - Login via user/pass
 - Token stuff
 - Kerb stuff
 - (server) Cred Store


## Phase 6: GUI Polish & Performance
*Goal: Making the operator experience snappy and intuitive.*

### Day 15: March 24 - Terminal & Task Display
- [X] Finish task retrieval from the server to display in the UI terminal.
- [X] Implement timestamp/UUID sorting to prevent duplicate fetches.
- [X] Clean up terminal spacing, auto-focus, and add the "Enter to send" keybind.

### Day 16: March 25 - GUI Context & Workflows
- [X] Add relationship names to the GUI visualizer.
- [ ] Create context menus/buttons for selected items in the graph (e.g., right-click to "Open Implant Page" or "Pop Shell").
- [ ] Split the Implant and Host pages logically (Implant = binary info; Host = OS info, all implants on it).

### Day 17: March 26 - Performance Throttling
- [X] Implement pagination *everywhere* a list is returned.
- [X] Add user-specified refresh intervals (1-60s) on the operations table to stop the client from choking on updates.
- [ ] Rip out spammy `ui.notify` calls for high-frequency events.

### Day 18: March 27 - New Operations Commands
- [ ] Implement the `--resolve` command (ARP only by default, toggle DNS resolution via the arg).
- [ ] Finish the deref operator assistance functions and hook them up to BOF and file uploads.

---

## Phase 7: Deployment & Launch Prep
*Goal: If it isn't documented, it doesn't exist. Final run-throughs.*

### Day 19: March 28 - Deployment Architecture
- [ ] Clean up old MC2 artifacts (files, dependencies).
- [ ] Review `/tmp` artifact cleanup and add a `docker system prune` hook to the uninstall script.
- [ ] Finalize the `structlog` implementation across the entire server.

### Day 20: March 29 - Documentation & Final Smoke Test
- [ ] Write the deployment documentation (explaining `make deploy`, `make undeploy`).
- [ ] Document the API. (redoc - get stupid dark mode working)


---
**April 1st:** Beta Launch.