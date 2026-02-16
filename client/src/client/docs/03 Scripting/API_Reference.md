# API V1
## Version: 1.0

### /build/

#### GET
##### Summary:

Get a list of all payloads in the Database

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| X-Fields | header | An optional fields mask | No | string (mask) |

##### Responses

| Code | Description | Schema |
| ---- | ----------- | ------ |
| 200 | Success | [BuildItemWrapper](#BuildItemWrapper) |

#### POST
##### Summary:

Submit a task to build a new C2 implant payload

##### Description:

This endpoint accepts a JSON configuration defining the implant's properties,
including its name, output format, and a dictionary of listeners it should communicate with.

The build process is asynchronous. This endpoint returns immediately with a `build_uuid`
which can be used to poll the status via `GET /builds/{build_uuid}`.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Listener ID (uuid) to build implant to | No | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /build/jobs/{build_uuid}

#### GET
##### Summary:

Get the status of a build job

##### Description:

Contains all of the information about a build, except for payload bytes, and zip bytes.

If you are looking for the payload/source code,
Please use:

 - `GET /api/v1/build/{payload_hash}` to get the payload as a file (bytes)
 - `GET /api/v1/build/{payload_hash}/source` to get the source code zip

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| build_uuid | path |  | Yes | string |
| X-Fields | header | An optional fields mask | No | string (mask) |

##### Responses

| Code | Description | Schema |
| ---- | ----------- | ------ |
| 200 | Success | [BuildStatus](#BuildStatus) |

### /build/{hash}

#### GET
##### Summary:

Download a specific payload artifact, based on the provided hash

##### Description:

Downloads a single implant

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| hash | path | Hash of implant | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Binary File Stream |
| 400 | Bad request |
| 404 | Payload Not Found |
| 405 | Method Not Allowed |
| 500 | Server Error |

#### DELETE
##### Summary:

Delete a specific payload artifact, based on the provided hash

##### Description:

Deletes a single implant

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| hash | path | Hash of implant | Yes | string |
| X-Fields | header | An optional fields mask | No | string (mask) |

##### Responses

| Code | Description | Schema |
| ---- | ----------- | ------ |
| 200 | Deletion Successful | [SuccessResponse](#SuccessResponse) |
| 400 | Bad request |  |
| 404 | Payload Not Found |  |
| 405 | Method Not Allowed |  |
| 500 | Server Error |  |

### /build/{hash}/source

#### GET
##### Summary:

Download the source code zip for a specific payload

##### Description:

Retrieves the source code archive (ZIP) for a specific implant build.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| hash | path | The MD5 hash of the payload source to download | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Source Code Archive (ZIP) |
| 400 | Bad request |
| 404 | Source Code Not Found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /implants/

#### GET
##### Summary:

Gets all implants

##### Description:

Retrieve all implants the server knows about.
1. Gets a MYSQL Session

2. Retrieves all records in 'implant' table

3. Returns said data in JSON  format.

Note: There is no pagination on this. If there's a lot of entries, this request may take a while.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 404 | Implant not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

#### POST
##### Summary:

Create a new implant entry

##### Description:

Create a new implant entry. Returns an Implant ID to use with that implant
1. Gets a MYSQL Session

2. Creates a new record in the 'implants' table

3. Returns ID of new record in response

Note: This will create "ghost" sessions with no metadata. Metadata gets updated when 'PUT /v1/api/implants/{uuid}/' is called.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad Request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /implants/history/search

#### POST
##### Summary:

Search for an task with fields that match the supplied term

##### Description:

Search for an implant with fields that match the supplied term. Returns a list of dicts, with implants that have said term in them.
Returns a list of dicts, with implants that have said term in them.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| payload | body |  | Yes | [SearchModel](#SearchModel) |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /implants/search

#### POST
##### Summary:

Search for an implant with fields that match the supplied term

##### Description:

Search for an implant with fields that match the supplied term. Returns a list of dicts, with implants that have said term in them.
Returns a list of dicts, with implants that have said term in them.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| payload | body |  | Yes | [SearchModel](#SearchModel) |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /implants/{uuid}

#### PUT
##### Summary:

Update a single implant by its unique ID

##### Description:

Update a single implant by its unique ID. Data is supplied in the body of the request.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Agent ID (64-bit integer) | Yes | string |
| payload | body |  | Yes | [ImplantCreate](#ImplantCreate) |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad Request |
| 404 | Implant not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

#### GET
##### Summary:

Gets one implant based on user supplied ID

##### Description:

Retrieve a single implant by its unique ID.
1. Gets a MYSQL Session

2. Retrieves 1 record in 'implant' table based on ID

3. Returns said data in JSON format.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Agent ID (64-bit integer) | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 404 | Implant not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

#### DELETE
##### Summary:

Deletes one implant based on user supplied ID

##### Description:

Delete a single implant by its unique ID.
1. Gets a MYSQL Session

2. Deletes 1 record in 'implant' table based on ID

3. Returns said data in JSON format.

Note: Operationally, it might be best to not delete old records unless the user wants to.
    ID's are NOT reused after deleting, so if you delete record 1, said ID will NOT be reused upon calling `POST /v1/api/implants/`

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Agent ID (64-bit integer) | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad Request |
| 404 | Implant not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /implants/{uuid}/task

#### GET
##### Summary:

Gets next task of implant

##### Description:

Retrieve the next task for the implant
Task is returned as a base64 encoded, MSGPACK blob

This will DEQUEUE the next task, NOT peek.

Meant to be called by listeners, to get the next task to forward to the implant.

1. Spins up a new RedisImplantTaskService instance
2. Dequeus next task
3. Converts each task into base64 (From MSGPACK blob)
4. Return response with task in data field: `{"task":"AABB=="}`

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Agent ID (64-bit integer) | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 404 | Task not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

#### POST
##### Summary:

Add a task to a single implant by its unique ID

##### Description:

Add a task to a single implant by its unique ID. Data is supplied in the body of the request.
Data is supplied in the body of the request.

Returns a task_uuid for tracking the task:

{"task_uuid": task_uuid}

Note, this accepts a task in the form of a JSON body, OR a MSGPACK blob (with content-type header of application/msgpack). The server will convert the task into a MSGPACK blob before putting it in the queue, so either format can be used by the client.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Agent ID (64-bit integer) | Yes | string |
| payload | body |  | Yes | [Task](#Task) |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Task not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /implants/{uuid}/tasks

#### GET
##### Summary:

Peek all currently queued tasks of implant

##### Description:

Peeks all currently queued tasks of implant
Tasks are returned as a list of tasks,
with the task being a base64 encoded MSGPACK blob.


1. Gets how many tasks are queued
2. Peeks that many tasks and returns them (as MSGPACK blob)
3. Converts each task into base64
4. Returns list of tasks `[{"task":"AABB=="},{"task":"AABB=="}]`

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Agent ID (64-bit integer) | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 404 | Task not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

#### DELETE
##### Summary:

Delete all the currently queued tasks of an agent

##### Description:

Delete all the tasks of an implant

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Agent ID (64-bit integer) | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Task not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /implants/{uuid}/tasks/history

#### GET
##### Summary:

Gets ALL history of an implant from the DB

##### Description:

Gets task history of implant from the DB. Provide 'since' parameter, with a uuid, to lookup since a previous uuid7, otherwise all history is returned
1. Queries MySQL DB
2. Returns results as a list of tasks

Ex:
```
{
    "data": [
        {
            "implant_uuid": 1,
            "task_request": {
                "data": {
                    "somevar": "1234"
                },
                "task": "cmd",
                "uuid": "019b46f8-e066-76ff-bb2f-0a1f0daa318c"
            },
            "task_response": null,
            "task_uuid": "019b46f8-e066-76ff-bb2f-0a1f0daa318c"
        },
    ]
}
```

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Agent ID (64-bit integer) | Yes | string |
| since | query | Return tasks with task_uuid greater than this UUIDv7 | No | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /listeners/

#### GET
##### Summary:

Gets all listeners

##### Description:

Retrieve all listeners in the DB.
1. Gets a MYSQL Session

2. Retrieves all records in 'listeners' table

3. Returns said data in JSON format.

Note: There is no pagination on this. If there's a lot of entries, this request may take a while.

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

#### POST
##### Summary:

Spawn a new listener

##### Description:

Create a new listener. Returns an listener ID to use with that listener
1. Gets a MYSQL Session

2. Creates a new record in the 'listeners' table

3. Returns ID of new record in response

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| payload | body |  | Yes | [ListenerSpawnModel](#ListenerSpawnModel) |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### /listeners/{uuid}

#### GET
##### Summary:

Gets one listener based on user supplied ID

##### Description:

Retrieve a single listener by its unique ID.
1. Gets a MYSQL Session

2. Retrieves 1 record in 'listeners' table based on ID

3. Returns said data in JSON format.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Listener ID (uuid) | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

#### DELETE
##### Summary:

Deletes/Stops one listener based on user supplied ID

##### Description:

Stops one listener based on user supplied ID
1. Gets a MYSQL Session

2. Deletes 1 record in 'listener' table based on ID

3. Returns said data in JSON format.

##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| uuid | path | Listener ID (uuid) | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |
| 400 | Bad request |
| 404 | Not found |
| 405 | Method Not Allowed |
| 500 | Server Error |

### Models


#### BuildItemWrapper

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| data | [ [BuildItem](#BuildItem) ] |  | No |
| message | string |  | No |
| status | string |  | No |

#### BuildItem

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| build_uuid | string | The UUID of the build | No |
| build_status | string | The status of the Payload building | No |
| payload_name | string | The name of the payload in the Database | No |
| payload_hash | string | The MD5 hash of the Payload after it is build. This is initially blank, and filled in when the payload has been successfully compiled. | No |

#### BuildStatus

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| build_uuid | string | The UUID of the build | No |
| build_status | string | The status of the Payload building | No |
| payload_name | string | The name of the payload in the Database | No |
| payload_hash | string | The MD5 hash of the Payload after it is build. This is initially blank, and filled in when the payload has been successfully compiled. | No |

#### SuccessResponse

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| status | string |  | No |
| message | string |  | No |
| data | string | No data returned | No |

#### ImplantCreate

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| external_ip | string | External IP address (IPv4/IPv6) | No |
| internal_ip | string | Internal IP address | No |
| listener | string | Listener address (IP or DNS) | No |
| user | string | User account name | No |
| system_hostname | string | Hostname of the system | No |
| notes | string | Operator notes | No |
| process | string | Process name | No |
| pid | integer | Process ID | No |
| arch | string | CPU architecture | No |
| last_checkin | string | Last check-in time (unix) | No |
| sleep_value | integer | Sleep interval in seconds | No |

#### Task

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| implant_uuid | string | Implant UUID | Yes |
| task | [TaskDetail](#TaskDetail) |  | Yes |

#### TaskDetail

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| task_name | string | Task type/name | Yes |
| args | [TaskArgs](#TaskArgs) | Task arguments | Yes |

#### TaskArgs

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| cli | string | Command line to execute | Yes |

#### SearchModel

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| search_term | string | Term to search for. | Yes |

#### ListenerSpawnModel

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| listener_host | string | Host the listener will listen on (DNS Host, or IP address) | Yes |
| listener_port | integer | Port to spawn the listener on | No |
| listener_type | string | What type of listener to spawn | Yes |
| listener_name | string | Name of listener | Yes |
| listener_notes | string | Listener notes | No |
| listener_profile_name | string | Listener malleable c2 profile name | Yes |
| listener_profile_contents | string | Listener malleable c2 profile contents (i.e., read the profile, and pass that string here) | Yes |