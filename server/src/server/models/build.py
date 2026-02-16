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
# Build
####################
# teh model for the specific endpoint
# do classname_method_MODEL
BUILD_GET_MODEL = api.model(
    "BuildItem",
    {
        # "id": fields.Integer(
        #     example=1,
        # ), # exclude id, the marshall will keep this out. TLDR, internal tracking id for the DB as the prim key.
        "build_uuid": fields.String(
            example="00000000-0000-0000-0000-000000000000",
            description="The UUID of the build",
        ),
        "build_status": fields.String(
            enum=["failed", "complete", "building"],
            example="failed",
            default="building",
            description="The status of the Payload building",
        ),
        "payload_name": fields.String(
            example="metadata_test",
            description="The name of the payload in the Database",
        ),
        "payload_hash": fields.String(
            example="7f3df637f39704c04d49d12906407ce8",
            description="The MD5 hash of the Payload after it is build. This is initially blank, and filled in when the payload has been successfully compiled.",
        ),
    },
)
# then add them here
# do classname_method
BUILD_GET = wrap_response(api, BUILD_GET_MODEL)

###################
# BuildJobs
####################

BUILDJOBS_GET_MODEL = api.model(
    "BuildStatus",
    {
        # "id": fields.Integer(
        #     example=1,
        # ), # exclude id, the marshall will keep this out. TLDR, internal tracking id for the DB as the prim key.
        "build_uuid": fields.String(
            example="00000000-0000-0000-0000-000000000000",
            description="The UUID of the build",
        ),
        "build_status": fields.String(
            enum=["failed", "complete", "building"],
            example="failed",
            default="building",
            description="The status of the Payload building",
        ),
        "payload_name": fields.String(
            example="metadata_test",
            description="The name of the payload in the Database",
        ),
        "payload_hash": fields.String(
            example="7f3df637f39704c04d49d12906407ce8",
            description="The MD5 hash of the Payload after it is build. This is initially blank, and filled in when the payload has been successfully compiled.",
        ),
    },
)

###################
# BinaryActions
####################
BINARYACTIONS_DELETE_SUCCESS_MODEL = api.model(
    "SuccessResponse",
    {
        "status": fields.String(example="200"),
        "message": fields.String(example="Success"),
        "data": fields.String(example="", description="No data returned"),
    },
)


###################
# SourceActions
####################
# none needed
