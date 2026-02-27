## Planning:
 
### Road to Beta

* [ ] API Auth (via JWT) & Login page
   * [ ] HTTPS api 
* [ ] Implant Encryption
* [ ] Cleanup of old artifacts in `/tmp` (Verify if still applicable)
   * [ ] Consider a docker system prune on uninstall to prevent disk size ballooning
* [X] Listener Restarts
* [X] Implant Build Path
* [ ] Beacon Chaining
   - [ ] SMB read/write comms method
   - [ ] multi command retrieval
* [X] API Docs    

### GUI

* [ ] Per-Implant page (POC done, need to match with real data)
* [ ] Note: Explore more complex string matching later (beyond 3-character minimum)
* [ ] Login Page
* [X] Last-minute GUI cleanup (Go test)
* [X] Implant Search
* [X] Task Search (using dedicated endpoint instead of 'get all tasks')
* [X] Fix command descriptions in the GUI

### Graph db:
- left off workign in gui, it works fine for a display for now.
Keep building out logic based on responses, chains, etc etc. 

- [ ] GUI: Relationship names in GUI
- [ ] GUI: Context menu/Buttons for actions with selected items (i.e., open implant page, pop shell, etc.)
- [ ] Server/DB: Listeners and comms channels
 - > real data, like mac, gateway, and ip would help a lot for deving. Focus on that in metadata
   see metadata.cpp

> here
Take time to draw out what you want in like drawio/a perfect graph, and think about it. 
Use existing nodes, rework logic based on that.

May be worth adding a tracert command for mapping egress. 
That's a bit loud. Need to find balance between noise and accuracy.

> here:
Mostly done, may be a few stragglers I missed
<!-- reworking implant responses to be strucured.

no more key -> type/value, (ex, data: type, value) just "key"
Binary is auto stored as base64 in db with the BytesEncoder in mysql_connector,
so everything is safe to print -->


> register new node will create the node on listeenr reg, and that data will be dumped into data model, aka the graphdb, and 
be the kickoff point

once some of that is figured out, can continue to impleent tasks/other thigns to build out the nodes

