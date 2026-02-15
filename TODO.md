## Planning:
 
# Road to beta:
 - [ ] API Auth
 - [ ] Implant Encryption
 - [ ] Listener Restarts
 - [ ] Implant Build Path

# GUI:

   - [X] Last minute GUI cleanup things (go test)
      - [X] Implant Search
      - [X] Task Search (use dedicated endpoint like implant search, rather than a get all tasks)

      See if possible to do more string matching that isn't like 3 characters min
         - it is but is a problem for later

   <!-- - [ ] Server should say warning if task is invalid format -->

     # this is not needed yet, but would be a nice to have
   - [ ] Per-Implant page
      - POC done, fill in/match with real data, etc. 


#  server
   # API cleanup:

   #### Logging:
      # Last, before switching to GUI:
      - [ ] Convert everything to structlogger (with binds, etc.) Big tasks
      - [X] Add `check_type` on modules/other server code where applicable

   # cleanup/refinement:
    Fix/Move of the tasks/watchdogs, to a service folder, and a way to monitor if they are alive or not. (and viewable via gui, api)
      > stems from a bug where the task_wastchdog would crash

## Mal c2:

 - [ ] Server

   See readme, tldr:
      left off  trying different profiles. Things to do:

      ### 1. **Test Various Malleable C2 Profiles**
         - [ ] Experiment with different configurations to see if I can break it
         - [ ] > Mask is busted, needs a key, and that doesnt seem to be specified in the 
               mc2 profile. Need a way to store that key, or just not include mask at the moment.
            * [Throws Key Error] `mask` 

      ### 2. **Global Options**
         - [ ] Set up global options handling for the system.

      ### 4. **Error Handling**
         ~~- [ ] Implement error handling for invalid profiles.~~
         - [ ] Add error handling for invalid options or bad configurations.
         - [X] Create logging for when errors occur.
         - [X] Graceful failure for unexpected scenarios (e.g., invalid data format, connection issues).

      ### 5. teseting & docs:
         - [ ] Test "untested" methods in readme to make sure they work. 

         - [X] Create a draw io of full path of data as it comes in (including if bytes, etc. When headers appended, etc. For post and get)
      ### Addtl HTTP blocks:
         - [X] http-config

 - [ ] Implant
   - not implementing implant specific options. Sticking to response/network shaping options



   

# Implant:
 - Reqs:
   - Windows:
      - [X] Statically compiled
      - [ ] DLL Based (windows)
      - [x] CMAKE based

   ## Plan:
      - [x] Test messagpack
      - [x] Test libcurl for HTTP
         - [x] maybe just use winhttp (start with winINet, for quicker dev, re-evaluate later)
            - https://learn.microsoft.com/en-us/cpp/mfc/wininet-basics?view=msvc-170

      - [x] Decide project structure (folder struct, etc)

   > Here - continue with capabilities dev
   # task queeus.
      Nope. TLDR: one command one output is easier to track/build on IMO/more explicit/predictable to users. 
      Maybe later. IN meantime, `bg` command, new thread, runs task in bacgkround if operator wants to.  
      <!-- inbox, and otubox.
      inboux has inbox tasks, outbox has outbox.
      Both are singlton clsses for easy access.
      
      inbox:
         > Enqueue: Takes task object retrieved by GET, iterates over each task, and enqueues to inbox. 


      Flow:
         server -> inbox
         inbox -> implant actions
         implant actions -> outbox
         outbox -> network -->

   # Command Tree:
      [ ] Revised output to data, windows_error_code, and message. 
         > data has command result data
         > windows_error_code is err code
         > message is either custom message, or the error code converted to a win error msg. 
         > This needs to be documented somehwere better. Maybe an `implant.md` guide for modifying it, etc. This style of
         return should be final

      - move strat storage to a dedicated system in .h? instead of hacky settings, but it kinda fits in settings. 
      `strat get/post`:
         - [X] validate switching strats. 
            -> [ ] Add safeguards, ex, user requesting get for post, vice versa.
            -> [ ] add a strat current that shows `current set` strats
      [X] `strat active`: Shows active strat

      note; command upload/download is based on operators perspective, they are *uploading* a file. 
      [X] `file upload`: Upload file to host disk
         > gui note, maybe an upload button, or take local file path?
         > Have file be in bytes, just easier all around. 
      [x] `file download`: Download file from host disk
         > server note, have an archive of files pulled from device? in a file store/db? this would support long term goals. 
         > maybe even a `file watch` command, that pulls new versions/checks every so often
         > [x] For now/simplicity, just retrieve file and download to operator. can do a storage later. 
   

      Memstore: hold data in memory
      Not meant to be super secure, just to evade mem scans:
      [x] `memstore upload`: Upload file to host memory store
      [x] `memstore download`: Get file from host memory store
      [x] `memstore list`: List file names of memory store
      [x] `memstore delete`: Nuke file from memory
      [x] `memstore clear`: Nuke all files from memory
      
      > here
      > Docs in gui, as commands are added. 

      [ ] add generic error handling/base64 err handling when a command input doesn't pass/fails

      [X] fix cmd descs in gui

      `shexecute`: Executes shellcode, inline? Ran into issues with this in previous projects. Maybe in a new thread

      `setting`: Generic setting chagner  
         > `setting setting_name setting_new_value`
         > start with int, and string. 
         > Then do map/vector.   
            > these would need to be `setting setting_name add/remove value`
         `setting list`

      Maybe...:
         `bof`: runs bofs... but that takes a lot of work to do. (and needs upload/download funcs first anyways. )

      - Addtl:
         - response qeueu. This allows tasks to run in the background, and hwen they complete, pop the data into the queue and it'll get sent back. 
         - A vector of tasks should do this fine. 

         - Switchable callback domains, like cs, has, where there's a list of callback hosts to randomly try, etc. Just adds addtl reasurance for long term.
            > note, make this list editable, with an "add" and "remove" opption for this list. Make it a setting as well 
            By default, it shuold auto fill to the listener address, but have the ability to add options at compile time

   # Implant Hardening:
   - [ ] String Encryption
      > https://github.com/skadro-official/skCrypter - encrypts strings at compiletime

   - [ ] Memory Store encryption:
      - [x] XOR via key name, basic, but works for now.

   # Commands list:
      - cd (SetCurrentDirectoryA(path);): sets cwd of whole program

   # Structure:
      - [ ] encoders.cpp: Has stuff for malleable c2 (b64 de/en, b64url de/en, netbios de/en)
      - [ ] metadata.cpp: Metadata gathering (Have this early on, should be good to implement/define some things)

   # advanced/sytems I'll need:
      - Memory tracking System (every malloc, etc) store memory address, size, etc. Will be useful for later addons
            Ex: mem encryption of blocks, wiping of data from mem (free doesn't delete/overwrite )

      
   # Next Steps:
 - [ ] Setup encoder funcs, and tests. (note - have them be pass by ref, and modify data directly, way easier to do something like `b64_decode(data); b64_decode(data); b64_decode(data);`)
    - [X] b64 encode
    - [X] b64 decode
    - [X] b64 url encode
    - [X] b64 url decode
 - [ ] Implement a hardcoded implant loop based on current malc2 prof.
    - [X] Register
    - [X] Get Task
    - [ ] (fake) process
    - [X] Post Task > not posting anythign back seemingly, or somethign is goign wrong. post is erroring out somehwere. missing req data.
    - [ ] Harden functions with checks.

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
- `{"task_uuid":"", "implant_uuid": 9999, "result":{command_output:{"type":"text", "value":"somedata"}, other_value:{"type":"text", "value":"abcd"}}}`

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