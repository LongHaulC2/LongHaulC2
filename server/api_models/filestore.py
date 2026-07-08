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
# Class: File
# Routes: GET /, POST /
######################################################################

# get - and waht it returns
FILE_GET_MODEL = api.model(
    "FILE_GET_MODEL",
    {
        "file_uuid": fields.String(
            example="00000000-0000-0000-0000-000000000000",
            description="The UUID of the file",
        ),
        "file_name": fields.String(
            example="myfile_.exe",
            description="The name of the file",
        ),
        "file_hash": fields.String(
            example="7f3df637f39704c04d49d12906407ce8",
            description="The MD5 hash of the file.",
        ),
        "uploaded_by": fields.String(
            example="longhaul",
            description="Operator username or implant:<uuid>",
        ),
        "uploaded_at": fields.Integer(
            example=1720000000000,
            description="Upload timestamp in milliseconds since epoch",
        ),
        "source_implant": fields.String(
            example="00000000-0000-0000-0000-000000000000",
            description="Implant UUID if file came from a download",
        ),
    },
)
FILE_GET_RESPONSE = wrap_response_list(api, FILE_GET_MODEL)


# post INPUT
FILE_POST_INPUT = api.model(
    "FILE_POST_INPUT",
    {
        "file_name": fields.String(required=True, description="Name of the file", example="some_file_.exe"),
        "file_contents": fields.String(required=True, description="base64 encoded file data", example="aabbcc=="),
    },
)


# POST response for filestore/
FILE_POST_MODEL = api.model(
    "FILE_POST_MODEL",
    {
        "file_uuid": fields.String(
            example="00000000-0000-0000-0000-000000000000",
            description="The UUID of the file",
        ),
    },
)
FILE_POST_RESPONSE = wrap_response_single(api, FILE_POST_MODEL)


######################################################################
# Class: FileActions
# Routes: DELETE /<UUID>
######################################################################

# DELETE /<hash>
FILEACTIONS_DELETE_RESPONSE = wrap_response_empty(api, "BINARYACTIONS_DELETE_RESPONSE")
