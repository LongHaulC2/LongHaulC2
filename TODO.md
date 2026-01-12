## Planning:
 
# GUI:

   - [X] Task Enqueuing
   - [X] Task Retrieval
      - start with polling? do something else later?
      - ex, get all messages since last timestamp retrieval to not overload. 
      > left off workign on the terminal display. 
         - Thoughts: 
            - Maybe switch ID to username, takes up less space

      - [X] Implement history command, a special command, that displays all console history (just calls get_all_history)
      - [X] Prepend it with ------ * whatever. Warn user post command, that the history may be truncated due to
            max ui.log output size. 

      - [X] Auto scroll to bottom at term open

   >> start here (in gui-cleanup branch)
   # nice to haves:
      - [X] Logging
         - [X] Switch to structlogger
            - [X] api_calls and url.py
            <!-- - [ ] pages -->
            - [X] utils

      - [X] Type checker (check_type) where possible. 
            - [X] api_calls and url.py
            - [X] pages

   - [ ] Per-Agent page
   - [ ] Fix any tab issues
      - [ ] Closing last tab leaves the tab "open"

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