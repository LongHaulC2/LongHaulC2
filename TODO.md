## Planning:
 
##  server
   - [ ] Add API Endpoints for these 
      X Left off: `{{baseUrl}}/implants/:id/task` - return payload["id"] bug.

      - Marshalling on output of GET /implants/id/task, and /implants/id/tasks. 
         - maybe consider marhsalling on every output... don't go too far into the rabbit hole


      - Configure/rename keys, have an "inbox" and "outbox" for each agent.
         [ ] Inbox: Data from implants (unknown format - some json/msgpack format. Undecided)
            - Batch write to mysql every 1 second to prevent thrashing, and have a command log
         [X] Outbox: Tasks for clients (the usual task queue, just rename it.)
            - [X] Write command to mysql (plaintext for searchability), and redis (msgpack). 
               (if scaling is an issue here, can cache commands in redis and batch write to mysql on intervals - more complicated)
               [X] Define mysql schema
               NOTE: task_uuid will be used for request and response for correlation.
            - [X] Clean up and add logging. 

      Post this, close branch, move to gui, and implenet terminal properly. 

   - [ ] Listeners
      - [ ] Listeners
         - [ ] play with HTTP listener & malleable c2 parsing POC. 

      - [ ] Listener hookup to redis/defining of response structure.
            `{task_id:"", "data_type":binary|text, data="somedata"}`? seems good enough for now. 
            Maybe make it a list, for future expansion for multiple responses? iffy.
      - [ ] Keep in mind, be on look out for flexible python webservers, for http listeners. Ex, can easily set things such as endpoints, headers, etc, etc. 

   # API cleanup:
      - [ ] Exceptions where needed in logic 
         - These must bubble up

# Mal c2:

 - [ ] Server
   - [ ] RESPONSE
      # leftoff working on maleable c2 compatability. GET seems fine, finish with terminiationtypes, then start on POST.

      # after  that, client side support would be good to look into
      
      - [X] terminiation types (learn how cs puts data in the responses) 
            Spin up  wireshark and do some research with an http beacon on where this data is put for each terminator type


   See readme, tldr:
      left off  trying different profiles. Things to do:

      ### 1. **Test Various Malleable C2 Profiles**
         - [ ] Test different C2 profiles.
         - [ ] Experiment with different configurations to see if I can break it
         - [ ] Mask is busted, needs a key, and that doesnt seem to be specified in the 
               mc2 profile. Need a way to store that key, or just not include mask at the moment.
            * [Throws Key Error] `mask` 

      ### 2. **Global Options**
         - [ ] Set up global options handling for the system.

      ### 3. **Redis Integration**
         - [X] > hook into Redis for task management.
            - [X] > Need to define metadata structure. Likely will contain ID at a minimum. 
               {"id":"uuid"} (msgpack) is probably best minimum needed on get. Can then add other fields  as needed, later. 

               - [X] HTTP Get  
               - [X] HTTP Get URI 
               - [X] HTTP Post  
               - [X] HTTP Post URI  

               - [ ] fix up the redis side/rest of code to use new task stuff
                  - [X] Modify to have inbox/outbox keys.
                  - [ ] Note, implant-tasks might have a busted implant_id,that shows 0

               - [ ] Redis watchdog to actually write responses/make sure the full chain/flow works
                  - [X] Stuck at http-post, bug when posting back, shows data is none that is from parameter and header apparently have a .key method, instead of a .value
                     
                     this was causing 400 errs on http-post
                     Unsure if uri-append is key or value 

                     - [ ] Check URI-APPEND malleable c2 option and see if it stores the parameter in value or key (if it even stores one...)

                     ```
                     if name in ("uri-append"):
                        return name, value
                     elif name in ("parameter", "header"):
                        return name, stmt.key
                     ```req. Weird. print more stuff.


               - [ ] Make a quick shitty dev python implant with hardcoded responses to test the flow


         - [ ] Ensure proper data retrieval from Redis.
         - [ ] Implement tasking mechanisms to inject custom data into responses.

      ### 4. **Error Handling**
         ~~- [ ] Implement error handling for invalid profiles.~~
         - [ ] Add error handling for invalid options or bad configurations.
         - [ ] Create logging for when errors occur.
         - [X] Graceful failure for unexpected scenarios (e.g., invalid data format, connection issues).

      ### 5. teseting & docs:
         - [ ] Test "untested" methods in readme to make sure they work. 

         - [X] Create a draw io of full path of data as it comes in (including if bytes, etc. When headers appended, etc. For post and get)
      ### Addtl HTTP blocks:
         - [X] http-config

 - [ ] Implant

# Task Formatting (for reference):

Note: Task_uuid and implant_uuid are included for task verification (right task to right agent),
and for potential pivoting (to know which tasks go to which agents)

## Task  Structure
- `{task_uuid: <some_uuid>, implant_uuid: <intended_target>, "task":{"taskname":"somename" "args":{"arg1":"value1"}}}`

Ex: `{task_uuid: 1234, implant_uuid: 9999, "task":{"taskname":"cmd" "args":{"cli":"whoami"}}}`

List of tasks:
- `[{task_uuid: 1234, implant_uuid: 9999, "task":{"taskname":"cmd" "args":{"cli":"whoami"}}}, {task_uuid: 1234, implant_uuid: 9999, "task":{"taskname":"cmd" "args":{"cli":"whoami"}}}]`

# Task Response Structure:
- `{"task_uuid":"", "implant_uuid": 9999, "result":{"data_type":binary|text, "data":"somedata"}}`

Ex: `{"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}`

List of task responses:
- `[{"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}, {"task_uuid":"1234", "implant_uuid": 9999, "result":{"data_type":"text", "data":"somedomain\bob"}}]`

# Metadata Structure:
- `{"implant_uuid":"uuid", ...}`

Ex: `{"implant_uuid":"1234"}`

# Scripting Idea:
   # FIX / PLAN EVERYTHING ELSE FIRST. 
 - [x] API  already exists, so let that be the way that 3rd party things can interact. 

 - Idea #1:
   - A "terminal" on a page that has scriptsin the current dir. These are scripts that make api calls that interact with the 
      server

 - Idea #2: Something similar to splunk soar's scripting, either with blockscripting (complicated) or manual scripting (simpler), where it's a glorified IDE, and has a run menu/output. 

   From a usecase, #2 with blockscripting is easier, but #2 with manual scripting + fake IDE may be easiest.
   Example scripts would be necessary,  ex, getting all current beacons, and queueing a task for those with the external ip of X

   TODO:
   - [X] Keybinds (save) # would overwrite the default ctrl+s on the page. maybe a consideration for later. 
   - [X] File save func
      > might want to hash files, and compare OG to current saved file, to detect changes. Can then rename as something else? Prevents multiple save conflicts
   - [X] Create new file



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