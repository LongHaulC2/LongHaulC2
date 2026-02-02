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
   - [ ] Per-Agent page


#  server
   # API cleanup:

   #### Logging:
      # Last, before switching to GUI:
      - [ ] Convert everything to structlogger (with binds, etc.) Big tasks
      - [X] Add `check_type` on modules/other server code where applicable

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
      - [ ] Statically compiled
      - [ ] DLL Based (windows)
      - [x] CMAKE based

   ## Plan:
      - [x] Test messagpack
      - [x] Test libcurl for HTTP
         - [x] maybe just use winhttp (start with winINet, for quicker dev, re-evaluate later)
            - https://learn.microsoft.com/en-us/cpp/mfc/wininet-basics?view=msvc-170

      - [x] Decide project structure (folder struct, etc)
  
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

   - [ ] Figure out param field
          [go with this, is a better idea]
        - idea 1: Create an entirely seperate function with a "param" input (vector of strs) that auto adds params onto the request (stamped in at build)

 # Stamping in/templating:
    Goal: Only touch comms functions, make everything as generic as possible to "just work"/follow a schema. AKA, if you have an http implant vs ntp, the only thing that changes
        are the protocol calls (ex, for ntp, call get() -> ntp_get(), for http, call get() -> http_get())


    Step 1: Python logic for which options, files needed etc.
    2. Format code blocks with data  (callback, transforms, etc)
    3. Paste into build files

   >> here
   Left off: 
      Working on jinja templating.
      - [X] Make http_wininet_context into its own file, break up/clean up, and import into build.py
      - [>] Make sure transform_?.j2 match c++ function calls
         - [X] base64
         - [X] base64url
         - [X] append
         - [X] prepend
         - [ ] xor (still not sure about how the key works/where to get it from. Maybe generate on client side, OR pass in from server, in metadata/register)
         - [X] netbios
         - [X] netbiosu

         - Keep in mind the reverse steps macros, make a reverse set of macros for reversing.
            Name it "render_reverse_transform_metadata(object)
            - [X] Reverse are there, need to use where to reverse (ex, data coming back from server)
               - Just http-get.server has this at the moment, as that's where tasks are retrieved from.
               - This could, and probably should be added onto http-post server output, but it doesn't matter too much, as 
                  no meaningful data is transfered on that channel afaik. (some profiles do use it for some seemingly blank data)

      - [ ] cleanup build.py <<<<<
         - [X] DELTE OLD TEMP FILES AFTER USING THEM (after write to DB in payload.py)

         - implant vs payload naming: payload: unran implant. Implant: Active implant
         - [ ] Server: Clean up, add output options/logic (exe, etc)
            - Going to need to get that logic into the build process, for which verson of main to include (dll, vs exe main - have a template for both)

         - [ ] Add variant back to GUI, seemingly not showing up in payload build

         - [ ] move register to comms. 

      - note... containers not removed atm as they bugged out and would vanish before execution done? 

         >> Works - just continue building out/testing:
      - [ ] Implant Formatting/Jinja Options
         - [ ] Update keys needed at ehader of j2
         http_comms.cpp
            - [ ] http-config:
               - Add user agent (parser, in jinja, etc. )

Just remember, block == sender (ex, client, means sent from client). Transformations are top down
from the sender. 


# Test planning - need before further development
 3 VM's:

 1. C2 Host (linux)
 2. Operator ( (windows or lin) run scripts from - gui would be nice for debugging things.)
 3. Victim ( (windows) where agents are run)

Save/Revert; snapshots w proxmox

Goals;
 - test Malleable c2 scripts (make sure nothing breaks)
 - tests install pattern
 - tests implant compilation, etc. 
 - load testing?

Idea:
 - install server
 - start server
 - run script to create X listeners (various malleabel c2, that cover all test cases, params, output, etc)
 - compile implants for each listener
 - donwload implants
 - run on victim (somethign dumb like winrm or psexec or a way to just easily execute them, use a bad passwd for victim pc)
 - some sort of checker script that checks certain values to make sure everything is okay (this is a sanity check for the API as well to make sure Ihave everyhting)

Shorter goal:
 - 1 script, with a profiles folder. Script does everything. 

 - [ ] build id
   - [ ] add proper docs/logging to endpoint, and sub funcs, then continue testing



> here
Testing:

Every test failed - lots of crashes, which means invalid data being sent back to server/it's interpreting it wrong. 


Bugs:
 - [X] order: http_get metadata seems to be doing transforms in reverse order. 
 - [ ] Delim: Seems to be a problem that some profiels have delims, ex `"\"en-us\""`. TLDR: delims don't get escaped, and implant math on length of this datais wrong, which casues decode errors. 

 - [X] Extra / in URL's. YARL every URL string, check every point it could be at.


Note: may need to intergrate the special chars, \x, etc (see docs) that mc2 allows for, to get a 100% pass below.

- [X] delim \" and \"
- [ ] \x byte conversion (\x00 -> bytes in string)
      >: Example: `b = bytes("\x33", "latin-1")`, then take b and append to bytearray
      > latin-1 because it maps from 0x00 to 0xFF
- [ ] other converstions in mc2
Current test results:

========================================
      FINAL EXECUTION REPORT
========================================
my guess: 
 - step 5 == Was cookies, need to check profile by profile next.
 - Step 7: Unsure, somethign not matching the POST data as needed by server. test case by case

========================================
      FINAL EXECUTION REPORT
