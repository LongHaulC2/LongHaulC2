## Planning:
 
### Road to Beta

* [ ] API Auth (via JWT) & Login page
   * [ ] HTTPS api 
* [ ] Implant Encryption
* [X] Cleanup of old artifacts in `/tmp` (Verify if still applicable)
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

* [ ] Clean up api to pass schemathesis
   > big issue: data being NULL
   > Use werkzeug errors where needed
   > really fucking annoying. There's a few to fix still

* [ ] Seaarch seems to have gotten broken in the process. 

* [X] write some GUI tests too once API done
   > kind of smoke tests cuz it was being dumb

Neo4j Cleanup
* [X] UUID7 as primary key for every node
* [ ] Rough structure for keys each moodel would have. Ex: mac_address, ip_address, hostname, for NIC. These do not need to be 
   filled it at creation time, but should be available for each host. This gives the data a repeatable, predictable structure.

> Here
* [ ] 1/2 agent, 1/2 neo/pipeline: Remove the automatic host resolver call for discover neighbors, and make it an argument. By default, this should be
   ARP only, and the operator should specify if they want to resolve or not. something like "--resolve", somehow fit into the current command schema
   > Command schema has been updated to allow for positional & -- commands.

* [ ] --resolve command
   > [ ] Implant logic to handle it (arg: resolve=True)
   > [ ] Web/Task logic to handle it (arg: resolve=True)

* [X] Migration of listeners to neo4j

### System: CICD

* [X] CICD testing locally
* [X] CICD testing GH runners
>HERE
   > Note: Works, need to fix a few bugs its found with commands ()
   > Also, runners (i.e. the ubuntu server runner) needs to be rolled back, restarted to, and logged into each run
      >for some reason make redeploy doesn't nuke neo4j

   * [X] Fix commands to pass testing
   * [X] Continue to clean up
      > see obsidian, 
      - [X] Clean up implant file structure
      - [X] implant to /var/lib instead of in file dir
 
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
* [ ] Memory tracking system (store memory address/size on malloc for wiping/encryption)
* [X] Memory Store encryption (XOR via key name)

* [ ] String Encryption (e.g., skCrypter at compile time)
   > [ ] Re-Compile .LIB of bof, to use skCrypter as well. It has some strings which are very obvious
   * [ ] Convert rest of project to WinApi::FUNC (thinking, c2.cpp for sure)
      * [ ] c2.cpp
      * [ ] HTTP Calls (in IAT, very obvious)
      * [ ] Socket Calls (in IAT, very obvious)
      * [ ] Remove pragmas as well, these include all the funcs of what you incldued

> ========================================================
> here
Mental Dump

Was working on SMB. Core logic is setup, need to integrate smb as a valid strategy to select.
See comments about register pipe in c2.cpp.

Additionally, need to fix the following (priroity):

* [X] Export all objects built by container, correctly, into db. i.e., exe, dll etc.
   > sometimes you get the dll, sometimes you get the exe, client side. 
* [ ] Create a 32 bit version of the .lib for bofrunner, and add into cmake for 32 bit builds

* [ ] Implant, fix up smb logic, include by default, but add itin as an option
   > figure out how to do "are pipes registered - probably in settings, as the implant waits for conn then
   > More work, but INTEGRATE smb as a "normal listener" to add. This lays groundwork for other/multiple comms as well

SMB Chain Steps:
* [X] ChildStore in Implant (stores child connection info)
   > added childhandler.cpp/.h. This handles child conns.
* [ ] Server side link stuff
   * [ ] link command 
      > "link <host_or_ip>"
      > Neo4j:
         > creates implant node
         > creates a c2 channel node
         > Creates a link_to (or similar), with pipe names?

      > implant:
         > add link command -> command tree
         > Accesses childhandler singleton to add a new child
         > should be good after that

   * [ ] On implant checkin, find linked (if any) from neo4j
      Add all pending tasks for linked implants, to the task list.
   
   > finger crossed, this should work/go through

   > test setup:
   1 smb implant (use the dev_payload_source)
   1 egress implant

   run smb implant
   run egress implant
   run link on egress implant
   hope new implant shows up. 
      > hope registration works, it should

<!-- Hitting a reg bug, parent -> child works, but then the child
continues to try and register forever. Something is not quite lining up.

maybe we need to send a blank task first, then on connect/data back from it, then send registration  -->

> fixed - doubel array bug:
   //quick note - somewhere, this gets wrapped as an array, so no need to 
   //wrap it as one here. I dunno where that is happening, but somewhere down the line.

