# API V1 Documentation

**Title:** API V1

**Version:** 1.0

**Base URL:** `/api/v1`

<!-- ## Table of Contents -->

<!-- 1. [Build Operations]()
2. [Implant Operations]()
3. [Listener Operations]() -->

---

# Build Operations

Anything and everything related to the Payload build process.

###Get All Builds

**HTTP Method:** `GET`

**Path:** `/build/`

**Description:** Get a list of all payloads/builds currently in the Database.

**Authentication:** None specified.

**Parameters:** *None.*

**Responses:**

**200 OK** List of builds retrieved successfully.

| Field Name | Type | Description |
| --- | --- | --- |
| **status** | string | The HTTP status code (e.g., "200"). |
| **message** | string | Status message (e.g., "Success"). |
| **data** | array | List of build objects. |
| data[].**build\_uuid** | string | The UUID of the build. |
| data[].**build\_status** | string | Status: `failed`, `complete`, or `building`. |
| data[].**payload\_name** | string | Name of the payload. |
| data[].**payload\_hash** | string | MD5 hash of the payload after build. (Initally is NULL) |

**Example Response:**

```json
{
  "data": [
    {
      "build_uuid": "00000000-0000-0000-0000-000000000000",
      "build_status": "building",
      "payload_name": "metadata_test",
      "payload_hash": "7f3df637f39704c04d49d12906407ce8"
    }
  ],
  "message": "Success",
  "status": "200"
}

```

**Error Handling (400, 404, 500):**

```json
{
  "status": "400",
  "message": "Bad Request",
  "data": {}
}

```

**Python Usage:**

```python
import requests

url = "http://localhost:5000/api/v1/build/"

try:
    response = requests.get(url)
    response.raise_for_status()
    print(response.json())
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")

```

---

###Submit Build Task

**HTTP Method:** `POST`

**Path:** `/build/`

**Description:** Submit a task to build a new C2 implant payload. This endpoint accepts a JSON configuration defining the implant's properties, including its name, output format, and a dictionary of listeners it should communicate with. The build process is asynchronous; use the returned `build_uuid` to poll status.

**Authentication:** None specified.

**Request Body:**

| Field Name | Type | Required | Description |
| --- | --- | --- | --- |
| **implant\_name** | string | **Yes** | Name of the implant (e.g., "implant_one"). |
| **output\_format** | string | **Yes** | Output format (e.g., "exe", "bin"). |
| **listener\_uuids** | array[str] | **Yes** | List of listener UUIDs to compile into the implant. |
| **initial\_get\_profile\_listener\_uuid** | string | **Yes** | UUID of listener for GET profile. |
| **initial\_post\_profile\_listener\_uuid** | string | **Yes** | UUID of listener for POST profile. |

**Example Request:**

```json
{
  "implant_name": "implant_one",
  "output_format": "exe",
  "listener_uuids": [
    "0194fdc2-fa2f-4cc0-81d3-ff12045b3d33",
    "0194fdc2-fa2f-4cc0-81d3-ff12045b3d34"
  ],
  "initial_get_profile_listener_uuid": "019c...",
  "initial_post_profile_listener_uuid": "019c..."
}

```

**Responses:**

**200 OK** Build initiated.

| Field Name | Type | Description |
| --- | --- | --- |
| **status** | string | HTTP status code. |
| **message** | string | Status message. |
| **data** | object | Build details. |
| data.**build\_uuid** | string | The UUID of the initiated build job. |

**Example Response:**

```json
{
  "data": {
    "build_uuid": "019c..."
  },
  "message": "Success",
  "status": "200"
}

```

**Error Handling (400, 404, 500):** Standard error response.

**Python Usage:**

```python
import requests

url = "http://localhost:5000/api/v1/build/"
payload = {
    "implant_name": "my_implant",
    "output_format": "exe",
    "listener_uuids": ["UUID_HERE"],
    "initial_get_profile_listener_uuid": "UUID_HERE",
    "initial_post_profile_listener_uuid": "UUID_HERE"
}

response = requests.post(url, json=payload)
print(response.json())

```

---

### Get Build Job Status

**HTTP Method:** `GET`

**Path:** `/build/jobs/{build_uuid}`

**Description:** Get the status of a specific build job. Contains all information about a build except for payload bytes and zip bytes.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **build\_uuid** | string | **Yes** | The UUID of the build job. |

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **status** | string | HTTP status code. |
| **message** | string | Status message. |
| **data** | object | Job details. |
| data.**build\_uuid** | string | The UUID of the build. |
| data.**build\_status** | string | Status: `failed`, `complete`, or `building`. |
| data.**payload\_name** | string | Name of the payload. |
| data.**payload\_hash** | string | MD5 hash of the payload. |

