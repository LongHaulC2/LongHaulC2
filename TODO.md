## Planning:
 
##  server

 - Structure:
    - [X] Determine a folder structure
    - [X] Logging <
    - [X] SQL Connection & checks
    - [X] Redis Connection & checks

 - API:
  - [X] PUT /implants/{id} (updating records)
  - [X] DELETE /implants/{id}
  - [X] GET /implants/{id}
  - [X] POST /implants/
  - [X] GET /implants/

 - Redis:
   - [X] Figure out a redis structure for client queues.
      Idea: Basic fifo list. Jobs can fail here, and retry is not built in. This is fine, as jobs are seen by humans. if it fails, 
         human sees that, and can choose next steps,instead of accidenlty sending the same command 2 times, etc and causing problems.
         # producer
         redis.rpush("jobs", job_data)

         # consumer
         job = redis.lpop("jobs")



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
      - [ ] Listener supervisor/logic
            - [ ] table in DB with listeners (for easy restart, figure out fields later.)
                  Fields: (listener_id [uuid7, can get start time], listener_ip, listener_port (optional), listener_config (a file pointing to config))
            - [ ] DB service for this table
      - [ ] Listener endpoints
            # put in listener logic with a dummy listener class, etc. & handling for listener args like type.
            - [X]  GET /api/v1/listeners - gets all listeners
            - [DB yes, Listener No]  POST /api/v1/listener/ - Creates a new listener
            - [X]  GET /api/v1/listener/{id} - gets ONE listener
            - [DB Yes, Listener No]  DELETE /api/v1/listener/{id} - stops one listener
      - [ ] Listener hookup to redis/defining of response structure.
            `{task_id:"", "data_type":binary|text, data="somedata"}`? seems good enough for now. 
            Maybe make it a list, for future expansion for multiple responses? iffy.
      - [ ] Keep in mind, be on look out for flexible python webservers, for http listeners. Ex, can easily set things such as endpoints, headers, etc, etc. 

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
 - [X] Figure out structure
      - I don't like it, but no class based widgets, just one file per "page"
 - [X] Logging
 - [X] API Call strucutre/setup
      - needs a way to access user supplied address for where to make the requests
 - [X] Implement GET IMPLANTS (and updates every so often)

 - [X]  Notes (multi and single edit)

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