> Now, this. Successful link = do these things
Now, need to let the server know the task was successful, and on successful link,
 > update neo4j,
 > route all tasks for that uuid, to the agent they are linked in.
   (at get, just shove all tasks into an array if there's a child that has an inbound task)


OKAY big shift:
 - Implants shuold now generate their own UUID's. 
 This makes chaining a hell of a lot easier, and no need to fuck around with 
 passing a uuid to the agent. 

   > note, this will break current neo4j parent/child logic - fix could be:
      if in list of responses from implant, if there's a UUID that's not ours,
      hook it up to us in the graph

...we are tentatively good. I think it worked. Just a fwe changes to the listener, one to agent, and the
rest was mostly a drop in fix.

As a HUGE bonus, implants that die/come back, or get deleted, re-check in now. 
WAYYY more resilient, and this is how CS does it. 

update & re-try smb now
 > need to remove register task. 
 Also, need to liekly re-work a little bit, so it gets its init callback
 to the pipe it needs, i.e., wihtout a poke? not sure... 
 remove register first, then see what happens

==============================================================
> Left off:
 Switched it up, parent is now "server" and child sends data up
 It's kind of working, there's something off with metadta/data coming back to server
 It shows up as a blank implant, and I don't know why

prbably related to the type == register thing... go fix/remove that
		if (child_request.value("type", "") == "register") {

Steps for bug hunting:
1. dump every task/response (json .dump, there's an example smoewere) to verify whats up
2. go over all of it again in the morning

So, it appears the parent is getting the checkin from the child. Our bugs might be
server side. 
   Double check that "type, register", it seems redundant


okay - predicament

2 options for init checkin fro child:

1. create a list of checkin tasks (GET), which contain each's child's chekcin/metadata

Plan:

GET: 
   > move to an array of GET reqs (need a queue for this, request queue)
   > server iter's over those requests. 
   > server constructs ONE array of tasks, based on all provided UUID's of checkin tasks. 

   ex:
   [{implant_uuid:808080}, {implant_uuid:5145145}]

   response_list = []

   for implant in implant_uuids:
      if implant_not_in_db:
         register

      else:
         extract data/update metadata

      finally:
         if task_for_implant:
            response_list.append(task)

   msgpack it and -> to parent

POST:
   > Leave as is
   > array of POST requests. 
   > server iters over those requests


note - smb task returns successfully, but we might have a 
deadlock between the parent/child.

TLDR: child stuck waiting for data in task

Additionally, it's weird that the child is not showing on screen in gui

okay bug here^ get task not being added to queue, or not recieved by parent. 
> fixed, link task did not return OG, linked shows up now. 


OKAY - NOW, re-do link command in response_queue so we know who is linked to who

THEN, on task fetch, use that to get all tasks and feed to implant
Then we should be golden & working

link command, in data, should include:
 - UUID of child, ex: ["data"]["child_uuid"] = child_uuid

so the response has something to go off of/link the node *to* - done.

Next bug: 
 > child is not sending its metadata/GET each time, it waits on a connection to its pipe.
 We (parent) might have to give it an empty message for it to continue on.

okay - that was fixed by doing a full cycle, of sending a blank task to the child to reset it

NEXT BUG: data gets out, but server is fuckign up and not getting it???
Need to check. It's verfied to be printed out from parent, need to make sure:
1. parent is queueing it up
2. server gets it

<!-- its implant side
works fine when implant is NOT linked,
but when a link is introduced it fails -->

okay dumb server bug:

it all works, and commands are stored in db.
BUUUUUT, the task was sent to the PARENT, and exists as an entry with PARENT's
row/uuid, so of course the gui doesn't know about it. wtf.


See here: All tasks for the child () are stored under parent tasks. I don't know why. 
I remember this might have been an intentional choice, but it's still dumb. Need to figure out what's up.
```
Task History
{'implant_uuid': '019ccb99-dbf2-7431-a8a9-232c0be2220e', 'task_uuid': '019ccb9a-01e9-77fb-8526-d7b732ca0c4b', 'task_request': {'task': {'args': {'target': 'localhost', 'protocol': 'smb', 'inbox_pipe': 'inbox2', 'outbox_pipe': 'outbox2'}, 'task_name': 'link'}, 'task_uuid': '019ccb9a-01e9-77fb-8526-d7b732ca0c4b', 'implant_uuid': '019ccb99-dbf2-7431-a8a9-232c0be2220e'}, 'task_response': {'data': {'child_uuid': '019ccb9a-1766-772e-b8de-01cbd8b546a1'}, 'message': 'Successfully linked to child implant smb.', 'windows_error_code': 0}}

{'implant_uuid': '019ccb99-dbf2-7431-a8a9-232c0be2220e', 'task_uuid': '019ccb9a-4673-7ea8-932e-15b751a54978', 'task_request': {'task': {'args': {'directory': '.'}, 'task_name': 'ls'}, 'task_uuid': '019ccb9a-4673-7ea8-932e-15b751a54978', 'implant_uuid': '019ccb99-dbf2-7431-a8a9-232c0be2220e'}, 'task_response': {'data': 'http.exe\nImplant_v01_dll.dll\nsmb.exe\n', 'message': 'Success', 'windows_error_code': 0}}

# these 2 ls's specificlaly, why are they stored under the parent uuid
{'implant_uuid': '019ccb99-dbf2-7431-a8a9-232c0be2220e', 'task_uuid': '019ccb9a-b357-7f42-8301-07a801d20cd4', 'task_request': {'task': {'args': {'directory': '.'}, 'task_name': 'ls'}, 'task_uuid': '019ccb9a-b357-7f42-8301-07a801d20cd4', 'implant_uuid': '019ccb9a-1766-772e-b8de-01cbd8b546a1'}, 'task_response': {'result': {'data': 'http.exe\nImplant_v01_dll.dll\nsmb.exe\n', 'message': 'Success', 'windows_error_code': 0}, 'implant_uuid': '019ccb9a-1766-772e-b8de-01cbd8b546a1'}}

{'implant_uuid': '019ccb99-dbf2-7431-a8a9-232c0be2220e', 'task_uuid': '019ccb9b-10d0-7bb7-ab1e-5ce995f5850a', 'task_request': {'task': {'args': {'directory': '.'}, 'task_name': 'ls'}, 'task_uuid': '019ccb9b-10d0-7bb7-ab1e-5ce995f5850a', 'implant_uuid': '019ccb9a-1766-772e-b8de-01cbd8b546a1'}, 'task_response': {'result': {'data': 'http.exe\nImplant_v01_dll.dll\nsmb.exe\n', 'message': 'Success', 'windows_error_code': 0}, 'implant_uuid': '019ccb9a-1766-772e-b8de-01cbd8b546a1'}}
--------------------------------------------------

```

TLDR: Something is off, and tasks for child implants are getting their parents UUID's instead
of their own. 

It's likely in the implant itself...
go check how the implant child sends back data, and make sure a uuid is sent with:

ex:

```
[*] Poll Based Ingress
[*] SMB: Sending initial check-in GET request...
[*] Waiting on a task to enter my inbox
[
    {
        "implant_uuid": "019ccb9a-1766-772e-b8de-01cbd8b546a1",
        "task": {
            "args": {
                "directory": "."
            },
            "task_name": "ls"
        },
        "task_uuid": "019ccb9b-10d0-7bb7-ab1e-5ce995f5850a"
    }
]
Task List recieved
[*] Start of cycle
queued task for response:
{ # << here (check parent side too)
    "data": "http.exe\nImplant_v01_dll.dll\nsmb.exe\n",
    "message": "Success",
    "task_uuid": "019ccb9b-10d0-7bb7-ab1e-5ce995f5850a",
    "windows_error_code": 0
}
[*] Worker completed, queueing task response
[+] Instantly sent 189 bytes.
[*] Start of cycle
[*] Poll Based Ingress
[*] SMB: Sending initial check-in GET request...
[*] Waiting on a task to enter my inbox
```


from parent:

```
queued task for response:
{
    "implant_uuid": "019ccb9a-1766-772e-b8de-01cbd8b546a1",
    "result": {
        "data": "http.exe\nImplant_v01_dll.dll\nsmb.exe\n",
        "message": "Success",
        "windows_error_code": 0
    },
    "task_uuid": "019ccbc1-8ca2-7501-8f2a-b8fe4327d5d7"
}
```
the implant uuid here is fine.

I wonder if task_uuid is originally registered to parent for some reason?
see if lookups are done via task_uuid?
> HERE

Checklist:

- [X] GUI sending correct UUID
- [X] API getting right UUID
- [X] DB queuing right UUID

- [X] listener on GET

response:
- [ ] listener getting right UUID
- [ ] Saved to redis with right uuid

found it:
2026-03-08T07:06:15.721602Z [info     ] Received tasks from implant    [listener] implant_id=019ccc43-b66c-7168-a83c-4b2724b5c6ee ip=10.0.0.24 method=POST path=/N4215/adj/amzn.us.sr.aps tasks=[{'implant_uuid': '019ccc43-b66c-7168-a83c-4b2724b5c6ee', 'result': {'implant_uuid': '019ccc43-ddf3-737d-91b7-f4189403b084', 'result': {'data': 'http.exe\nImplant_v01_dll.dll\nsmb.exe\n', 'message': 'Success', 'windows_error_code': 0}}, 'task_uuid': '019ccc44-968d-7693-a719-514b16682261'}]

somehow, the child task is having the parent implant UUID appended to it

fixed it, it was the stpuid batching functino that added the parent UUID onto it. 

okay now the fun part.

cleanig up the fucking implant, and then moving to jinja

Left off:
 - [X] Chaining is working
 - [ ] Clean up any other code/comments. 
 - [ ] prep code for templating & update all of it (can keep hardcoded smb for now, just get it all updated)
   > after that works, can work on things like an smb block for malleable c2/pipe names, etc. 
- [ ] Listener cleanup
   > move functions out to dedicated helpers where necessary, keep the listeners 
   "transport only"

 - Note: pipes were moved to synchronos handling for simpliocity. way less to bug out on. 
 This means they will "sleep" as well, same for child pipes under them. latency may get long. review 
 it all

==============================================================

[X] Another bug:
 whetehr to send metadata or not is in the HTTP code, based on registered setting.
 Find a better spot for this, maybe in register? I'm not sure.

>>
[X] maybe update fetch task to have an optional, data/metadata field, to include for GET request.

> ========================================================


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