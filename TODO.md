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

    Misc:
        - [ ] Implement Transforms
            - [X] C++
            - [X] Python
        - [ ] Implement parameters/things in client block
            - [ ] C++
            - [ ] Python
        - [ ] Implement Other terminators
            - [ ] C++
            - [ ] Python
        - [ ] Compile

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

      - [X] Plan and build out the actual build process
         - Docker based build system would be nice, takes longer and is a PITA. 
         - Note, subsequent docker builds, or a lot at once, get slow. 
         - Another note, payload id or something similar for tracking said payload that
            the API can return fro tracking payloads after build would be nice. 
            (Need to clarify, payload_uuid, and implant_uuid are 2 diff things, see payload vs implant) - maybe name it build_uuid for tracking the build

         - [X] Fix implant to let it compile
            Use conversions between vector<uint8_t> and std::string - do this in visual studio then copy in
         - [X] test compile
      - [X] Do basic compilation checks (copy paste into visual studio) to make sure generation is okay

         >> here
      - [ ] cleanup build.py <<<<<
         - [X] DELTE OLD TEMP FILES AFTER USING THEM (after write to DB in payload.py)


         - implant vs payload naming: payload: unran implant. Implant: Active implant
         - [ ] Server: Clean up, add output options/logic (exe, etc)
            - Going to need to get that logic into the build process, for which verson of main to include (dll, vs exe main - have a template for both)

         - [ ] Defualt implant gets picked up by defender... yay. ON WHAT????? (it said ml. Probably new donwload, execute, and callback instantly to server)

         - [ ] Add variant back to GUI, seemingly not showing up in payload build

         - [ ] move register to comms. 

      - note... containers not removed atm as they bugged out and would vanish before execution done? 

      - [ ] Implant Formatting/Jinja Options
         http_comms.cpp
            HTTP_GET:
               - Double check these - only x off when known working with different profiles. 
               - Metadata
                  - [X] Header
                  - [ ] Parameter
                  - [ ] URI
                  - [ ] Print

               - Task (server) Output
                  - [ ] Header
                  - [ ] Parameter
                  - [ ] URI
                  - [X] Print

                  Register works, bug at HTTP_POST, so we get a successful register, but not a consistent loop:
                     "019be859-b11f-769b-9e2a-27b180f326da"
                     terminate called after throwing an instance of 'nlohmann::json_abi_v3_12_0::detail::parse_error'
                     what():  [json.exception.parse_error.110] parse error at byte 2: syntax error while parsing MessagePack value: expected end of input; last byte: 0x22

                     Likely due to a bad base64 -> server. Investigate on wire comms (wireshark + cyberchef), but it compiles fine. 
                     Need to also think about resilient failures, like, if fail, continue to next loop.

               - imlpement
            HTTP_POST:
               - ID
                  - [ ] Header
                  - [ ] Parameter
                  - [ ] URI
                  - [ ] Print

               - Client Output (client -> server)
                  - [ ] Header
                  - [ ] Parameter
                  - [ ] URI
                  - [ ] Print


Just remember, block == sender (ex, client, means sent from client). Transformations are top down
from the sender. 


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