> left off:
working on response_pipeline. todo's left:
 - [ ] excessive safety checks in response pipeline
   - [x] add a `if task result not 0, or task failed`, return immediatly for a fail fast and to not accidently update the graph on failure.
   - [ ] local loggers
 - [ ] review/modularity in neo4j functions if possible
    - [ ] doc each function & class & model
 - [ ] extract as MUCH metadata as you can manage from command responses
   - [X] files:
      - [x] file hash
      - [X] file size (kb)
      - [X] first X bytes (i.e. type tracking, for stuff like exe's)

 - [x] gui nodes
      -[ ] link buttons to actions
 - [ ] idea: split implant/host page 
       - running implant; breakdown of binary & source. Hosted files, last checkin, etc. 
       - host: Host breakdown, implants on it, other info, etc. 

### Deployment:
- [X] GUI: Script location. Save in /var/lib/longhaulc2, as /opt won't work
- [X] server: Set logs to /var/log/longhaulc2

- [X] Fix things not working, they just kinda hangup, and get a all connection attempts failed. I might have a hardcoded ip in there.
   > yep hardcoed ip. this will get fixed when the login page exists.

- [x] uptime daemon
> turned into a status notification system & endpoint

>here 
- [...] Make /status more functional (buttons, or not?)
- [x] Processes/Listeners
- [TODO] Core
- [ ] General cleanup of all things processes/threads, etc. 

   > Core: Stop, Start, Restart. 
Use the one/named thread pattern, so we don't have multiple of each thread going, which would be chaos.
```
def start_thread_once(name, target):
    for t in threading.enumerate():  # returns all alive threads
        if t.name == name and t.is_alive():
            print(f"Thread {name} is already running")
            return t
    t = threading.Thread(target=target, name=name)
    t.start()
    return t

Ex: 
t1 = start_thread_once("worker_thread", worker)
t2 = start_thread_once("worker_thread", worker)  # won't start a new one
```
Or, could enforce per function? 

- [ ] Docs for deployment, how to run, etc. Just need to install make and run make deploy.
> tldr: sudo make deploy to deploy, sudo make undeploy to undeploy, sudo make redeploy to redep

known broken on deploy:
 - [X] script editor
      > move scripts to /var/lib/longhaulc2

 - [X] compilation of bins
   > working on - was a docker permission

- [X] GUI css cleanup:
rule:use css as base, override as needed. not for sizing

> just finished gui, not sure what next.

- [] Chaining:

Plan/flow:

1. Parent beacon exists. Wants to chain another to it.
2. Parent spawns Child (for now, basic upload & run), with listener set to smb
3. Child setups up inbox and outbox smb pipes on run. Generates metadata (register), pushes to outbox
4. Parent reads outbox, includes in response queue.
5. Parent, if task, writes to inbox for that beacon.
6. parent POST

Parent:
```
checkin()

actions()

check_chained() -> for each chained in chain list, read outbox, then write inbox if new task

post()

```
Implant:
 - Get that global task mutex setup, and switch over to it.
      For each loop, pull out all tasks, yeet back to next hop/pass to the egress func. 
      This should allow chaining as deep as needed. 

note - current bind pipe allows for parent beacon to "link" and "unlink" at will, soa beacon can sit there,
unlinked, until it's linked  to.

Left off working on some gui (it's done) - and understanding the beacon better. It works,
and need to do templating *in* jinja before moving on with further SMB beacon imlementation

1. Update implant & server to do multi task, one task per implant per checkin
   > accept multiple tasks back (loop over msgpack)

   > implant:
      <!-- 1. pass list of tasks INTO post function. 
      2.  let that create the array of objects (custom helper instead of craet task response?)
      3. send that as outbound.  -->

   Task response:
      DONE.

   Task request: 
      > 1. get list working, on implant, and server first, with one task.
      > add a lookup for implants chained to this parent, via neo4j. Return all tasks, in a list for them

2.  put into template

3.  Get that working, THEN do smb

HEY - add delete listener in gui so it actually deletes it from the db

### Server: Listeners & Core

* [ ] Fix active flag in the database (Idea: Start listener on startup if marked active)
* [ ] Fix/Move tasks/watchdogs to a service folder & monitor health (stemming from task watchdog crash)
* [ ] Convert all logging to `structlog` (with binds, etc. - large task)
* [X] Auto-restarting listeners and quick restart endpoint
* [X] Add `check_type` on modules and server code
* [X] API documentation

### CICD/Testing:

> Here
* [ ] Clean up api to pass schemathesis
   > big issue: data being NULL
   > Use werkzeug errors where needed
* [ ] write some GUI tests too once API done


### Implant: Command Tree & Capabilities

~* [ ] `setting`: Generic setting changer command (`setting name new_value`, `setting list`)~
* [ ] `run`: Execute via `CreateProcess` (discourage use, prefer BOF, but include)
* [X] Deref operator [In Progress]: Format special characters via `format_command` function
* [ ] Move assistance functions to a better location? (Deref)
* [ ] Add Deref support to other binary commands   
   * [X] BOF
   * [X] file upload
* [ ] Metadata gathering [In Progress]: Internal IP, architecture, docs
* [X] `strat active` / `strat get/post` validation
* [X] File operations: `upload` and `download` (bytes format)
* [X] Memstore operations: `upload`, `download`, `list`, `delete`, `clear`
* [X] BOF implementation and documentation

#### Multi Command Retrieval:

Architecture: 
Server knows what implants are chaining for other implants. When implant parent checks in, next task for implant parent, and all implant children, are returned. (in a list... tasks have ID of implant they are for)
Implant then delegates tasks out via SMB (writes to pipe of child implant), as it will also hold a map of what task goes to what pipe on what host. 
   > Yes, leaves the burden on the server to provide next tasks

imlpementatino notes, SMB module will need to be in EVERY implant for chaining purposes. 


Note: The best way to track this is with a graphdb. Neo4j would come into play here. 

Can track things such as:
 - Chained' connections
   > chain task, result is success/failure, this value is used to set neo4j chain
 - Networks/if implants can talk to eachother
   > contact task? i.e., see if we can even contact other host. 
 - path finding
 - perms for who can talk to what, etc. 
 - what protocols can get where, etc. 

This would enable advanced analytics, and really drive home the "longhaul" part with a long term op of the 5 w's


Architecture:

task goes to client (i.e., chain)

client sends response. 

server has a trigger here, to check out that response. 
   > if chain command, and chain successful, update neo4j...
   > if other command...

So, plan (and draw out?)

Update `_task_batch_job()` to integrate the neo4j functionality.
   > also, clean this up a lot, make it somewhat readable/useable. It needs to be as fast/clear/explicit as it can be.

Put a placeholder func that just prints "neo4j" or something, but basically pass in each task to it, and it (or a class it calls)
will decide how to update neo4j properly with said data passed to it. 

*after* this, start figuring out the specifics of the meo4j db, and other various components. Just need an entry point first for a proper update. 

> Note, when exposing neo4j endpoints, give them a /graph or like /neo4j endpoint? maybe /analytics


### Implant: Comms & Hardening

* [ ] NTP Beacon implementation (Server, Client, MC2, Build process)
* [ ] Response queue (vector of tasks to run in background and queue return data)
   - This is a prereq to chaining
* [ ] Switchable callback domains (Random fallback hosts, auto-fill default, editable via settings)
* [ ] String Encryption (e.g., skCrypter at compile time)
* [ ] Memory tracking system (store memory address/size on malloc for wiping/encryption)
* [X] Memory Store encryption (XOR via key name)

### Server: Malleable C2

* [ ] Add a global user agent option to the render process
* [ ] Set up global options handling
* [ ] Add error handling for invalid options or bad configurations?
* [X] Test MC2 profiles to find breaking points
* [ ] Fix Mask (Needs a key not specified in the profile, decide whether to store the key or omit the mask. Could just use implant ID as KEY)
* [X] Create logging for errors
* [X] Draw.io data path mapping (bytes, headers, POST/GET)
* [X] `http-config` blocks



 # Stamping in/templating:
    Goal: Only touch comms functions, make everything as generic as possible to "just work"/follow a schema. AKA, if you have an http implant vs ntp, the only thing that changes
        are the protocol calls (ex, for ntp, call get() -> ntp_get(), for http, call get() -> http_get())


    Step 1: Python logic for which options, files needed etc.
    2. Format code blocks with data  (callback, transforms, etc)
    3. Paste into build files


   Left off: 
   - [ ] xor (still not sure about how the key works/where to get it from. Maybe generate on client side, OR pass in from server, in metadata/

Just remember, block == sender (ex, client, means sent from client). Transformations are top down
from the sender. 


# Tests output (2/2/2026)

========================================
      FINAL EXECUTION REPORT
========================================
amazon.profile                 | SUCCESS
apt1_virtually.profile         | SUCESSS
apt1_virtuallythere.profile    | SUCCESS
asprox.profile                 | SUCCESS
backoff.profile                | SUCCESS
bingsearch_getonly.profile     | SUCCESS
bing_search.profile            | SUCCESS
cnnvideo_getonly.profile       | SUCCESS
comfoo.profile                 | SUCCESS
etumbot copy.profile           | SUCCESS
etumbot.profile                | SUCCESS
fiesta.profile                 | SUCCESS
fiesta2.profile                | SUCCESS
gmail.profile                  | SUCCESS
googledrive_getonly.profile    | SUCCESS
havex.profile                  | SUCCESS
magnitude.profile              | SUCCESS
meterpreter.profile            | SUCCESS
microsoftupdate_getonly.profile | FAILURE: Checkin: URI did not match any configured endpoints... look closer. prepend might be doing something weird. CHECK WININET, this prepends a host header, and that might be getting messed with. Guess is that wininet protects the
host header to prevent weird http stuff I guess. Maybe just note this in noteable exceptions
msnbcvideo_getonly.profile     | SUCCESS
ocsp copy.profile              | SUCCESS
ocsp.profile                   | SUCCESS
onedrive_getonly copy.profile  | SUCCESS
onedrive_getonly.profile       | SUCCESS
pandora.profile                | SUCCESS
pitty_tiger.profile            | SUCCESS
reference.profile              | Incomplete (Unknown Error)
rtmp.profile                   | SUCCESS
safebrowsing.profile           | SUCCESS
string_of_paerls.profile       | SUCCESS
taidoor.profile                | SUCCESS
webbug.profile                 | SUCCESS
webbug_getonly.profile         | SUCCESS
webbug_getonly_v0.0.0.profile  | SUCCESS
wikipedia_getonly.profile      | SUCCESS
zeus.profile                   | SUCCESS
========================================



# Task Formatting (for reference):

Note: Task_uuid and implant_uuid are included for task verification (right task to right agent),
and for potential pivoting (to know which tasks go to which agents)

## Task  Structure
- `{task_uuid: <some_uuid>, implant_uuid: <intended_target>, "task":{"task_name":"somename" "args":{"arg1":"value1"}}}`

Ex: `{task_uuid: 1234, implant_uuid: 9999, "task":{"task_name":"cmd" "args":{"cli":"whoami"}}}`

List of tasks:
- `[{task_uuid: 1234, implant_uuid: 9999, "task":{"task_name":"cmd" "args":{"cli":"whoami"}}}, {task_uuid: 1234, implant_uuid: 9999, "task":{"task_name":"cmd" "args":{"cli":"whoami"}}}]`

## Task Response Structure:
- `{"task_uuid":"", "implant_uuid": 9999, "result":{data:{"type":"text", "value":"somedata"}, other_value:{"type":"text", "value":"abcd"}}}`

Ex: `{"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}`

List of task responses:
- `[{"task_uuid":"", "implant_uuid": 9999, "result":{command_output:{"type":"text", "value":"somedata"}, other_value:{"type":"text", "value":"abcd"}}},{"task_uuid":"", "implant_uuid": 9999, "result":{command_output:{"type":"text", "value":"somedata"}, other_value:{"type":"text", "value":"abcd"}}}]`

## Metadata Structure:
- `{"implant_uuid":"uuid", ...}`

Ex: `{"implant_uuid":"1234"}`


## Client:

 - [ ] Styling: Clean up spacing/layout in terminal of operations
      - [x] tighter, better fitting, and [x] auto focus
      - [ ] Crappy themes

 - [ ] Terminal
      - [X] Task types & output formatting
      - [X] Task sending to server
      - [ ] Task retrieval from server to display 
            Use UUID for timestamp sorting or something... might be a challenge. To prevent duplicate fetch, maybe do all events since last event. (time based)

      - [ ] Cleanup & document methods/structures. 
      - [X] Enter key bind to send

 - [ ] Searching:
      Add endpoints to server api for searching:
         # [X] POST /api/v1/search/implants
         # [ ] POST /api/v1/search/implants/history
            # Need to figure this out/do  more research. Fields are JSON, which makes searching harder
      These should be cached and have a refresh of 1-5 seconds. 

   Finish the above before  continuing

 - [ ] Perf:
    - [ ] User specified refresh on operations table (Ex, between 1-60 seconds). Client gets a little slow when there's thousands of agents being updated  every second. Use some dataelement tospecify this. Should be fairly easy to implement, hopefully?



Performance Considerations:
---------------------------
    - User specified refresh on operations table (Ex, between 1-60 seconds). Client gets a little slow when there's thousands of agents being updated  every second
    - Use pagination EVERYWHERE when possible. 
    - DO NOT use ui.notify for lots of events, it slows the whole thing down.