**Example Response:**

```json
{
  "data": {
    "build_uuid": "0000...",
    "build_status": "complete",
    "payload_name": "metadata_test",
    "payload_hash": "7f3df..."
  },
  "message": "Success",
  "status": "200"
}

```

**Python Usage:**

```python
import requests

build_uuid = "YOUR_BUILD_UUID"
url = f"http://localhost:5000/api/v1/build/jobs/{build_uuid}"

response = requests.get(url)
print(response.json())

```

---

### Download Payload Artifact

**HTTP Method:** `GET`

**Path:** `/build/{hash}`

**Description:** Downloads a specific single implant payload based on the provided MD5 hash.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **hash** | string | **Yes** | Hash of the implant. |

**Responses:**

**200 OK** Binary File Stream. Content-Disposition header typically contains `filename=payload.bin`.

**Error Handling (400, 404, 500):** Standard error response (JSON).

**Python Usage:**

```python
import requests

file_hash = "7f3df..."
url = f"http://localhost:5000/api/v1/build/{file_hash}"

response = requests.get(url, stream=True)
if response.status_code == 200:
    with open("payload.bin", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download complete.")
else:
    print(response.text)

```

---

### Delete Payload Artifact

**HTTP Method:** `DELETE`

**Path:** `/build/{hash}`

**Description:** Deletes a single implant artifact based on the provided hash.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **hash** | string | **Yes** | Hash of the implant. |

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **message** | string | "Success" |

**Python Usage:**

```python
import requests

file_hash = "7f3df..."
url = f"http://localhost:5000/api/v1/build/{file_hash}"

response = requests.delete(url)
print(response.json())

```

---

### Download Source Code

**HTTP Method:** `GET`

**Path:** `/build/{hash}/source`

**Description:** Retrieves the source code archive (ZIP) for a specific implant build based on the payload hash.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **hash** | string | **Yes** | The MD5 hash of the payload source to download. |

**Responses:**

**200 OK** Application/Zip stream.

**Python Usage:**

```python
import requests

file_hash = "7f3df..."
url = f"http://localhost:5000/api/v1/build/{file_hash}/source"

response = requests.get(url, stream=True)
if response.status_code == 200:
    with open("source.zip", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
else:
    print(response.text)

```

---

# Implant Operations

For various actions around Implants.


### Get All Implants

**HTTP Method:** `GET`

**Path:** `/implants/`

**Description:** Retrieve all implants the server knows about.

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **status** | string | HTTP Status code. |
| **data** | array | List of implants. |
| data[].**implant\_uuid** | string | Unique ID of the implant. |
| data[].**external\_ip** | string | External IP address. |
| data[].**internal\_ip** | string | Internal network IP. |
| data[].**user** | string | Username of process owner. |
| data[].**system\_hostname** | string | Hostname of target. |
| data[].**pid** | integer | Process ID. |
| data[].**process** | string | Process path/name. |
| data[].**arch** | string | Architecture (e.g., x64). |
| data[].**last\_checkin** | string | Last check-in timestamp (date-time). |
| data[].**sleep\_value** | integer | Sleep interval in seconds. |
| data[].**listener** | string | Associated listener name. |
| data[].**notes** | string | User notes. |

**Example Response:**

```json
{
  "data": [
    {
      "arch": "x64",
      "external_ip": "1.2.3.4",
      "implant_uuid": "019c6536-3ee4-719e-b432-fdbfef4440cc",
      "internal_ip": "192.168.1.50",
      "pid": 1234,
      "process": "notepad.exe",
      "system_hostname": "OFFENSIVE",
      "user": "ryan"
    }
  ],
  "message": "Success",
  "status": "200"
}

```

**Python Usage:**

```python
import requests
print(requests.get("http://localhost:5000/api/v1/implants/").json())

```

---

### Create Implant Entry

**HTTP Method:** `POST`

**Path:** `/implants/`

**Description:** Manually create a new implant entry. Returns an Implant ID.

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **data** | object | Creation details. |
| data.**uuid** | string | The UUID of the created implant. |

**Python Usage:**

```python
import requests
# Typically requires no body, just creates a placeholder/entry
print(requests.post("http://localhost:5000/api/v1/implants/").json())

```

---

### Search Implant History

**HTTP Method:** `POST`

**Path:** `/implants/history/search`

**Description:** Search for a task with fields that match the supplied term.

**Request Body:**

