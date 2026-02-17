from flask_restx import Namespace, Resource, fields

from ..instance import api

# The task model, direct from DB
DB_IMPLANT_TASK_MODEL = api.model(
    "ImplantTask",
    {
        "implant_uuid": fields.String(
            description="UUID of the target implant",
            example="019c6536-3ee4-719e-b432-fdbfef4440cc",
        ),
        "task_uuid": fields.String(
            description="Unique identifier for the task",
            example="019c6b12-8850-7378-a931-387b089b3d4a",
        ),
        "task_request": fields.Raw(
            description="The dynamic JSON task request sent to the implant",
            example={"task_name": "shell", "args": {"cli": "whoami"}},
            allow_null=True,
        ),
        "task_response": fields.Raw(
            description="The dynamic JSON response received from the implant",
            example={"status": "success", "output": "root"},
            allow_null=True,
        ),
        # Optional: Include these if you want to expose the indexed text versions
        "task_request_text": fields.String(readonly=True),
        "task_response_text": fields.String(readonly=True),
    },
)
