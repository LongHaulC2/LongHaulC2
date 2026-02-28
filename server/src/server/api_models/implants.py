from flask_restx import fields

from ..instance import api


###################
# Helpers
####################
def wrap_response_list(api, inner_model):
    name = f"{inner_model.name}Wrapper"
    return api.model(
        name,
        {
            "data": fields.List(fields.Nested(inner_model), default=[]),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


def wrap_response_single(api, inner_model):
    name = f"{inner_model.name}Wrapper"
    return api.model(
        name,
        {
            "data": fields.Nested(inner_model, default={}),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


def wrap_response_empty(api, model_name):
    """For responses that just return status/message (DELETE, PUT)"""
    return api.model(
        model_name,
        {
            "data": fields.String(example="", description="No data returned", default=""),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


######################################################################
# Class: Implants
# Routes: GET /, POST /
######################################################################

# GET / (List)
IMPLANTS_GET_MODEL = api.model(
    "IMPLANTS_GET_MODEL",
    {
        "arch": fields.String(description="Architecture", example="x64", allow_null=True),
        "external_ip": fields.String(description="External IP address", example="1.2.3.4", allow_null=True),
        "implant_uuid": fields.String(
            description="Unique ID of the implant",
            example="019c6536-3ee4-719e-b432-fdbfef4440cc",
        ),
        "internal_ip": fields.String(description="Internal network IP", example="192.168.1.50", allow_null=True),
        "last_checkin": fields.Integer(description="Last check-in timestamp", example=None, allow_null=True),
        "listener": fields.String(
            description="Associated listener name",
            example="http_listener",
            allow_null=True,
        ),
        "notes": fields.String(description="User notes", example="placeholder", allow_null=True),
        "pid": fields.Integer(description="Process ID", example=1234, allow_null=True),
        "process": fields.String(description="Process path or name", example="notepad.exe", allow_null=True),
        "sleep_value": fields.Integer(description="Sleep interval in seconds", example=None, allow_null=True),
        "system_hostname": fields.String(description="Hostname of the target", example="OFFENSIVE", allow_null=True),
        "user": fields.String(description="Username of the process owner", example="ryan", allow_null=True),
    },
)
IMPLANTS_GET_RESPONSE = wrap_response_list(api, IMPLANTS_GET_MODEL)


# POST / (Create)
IMPLANTS_POST_MODEL = api.model(
    "IMPLANTS_POST_MODEL",
    {
        "uuid": fields.String(
            description="The UUID of the created implant",
            example="00000000-0000-0000-0000-000000000000",
        ),
    },
)
IMPLANTS_POST_RESPONSE = wrap_response_single(api, IMPLANTS_POST_MODEL)


######################################################################
# Class: Implant
# Routes: GET /<uuid>, PUT /<uuid>, DELETE /<uuid>
######################################################################

# GET /<uuid>
IMPLANT_GET_MODEL = api.model(
    "IMPLANT_GET_MODEL",
    {
        "arch": fields.String(description="Architecture", example="x64", allow_null=True),
        "external_ip": fields.String(description="External IP address", example="1.2.3.4", allow_null=True),
        "implant_uuid": fields.String(
            description="Unique ID of the implant",
            example="019c6536-3ee4-719e-b432-fdbfef4440cc",
        ),
        "internal_ip": fields.String(description="Internal network IP", example="192.168.1.50", allow_null=True),
        "last_checkin": fields.Integer(description="Last check-in timestamp", example=None, allow_null=True),
        "listener": fields.String(
            description="Associated listener name",
            example="http_listener",
            allow_null=True,
        ),
        "notes": fields.String(description="User notes", example="placeholder", allow_null=True),
        "pid": fields.Integer(description="Process ID", example=1234, allow_null=True),
        "process": fields.String(description="Process path or name", example="notepad.exe", allow_null=True),
        "sleep_value": fields.Integer(description="Sleep interval in seconds", example=None, allow_null=True),
        "system_hostname": fields.String(description="Hostname of the target", example="OFFENSIVE", allow_null=True),
        "user": fields.String(description="Username of the process owner", example="ryan", allow_null=True),
    },
)
IMPLANT_GET_RESPONSE = wrap_response_single(api, IMPLANT_GET_MODEL)


# PUT /<uuid>
IMPLANT_PUT_INPUT = api.model(
    "IMPLANT_PUT_INPUT",
    {
        "external_ip": fields.String(description="External IP address", example="203.0.113.10", required=False),
        "internal_ip": fields.String(description="Internal IP address", example="10.0.0.15", required=False),
        "listener": fields.String(description="Listener address", example="c2.example.com:443", required=False),
        "user": fields.String(description="User account name", example="SYSTEM", required=False),
        "system_hostname": fields.String(description="Hostname", example="WIN-ABC123", required=False),
        "notes": fields.String(description="Operator notes", example="Initial check-in", required=False),
        "process": fields.String(description="Process name", example="svchost.exe", required=False),
        "pid": fields.Integer(description="Process ID", example=1234, required=False),
        "arch": fields.String(description="CPU architecture", example="x64", required=False),
        "last_checkin": fields.Integer(description="Last check-in time (unix)", example=11223344, required=False),
        "sleep_value": fields.Integer(description="Sleep interval", example=60, required=False),
    },
)
IMPLANT_PUT_RESPONSE = wrap_response_empty(api, "IMPLANT_PUT_RESPONSE")


# DELETE /<uuid>
IMPLANT_DELETE_RESPONSE = wrap_response_empty(api, "IMPLANT_DELETE_RESPONSE")


######################################################################
# Class: ImplantTask
# Routes: POST /<uuid>/task
######################################################################

# POST /<uuid>/task
# Internal model for the nested task dictionary
IMPLANT_TASK_POST_INTERNAL_MODEL = api.model(
    "IMPLANT_TASK_POST_INTERNAL_MODEL",
    {
        "task_name": fields.String(required=True, description="Name of the command", example="cmd"),
        "args": fields.Raw(description="Dictionary of arguments", example={"cli": "whoami"}),
    },
)

# The expected input body
IMPLANT_TASK_POST_INPUT = api.model(
    "IMPLANT_TASK_POST_INPUT",
    {
        "task_uuid": fields.String(description="Optional UUID for the task", example="019c6b12..."),
        "implant_uuid": fields.String(required=True, description="Target implant ID", example="019c6536..."),
        "task": fields.Nested(
            IMPLANT_TASK_POST_INTERNAL_MODEL,
            required=True,
            description="Task definition",
        ),
    },
)

# The response data
IMPLANT_TASK_POST_MODEL = api.model(
    "IMPLANT_TASK_POST_MODEL",
    {"task_uuid": fields.String(description="The unique ID of the queued task", example="019c6b12-...")},
)
IMPLANT_TASK_POST_RESPONSE = wrap_response_single(api, IMPLANT_TASK_POST_MODEL)


######################################################################
# Class: ImplantTasks
# Routes: GET /<uuid>/tasks, DELETE /<uuid>/tasks
######################################################################

# GET /<uuid>/tasks (Peek)
IMPLANT_TASKS_GET_MODEL = api.model(
    "IMPLANT_TASKS_GET_MODEL",
    {
        "task": fields.String(description="Base64 encoded task blob", example="AABBCC..."),
    },
)
IMPLANT_TASKS_GET_RESPONSE = wrap_response_list(api, IMPLANT_TASKS_GET_MODEL)


# DELETE /<uuid>/tasks (Clear)
IMPLANT_TASKS_DELETE_RESPONSE = wrap_response_empty(api, "IMPLANT_TASKS_DELETE_RESPONSE")


######################################################################
# Class: ImplantHistory
# Routes: GET /<uuid>/tasks/history
######################################################################

# GET /<uuid>/tasks/history
# Defining a generic task structure for history.
# You can expand this based on what MySQLImplantTaskService actually returns.
IMPLANT_HISTORY_GET_MODEL = api.model(
    "IMPLANT_HISTORY_GET_MODEL",
    {
        "implant_uuid": fields.String(example="019c6536..."),
        "task_uuid": fields.String(example="019b46f8..."),
        "task_request": fields.Raw(description="JSON of the request"),
        "task_response": fields.Raw(description="JSON of the response", allow_null=True),
    },
)
IMPLANT_HISTORY_GET_RESPONSE = wrap_response_list(
    api, IMPLANT_HISTORY_GET_MODEL
)  # Note: Using generic list wrapper for now


######################################################################
# Class: ImplantSearch
# Routes: POST /search
######################################################################

# POST /search
IMPLANT_SEARCH_POST_INPUT = api.model(
    "IMPLANT_SEARCH_POST_INPUT",
    {
        "search_term": fields.String(required=True, description="Term to search for."),
    },
)

IMPLANT_SEARCH_POST_MODEL = api.model(
    "IMPLANT_SEARCH_POST_MODEL",
    {
        "implant_uuid": fields.String(example="019c6536..."),
        "external_ip": fields.String(example="203.0.113.42"),
        "internal_ip": fields.String(example="192.168.1.15"),
        "listener": fields.String(example="c2.example.com"),
        "user": fields.String(example="SYSTEM"),
        "system_hostname": fields.String(example="DESKTOP"),
        "notes": fields.String(example="Initial access"),
        "process": fields.String(example="svchost.exe"),
        "pid": fields.Integer(example=4216),
        "arch": fields.String(example="x64"),
        "last_checkin": fields.Integer(example=1739742373),
        "sleep_value": fields.Integer(example=60),
    },
)

IMPLANT_SEARCH_POST_RESPONSE = wrap_response_list(api, IMPLANT_SEARCH_POST_MODEL)


######################################################################
# Class: TaskSearch
# Routes: POST /history/search
######################################################################

# POST /history/search
TASK_SEARCH_POST_INPUT = api.model(
    "TASK_SEARCH_POST_INPUT",
    {
        "search_term": fields.String(required=True, description="Term to search for."),
    },
)

# Assuming task search returns similar objects to history or simplified task objects
TASK_SEARCH_POST_MODEL = api.model(
    "TASK_SEARCH_POST_MODEL",
    {
        "implant_uuid": fields.String(example="019c6536..."),
        "task_uuid": fields.String(example="019b46f8..."),
        "task_name": fields.String(example="cmd"),
        # Add other fields returned by MySQLSearchService.search_tasks
    },
)

TASK_SEARCH_POST_RESPONSE = wrap_response_list(api, TASK_SEARCH_POST_MODEL)