| Field Name | Type | Required | Description |
| --- | --- | --- | --- |
| **search\_term** | string | **Yes** | Term to search for. |

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **data** | array | List of matching tasks. |
| data[].**implant\_uuid** | string | Implant UUID. |
| data[].**task\_uuid** | string | Task UUID. |
| data[].**task\_name** | string | Name of the task. |

**Python Usage:**

```python
import requests
url = "http://localhost:5000/api/v1/implants/history/search"
print(requests.post(url, json={"search_term": "whoami"}).json())

```

---

### Search Implants

**HTTP Method:** `POST`

**Path:** `/implants/search`

**Description:** Search for an implant with fields that match the supplied term.

**Request Body:**

| Field Name | Type | Required | Description |
| --- | --- | --- | --- |
| **search\_term** | string | **Yes** | Term to search for. |

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **data** | array | List of matching implants. |
| data[].**implant\_uuid** | string | Implant UUID. |
| data[].**external\_ip** | string | External IP. |
| data[].**user** | string | User. |
| *(Other implant fields)* | ... | ... |

**Python Usage:**

```python
import requests
url = "http://localhost:5000/api/v1/implants/search"
print(requests.post(url, json={"search_term": "192.168"}).json())

```

---

### Get Single Implant

**HTTP Method:** `GET`

**Path:** `/implants/{uuid}`

**Description:** Retrieve a single implant by its unique ID.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Agent ID. |

**Responses:**

**200 OK** Returns single implant object (see "Get All Implants" for field list).

**Python Usage:**

```python
import requests
uuid = "019c..."
print(requests.get(f"http://localhost:5000/api/v1/implants/{uuid}").json())

```

---

### Update Implant

**HTTP Method:** `PUT`

**Path:** `/implants/{uuid}`

**Description:** Update a single implant's details by its unique ID.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Agent ID. |

**Request Body:**

| Field Name | Type | Required | Description |
| --- | --- | --- | --- |
| **external\_ip** | string | No | External IP address. |
| **internal\_ip** | string | No | Internal IP address. |
| **listener** | string | No | Listener address. |
| **user** | string | No | User account name. |
| **system\_hostname** | string | No | Hostname. |
| **notes** | string | No | Operator notes. |
| **process** | string | No | Process name. |
| **pid** | integer | No | Process ID. |
| **arch** | string | No | CPU architecture. |
| **last\_checkin** | string | No | Last check-in time (unix string). |
| **sleep\_value** | integer | No | Sleep interval. |

**Example Request:**

```json
{
  "notes": "Compromised DC",
  "sleep_value": 30
}

```

**Responses:**
**200 OK** (Success message).

**Python Usage:**

```python
import requests
uuid = "019c..."
url = f"http://localhost:5000/api/v1/implants/{uuid}"
requests.put(url, json={"notes": "Updated note"})

```

---

### Delete Implant

**HTTP Method:** `DELETE`

**Path:** `/implants/{uuid}`

**Description:** Delete a single implant by its unique ID.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Agent ID. |

**Responses:**
**200 OK** (Success message).

**Python Usage:**

```python
import requests
requests.delete(f"http://localhost:5000/api/v1/implants/{uuid}")

```

---

### Task Implant

**HTTP Method:** `POST`

**Path:** `/implants/{uuid}/task`

**Description:** Add a task (queue a command) to a single implant by its unique ID.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Agent ID. |

**Request Body:**

| Field Name | Type | Required | Description |
| --- | --- | --- | --- |
| **implant\_uuid** | string | **Yes** | Target implant ID. |
| **task\_uuid** | string | No | Optional UUID for the task. |
| **task** | object | **Yes** | Task definition object. |
| task.**task\_name** | string | **Yes** | Name of the command (e.g., "cmd"). |
| task.**args** | object | No | Dictionary of arguments (e.g., `{"cli": "whoami"}`). |

**Example Request:**

```json
{
  "implant_uuid": "019c6536...",
  "task": {
    "task_name": "cmd",
    "args": {
      "cli": "whoami"
    }
  }
}

```

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **data** | object | Task result. |
| data.**task\_uuid** | string | The unique ID of the queued task. |

**Python Usage:**

```python
import requests
uuid = "019c..."
url = f"http://localhost:5000/api/v1/implants/{uuid}/task"

payload = {
    "implant_uuid": uuid,
    "task": {
        "task_name": "cmd",
        "args": {"cli": "dir"}
    }
}
print(requests.post(url, json=payload).json())

```

---

### Peek Implant Tasks

**HTTP Method:** `GET`

**Path:** `/implants/{uuid}/tasks`

**Description:** Peeks all currently queued tasks of an implant (does not remove them).

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Agent ID. |

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **data** | array | List of tasks. |
| data[].**task** | string | Base64 encoded task blob. |

