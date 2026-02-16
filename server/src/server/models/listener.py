from flask_restx import Namespace, Resource, fields

from ..instance import api


###################
# Helpers
####################
# A helper func to include all the parent models
def wrap_response(api, inner_model):
    """
    Dynamically creates a wrapper model with 'data', 'message', and 'status'.
    The model name is generated automatically (e.g., 'BuildItemWrapper').
    """
    name = f"{inner_model.name}Wrapper"
    return api.model(
        name,
        {
            "data": fields.List(fields.Nested(inner_model)),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


###################
# Listener
####################

# inner response model for api
LISTENER_GET_RESPONSE_MODEL = api.model(
    "LISTENER_GET_RESPONSE_MODEL",
    {
        "listener_active": fields.Boolean(
            description="Whether the listener is currently running", example=True
        ),
        "listener_host": fields.String(
            description="The IP or DNS host the listener binds to", example="10.0.0.30"
        ),
        "listener_name": fields.String(
            description="User-defined name for the listener", example="amazon_prod"
        ),
        "listener_notes": fields.String(
            description="Optional notes about the listener", example="Main HTTP egress"
        ),
        "listener_port": fields.Integer(description="Port number", example=9090),
        "listener_profile_contents": fields.String(
            description="The full Malleable C2 profile configuration text",
            example="set sleeptime '5000'; ...",
        ),
        "listener_profile_name": fields.String(
            description="The filename of the profile", example="amazon.profile"
        ),
        "listener_type": fields.String(
            description="Protocol type (http, https, etc)", example="http"
        ),
        "listener_uuid": fields.String(
            description="Unique identifier for the listener",
            example="019c67f6-4e24-789a-800f-473a4c70e4f2",
        ),
    },
)
LISTENER_GET_SUCCESS_MODEL = wrap_response(api, LISTENER_GET_RESPONSE_MODEL)

# DELETE
LISTENER_DELETE_SUCCESS_MODEL = api.model(
    "LISTENER_DELETE_RESPONSE_MODEL",
    {
        "status": fields.String(example="200"),
        "message": fields.String(example="Success"),
        "data": fields.String(example="", description="No data returned"),
    },
)
