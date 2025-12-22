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

      

## Client:
 - [X] Figure out structure
      - I don't like it, but no class based widgets, just one file per "page"
 - [X] Logging
 - [X] API Call strucutre/setup
      - needs a way to access user supplied address for where to make the requests
 - [X] Implement GET IMPLANTS (and updates every so often)

 - [ ] Styling: Clean up spacing/layout in terminal of operations
      - tighter, better fitting, and auto focus

 - [ ] PAGES:
   - [ ] Login
   - [ ] Operations