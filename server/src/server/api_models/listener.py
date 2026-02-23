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
            "data": fields.List(fields.Nested(inner_model)),
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
    return api.model(
        model_name,
        {
            "data": fields.String(example="", description="No data returned", default=None),
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


######################################################################
# Class: Listener
# Routes: GET /<uuid>, DELETE /<uuid>, PATCH /<uuid>
######################################################################

# --- GET /<uuid> ---
LISTENER_GET_MODEL = api.model(
    "LISTENER_GET_MODEL",
    {
        "listener_active": fields.Boolean(description="Whether the listener is currently running", example=True),
        "listener_host": fields.String(description="The IP or DNS host the listener binds to", example="10.0.0.30"),
        "listener_name": fields.String(description="User-defined name for the listener", example="amazon_prod"),
        "listener_notes": fields.String(description="Optional notes about the listener", example="Main HTTP egress"),
        "listener_port": fields.Integer(description="Port number", example=9090),
        "listener_profile_contents": fields.String(
            description="The full Malleable C2 profile configuration text",
            example="set sleeptime '5000'; ...",
        ),
        "listener_profile_name": fields.String(description="The filename of the profile", example="amazon.profile"),
        "listener_type": fields.String(description="Protocol type (http, https, etc)", example="http"),
        "listener_uuid": fields.String(
            description="Unique identifier for the listener",
            example="019c67f6-4e24-789a-800f-473a4c70e4f2",
        ),
    },
)
LISTENER_GET_RESPONSE = wrap_response_single(api, LISTENER_GET_MODEL)


# --- DELETE /<uuid> ---
LISTENER_DELETE_RESPONSE = wrap_response_empty(api, "LISTENER_DELETE_RESPONSE")


# --- PATCH /<uuid> ---
LISTENER_PATCH_RESPONSE = wrap_response_empty(api, "LISTENER_PATCH_RESPONSE")

######################################################################
# Class: Listeners
# Routes: GET /, POST /
######################################################################

# --- GET / ---
LISTENERS_GET_MODEL = api.model(
    "LISTENERS_GET_MODEL",
    {
        "listener_active": fields.Boolean(example=True),
        "listener_host": fields.String(example="10.0.0.30"),
        "listener_name": fields.String(example="aaa"),
        "listener_notes": fields.String(example=""),
        "listener_port": fields.Integer(example=9090),
        "listener_profile_contents": fields.String(description="Malleable C2 Profile Text"),
        "listener_profile_name": fields.String(example="amazon.profile"),
        "listener_type": fields.String(example="http"),
        "listener_uuid": fields.String(example="019c67f6-4e24-789a-800f-473a4c70e4f2"),
    },
)
LISTENERS_GET_RESPONSE = wrap_response_list(api, LISTENERS_GET_MODEL)


# --- POST / ---
LISTENERS_POST_INPUT = api.model(
    "LISTENERS_POST_INPUT",
    {
        "listener_host": fields.String(
            required=True,
            description="Host the listener will listen on (DNS Host, or IP address)",
        ),
        "listener_port": fields.Integer(required=False, description="Port to spawn the listener on"),
        "listener_type": fields.String(required=True, description="What type of listener to spawn"),
        "listener_name": fields.String(required=True, description="Name of listener"),
        "listener_notes": fields.String(required=False, description="Listener notes"),
        "listener_profile_name": fields.String(required=True, description="Listener malleable c2 profile name"),
        "listener_profile_contents": fields.String(required=True, description="Listener malleable c2 profile contents"),
    },
)

# Returns the created listener object
LISTENERS_POST_MODEL = api.model(
    "LISTENERS_POST_MODEL",
    {
        "listener_uuid": fields.String(example="019c67f6-4e24-789a-800f-473a4c70e4f2"),
        "listener_active": fields.Boolean(example=True),
        "listener_host": fields.String(example="10.0.0.30"),
        "listener_name": fields.String(example="aaa"),
        "listener_port": fields.Integer(example=9090),
        "listener_type": fields.String(example="http"),
    },
)
LISTENERS_POST_RESPONSE = wrap_response_single(api, LISTENERS_POST_MODEL)
