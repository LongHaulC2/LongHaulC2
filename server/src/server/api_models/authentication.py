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
    return api.model(
        model_name,
        {
            "message": fields.String(example="Success"),
            "status": fields.String(example="200"),
        },
    )


######################################################################
# Class: Auth / Register
# Routes: POST /, POST /register
######################################################################

# Input Model (Shared by both Login and Register endpoints)
AUTH_POST_INPUT = api.model(
    "AUTH_POST_INPUT",
    {
        "username": fields.String(required=True, description="The operator's username", example="operator_admin"),
        "password": fields.String(
            required=True, description="The operator's password", example="SuperSecretPassword123!"
        ),
    },
)

# POST / (Login) Response Model
AUTH_LOGIN_MODEL = api.model(
    "AUTH_LOGIN_MODEL",
    {
        "access_token": fields.String(
            description="JWT Access Token for authenticating future API requests",
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
        "refresh_token": fields.String(
            description="JWT refresh token for getting new access tokens",
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
    },
)

# Wrapped Responses
AUTH_LOGIN_RESPONSE = wrap_response_single(api, AUTH_LOGIN_MODEL)
AUTH_REGISTER_RESPONSE = wrap_response_empty(api, "AUTH_REGISTER_RESPONSE")
