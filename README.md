# LongHaulC2
C2 Aimed at Long Haul Management

# Goals:
Replace other  C2's as a long haul, Red Team/Offensive management C2. A "guardian"/"maintain access"/"Oh shit my shell got detected" solution.

I can't beat CS as a day-to-day red team operations tool. I can 
(probabbly) beat it as an overhead management tool.

## Things  I would like: 
 - Malleable C2 interopability (use CS's malleable C2 capabilities/scripts)
 - Good management capabilites (likely an API exposed from server, and a good management frontend)


# Implementation  Details:


#### Comms:
 - MessagaePack: Simple, easy to parse, JSON like, binary encoded structure. 

- Borrow from CS, Seperation between a beacon, and a checkin
    - Beacon: Do you have job for me (minimal proof this thing exists/is still up)
    - Checkin: Data going back and forth. Only happens if a job is available

#### Implant:
 - C++

 Primary platform: Windows first, but linux would be useful for long  term. Make the beacon source  as 
 platform agnostic as possible/have compile options (ex, win_func.cpp, lin_func.cpp)

 ###### Pivoting... 
    Various ways to do this. Maybe a "final" ip address where the messageneeds to go, etc. Not sure. Would be handy tohave, but not a thing that needs to be set in stone yet. 

#### Server:
 - Python
    - Flexibility with dynamic restarts, faster dev time, and flask-restx.
    Management:
        - API - JSON responses. REST.
    Listeners:
        - [http] Not sure. Something that allows for a new listener/schema on the fly
        - Mal c2


#### Data Management:
 - [container] Redis: For caching/message/pub sub DB work. 
    This would hold:
        - Queued Commands
        - Responses to Implants


 - [container] MySql: For long term data storage/stricter data types
        - [X]Implant metadata (ID [primary key], External IP, Internal IP, Listener, User, System Hostname, Notes, Process, PID, arch, last Checkin, Sleep Value)
        - Job Logs
            (Job ID [primary key], Job contents, User who Queued Job, Job Response)

#### Encryption:
 - Borrow CS's flow, Asymetric PKI, then symmetric once connected back. 

#### Managemnt:
 - A payload store on the server would be cool, for easy "re-access" to targets. Ex, a quick "spawn" command that you can choose whaat payload to spawn on said host.



# Malleable C2:
The current supported options in Malleable C2 profiles:

---
# Blocks:

# http-get:

### Applicable to:
- http-get.server

#### Misc:
* [X] Add on headers (`header "Content-Type" "image/gif";`)
* [X] Output Block (`output {}`)

### Applicable to:
- http-get.server.output

#### Transform operations:
* [X] `append "string"` ([Help Systems Tech Docs][1])
* [X] `base64` ([Help Systems Tech Docs][1])
* [X] `base64url` ([Help Systems Tech Docs][1])
* [X] `mask` ([Help Systems Tech Docs][1])
* [X] `netbios` ([Help Systems Tech Docs][1])
* [X] `netbiosu` ([Help Systems Tech Docs][1])
* [X] `prepend "string"` ([Help Systems Tech Docs][1])

#### Termination options:
* [ ] `header "header"` (send data in HTTP header) ([Help Systems Tech Docs][1])
* [ ] `parameter "key"` (send data as URI parameter) ([Help Systems Tech Docs][1])
* [X] `print` (send data in transaction body) ([Help Systems Tech Docs][1])
* [ ] `uri-append` (append data to URI) ([Help Systems Tech Docs][1])

---
# http-post:

### Applicable to:
- http-post.server

#### Misc:
* [ ] Add on headers (`header "Content-Type" "image/gif";`)
* [ ] Output Block (`output {}`)

### Applicable to:
- http-post.server.output

#### Transform operations:
* [ ] `append "string"` ([Help Systems Tech Docs][1])
* [ ] `base64` ([Help Systems Tech Docs][1])
* [ ] `base64url` ([Help Systems Tech Docs][1])
* [ ] `mask` ([Help Systems Tech Docs][1])
* [ ] `netbios` ([Help Systems Tech Docs][1])
* [ ] `netbiosu` ([Help Systems Tech Docs][1])
* [ ] `prepend "string"` ([Help Systems Tech Docs][1])

#### Termination options:
* [ ] `header "header"` (send data in HTTP header) ([Help Systems Tech Docs][1])
* [ ] `parameter "key"` (send data as URI parameter) ([Help Systems Tech Docs][1])
* [ ] `print` (send data in transaction body) ([Help Systems Tech Docs][1])
* [ ] `uri-append` (append data to URI) ([Help Systems Tech Docs][1])

---
# http-stager:
 - STAGERS NOT SUPPORTED. 

# Options:

* [ ] `data_jitter` ([Help Systems Tech Docs][1])
* [ ] `headers_remove` ([Help Systems Tech Docs][1])
* [ ] `host_stage` ([Help Systems Tech Docs][1])
* [ ] `jitter` ([Help Systems Tech Docs][1])
* [ ] `pipename` ([Help Systems Tech Docs][1])
* [ ] `pipename_stager` ([Help Systems Tech Docs][1])
* [ ] `sample_name` ([Help Systems Tech Docs][1])
* [ ] `sleep` ([Help Systems Tech Docs][1])
* [ ] `sleeptime` ([Help Systems Tech Docs][1])
* [ ] `smb_frame_header` ([Help Systems Tech Docs][1])
* [ ] `ssh_banner` ([Help Systems Tech Docs][1])
* [ ] `ssh_pipename` ([Help Systems Tech Docs][1])
* [ ] `steal_token_access_mask` ([Help Systems Tech Docs][1])
* [ ] `tasks_max_size` ([Help Systems Tech Docs][1])
* [ ] `tasks_proxy_max_size` ([Help Systems Tech Docs][1])
* [ ] `tasks_dns_proxy_max_size` ([Help Systems Tech Docs][1])
* [ ] `tcp_frame_header` ([Help Systems Tech Docs][1])
* [ ] `tcp_port` ([Help Systems Tech Docs][1])
* [ ] `useragent` (global default) ([Help Systems Tech Docs][1])