**Python Usage:**

```python
import requests
print(requests.get(f"http://localhost:5000/api/v1/implants/{uuid}/tasks").json())

```

---

### Delete Implant Tasks

**HTTP Method:** `DELETE`

**Path:** `/implants/{uuid}/tasks`

**Description:** Delete all the currently queued tasks of an agent (clear queue).

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Agent ID. |

**Responses:**
**200 OK** (Success message).

**Python Usage:**

```python
import requests
requests.delete(f"http://localhost:5000/api/v1/implants/{uuid}/tasks")

```

---

### Get Implant Task History

**HTTP Method:** `GET`

**Path:** `/implants/{uuid}/tasks/history`

**Description:** Gets ALL history of an implant from the DB.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Agent ID. |

**Query Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **since** | string | No | Return tasks with task_uuid greater than this UUIDv7. |

**Responses:**
**200 OK** (Returns list of implant objects/history).

**Python Usage:**

```python
import requests
# Optional: ?since=...
print(requests.get(f"http://localhost:5000/api/v1/implants/{uuid}/tasks/history").json())

```

---

# Listener Operations

For various actions around Listeners.


### Get All Listeners

**HTTP Method:** `GET`

**Path:** `/listeners/`

**Description:** Retrieve all listeners in the DB.

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **data** | array | List of listeners. |
| data[].**listener\_uuid** | string | Unique ID. |
| data[].**listener\_name** | string | User-defined name. |
| data[].**listener\_type** | string | Protocol type (http, etc). |
| data[].**listener\_host** | string | IP or DNS host. |
| data[].**listener\_port** | integer | Port number. |
| data[].**listener\_active** | boolean | Is listener running? |
| data[].**listener\_notes** | string | Optional notes. |
| data[].**listener\_profile_name** | string | Profile filename. |
| data[].**listener\_profile_contents** | string | Malleable C2 profile text. |

**Python Usage:**

```python
import requests
print(requests.get("http://localhost:5000/api/v1/listeners/").json())

```

---

### Spawn Listener

**HTTP Method:** `POST`

**Path:** `/listeners/`

**Description:** Create and spawn a new listener. Returns a listener ID.

**Request Body:**

| Field Name | Type | Required | Description |
| --- | --- | --- | --- |
| **listener\_host** | string | **Yes** | Host to listen on (DNS or IP). |
| **listener\_name** | string | **Yes** | Name of listener. |
| **listener\_profile\_contents** | string | **Yes** | Malleable C2 profile contents. |
| **listener\_profile_name** | string | **Yes** | Malleable C2 profile name. |
| **listener\_type** | string | **Yes** | Type of listener (e.g., "http"). |
| **listener\_port** | integer | No | Port to spawn on. |
| **listener\_notes** | string | No | Notes. |

**Example Request:**

```json
{
  "listener_host": "10.0.0.30",
  "listener_name": "http_one",
  "listener_type": "http",
  "listener_port": 8080,
  "listener_profile_name": "default",
  "listener_profile_contents": "..."
}

```

**Responses:**

**200 OK**

| Field Name | Type | Description |
| --- | --- | --- |
| **data** | object | Created listener details. |
| data.**listener\_uuid** | string | Listener UUID. |
| data.**listener\_active** | boolean | Active status. |

**Python Usage:**

```python
import requests
url = "http://localhost:5000/api/v1/listeners/"
payload = {
    "listener_host": "127.0.0.1",
    "listener_name": "dev_http",
    "listener_type": "http",
    "listener_port": 8080,
    "listener_profile_name": "default",
    "listener_profile_contents": "set sleeptime '5000';"
}
print(requests.post(url, json=payload).json())

```

---

### Get Single Listener

**HTTP Method:** `GET`

**Path:** `/listeners/{uuid}`

**Description:** Retrieve a single listener by its unique ID.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Listener ID (uuid). |

**Responses:**
**200 OK** (Returns single listener object).

**Python Usage:**

```python
import requests
uuid = "019c..."
print(requests.get(f"http://localhost:5000/api/v1/listeners/{uuid}").json())

```

---

### Stop/Delete Listener

**HTTP Method:** `DELETE`

**Path:** `/listeners/{uuid}`

**Description:** Stops/Deletes one listener based on user supplied ID.

**Path Parameters:**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| **uuid** | string | **Yes** | Listener ID (uuid). |

**Responses:**
**200 OK** (Success message).

**Python Usage:**

```python
import requests
requests.delete(f"http://localhost:5000/api/v1/listeners/{uuid}")

```