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
  


   # Strategies:
      - Compile implant with multiple strategies, i.e. multiple malleable c2 profiles
      Implant then has it listed in its settings, that it can use those strats

      user then:
         `strat <name_of_strat>`
         and implant switches to said strat. Ex, HTTP bingsearch -> http_cnnvideo | http->ntp, etc. 

      Implementation...

      - [X] Code outline/poc
      - [ ] jinja template it
         - going to need:
            - list of profiles that need to be compiled
            - A rendered copy of each profile in c++ (store all these funcs in a comms.cpp/comms.h I guess)
               > funcs will need to be named `protocol_get|post_<name_of_profile>`
               ex: `http_post_amazon` (need conversion to c++ safe var names)
         Files to be rendered:
            - c2.cpp -> /control/c2.cpp
               > init function with mappings.
                  Name of profile, mapped to function name. (need to add function name to jinja template for http_wininet)
                  `s_ingress_map["http_get_amazon"] = get_HTTP;`
                  `s_egress_map["http_post_amazon"] = post_HTTP;`

            settings... eventually. 


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