========================================
amazon.profile                 | FAILURE: Step 7 (Output Verification Failed)
apt1_virtuallythere.profile    | FAILURE: Step 7 (Output Verification Failed)
asprox.profile                 | FAILURE: Step 7 (Output Verification Failed)
backoff.profile                | FAILURE: Step 7 (Output Verification Failed)
bingsearch_getonly.profile     | SUCCESS
cnnvideo_getonly.profile       | SUCCESS
comfoo.profile                 | SUCCESS
etumbot.profile                | SUCCESS
fiesta.profile                 | SUCCESS
fiesta2.profile                | SUCCESS
gmail.profile                  | FAILURE: Step 7 (Output Verification Failed)
googledrive_getonly.profile    | SUCCESS
havex.profile                  | FAILURE: Step 5 (Execution - Crashed/Exited)
magnitude.profile              | FAILURE: Step 7 (Output Verification Failed)
meterpreter.profile            | FAILURE: Step 5 (Execution - Crashed/Exited)
microsoftupdate_getonly.profile | FAILURE: Step 5 (Execution - Crashed/Exited)
msnbcvideo_getonly.profile     | SUCCESS
ocsp copy.profile              | SUCCESS
ocsp.profile                   | SUCCESS
onedrive_getonly copy.profile  | SUCCESS
onedrive_getonly.profile       | SUCCESS
pandora.profile                | FAILURE: Step 5 (Execution - Crashed/Exited)
pitty_tiger.profile            | FAILURE: Step 5 (Execution - Crashed/Exited)
reference.profile              | Incomplete (Unknown Error)
rtmp.profile                   | SUCCESS
safebrowsing.profile           | FAILURE: Step 7 (Output Verification Failed)
string_of_paerls.profile       | FAILURE: Step 7 (Output Verification Failed)
taidoor.profile                | FAILURE: Step 5 (Execution - Crashed/Exited)
webbug.profile                 | FAILURE: Step 5 (Execution - Crashed/Exited)
webbug_getonly.profile         | FAILURE: Step 5 (Execution - Crashed/Exited)
wikipedia_getonly.profile      | FAILURE: Step 7 (Output Verification Failed)
zeus.profile                   | FAILURE: Step 7 (Output Verification Failed)
========================================

Misc idea:
 - "melting pot" where all comms that come in, and have some data, etc, are stored, but don't have valid ID's, etc etc. Just so repsonses aren't lost?


 - latest bug: 
  - Amazon: paramter extraction screwed up on post... not sure why. likely me mistyping something somewhere. 

```
=== REQUEST DUMP ===
METHOD: POST
URL: http://www.amazon.com/N4215/adj/amzn.us.sr.aps?sn=019c20a6-c03f-7327-8403-5c94e4578b2a&sz=160x600&oe=oe=ISO-8859-1;&s=3717&dc_ref=http%3A%2F%2Fwww.amazon.com
HEADERS: {'user-agent': 'GoogleChrome', 'accept': '*/*', 'content-type': 'text/xml', 'x-requested-with': 'XMLHttpRequest', 'host': 'www.amazon.com', 'content-length': '248', 'cache-control': 'no-cache'}
QUERY: {'sn': '019c20a6-c03f-7327-8403-5c94e4578b2a', 'sz': '160x600', 'oe': 'oe=ISO-8859-1;', 's': '3717', 'dc_ref': 'http://www.amazon.com'}
BODY: g6xpbXBsYW50X3V1aWTZJDAxOWMyMGE2LWMwM2YtNzMyNy04NDAzLTVjOTRlNDU3OGIyYaZyZXN1bHSCpGRhdGHZNklmIHlvdSBzZWUgdGhpcyBpdCBtZWFucyB0aGUgaW1wbGFudCBpcyB0YWxraW5nIHRvIHlvdalkYXRhX3R5cGWkdGV4dKl0YXNrX3V1aWTZJDAxOWMyMGE2LWRiZjEtN2U3MS1hYzMwLTNlMjBjNDU0YjBhMg==
2026-02-02T23:18:55.185155Z [debug    ] incoming_request               [listener] ip=10.0.0.24 method=POST path=/N4215/adj/amzn.us.sr.aps ua=GoogleChrome
2026-02-02T23:18:55.185399Z [debug    ] config_block_error             [listener] error="'http_config'" ip=10.0.0.24 method=POST path=/N4215/adj/amzn.us.sr.aps
2026-02-02T23:18:55.185489Z [debug    ] http-config block not found    [listener] ip=10.0.0.24 method=POST path=/N4215/adj/amzn.us.sr.aps
2026-02-02T23:18:55.185617Z [error    ] post_output_error              [listener] error='400: Missing required data' ip=10.0.0.24 method=POST path=/N4215/adj/amzn.us.sr.aps
```

  - I saw a base64 error during testing too.


# Task Formatting (for reference):

Note: Task_uuid and implant_uuid are included for task verification (right task to right agent),
and for potential pivoting (to know which tasks go to which agents)

## Task  Structure
- `{task_uuid: <some_uuid>, implant_uuid: <intended_target>, "task":{"taskname":"somename" "args":{"arg1":"value1"}}}`

Ex: `{task_uuid: 1234, implant_uuid: 9999, "task":{"taskname":"cmd" "args":{"cli":"whoami"}}}`

List of tasks:
- `[{task_uuid: 1234, implant_uuid: 9999, "task":{"taskname":"cmd" "args":{"cli":"whoami"}}}, {task_uuid: 1234, implant_uuid: 9999, "task":{"taskname":"cmd" "args":{"cli":"whoami"}}}]`

## Task Response Structure:
- `{"task_uuid":"", "implant_uuid": 9999, "result":{"data_type":binary|text, "data":"somedata"}}`

Ex: `{"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}`

List of task responses:
- `[{"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}, {"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}]`

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