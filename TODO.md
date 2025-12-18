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
   - [ ] Figure out a redis structure for client queues.
      Idea: Basic fifo list. Jobs can fail here, and retry is not built in. This is fine, as jobs are seen by humans. if it fails, 
         human sees that, and can choose next steps,instead of accidenlty sending the same command 2 times, etc and causing problems.
         # producer
         redis.rpush("jobs", job_data)

         # consumer
         job = redis.lpop("jobs")



   - [ ] Add API Endpoints for these 


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