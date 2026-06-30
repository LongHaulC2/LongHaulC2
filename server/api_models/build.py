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
# Class: Build
# Routes: GET /, POST /
######################################################################

# GET /
BUILD_GET_MODEL = api.model(
    "BUILD_GET_MODEL",
    {
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
            description="The MD5 hash of the Payload after it is build.",
        ),
        "payload_listener_uuids": fields.List(
            fields.String,
            description="Listener UUIDs (strategies) compiled into this payload",
            default=[],
        ),
    },
)
BUILD_GET_RESPONSE = wrap_response_list(api, BUILD_GET_MODEL)


# POST /
BUILD_POST_INPUT = api.model(
    "BUILD_POST_INPUT",
    {
        "implant_name": fields.String(required=True, description="Name of the implant", example="implant_one"),
        "output_format": fields.String(required=True, description="Output format (e.g., exe, bin)", example="exe"),
        "listener_uuids": fields.List(
            fields.String,
            required=True,
            description="The list of listener UUIDs that have their profiles compiled into the implant",
            example=[
                "0194fdc2-fa2f-4cc0-81d3-ff12045b3d33",
                "0194fdc2-fa2f-4cc0-81d3-ff12045b3d34",
            ],
        ),
        "initial_get_profile_listener_uuid": fields.String(
            description="UUID of listener for GET profile",
            example="019c...",
            required=True,
        ),
        "initial_post_profile_listener_uuid": fields.String(
            description="UUID of listener for POST profile",
            example="019c...",
            required=True,
        ),
        "options": fields.Nested(
            api.model(
                "BUILD_OPTIONS",
                {
                    "debug": fields.Boolean(
                        required=False, description="Build implant with debug logging", example=True, default=False
                    ),
                    "clear_cache": fields.Boolean(
                        required=False, description="Clear build cache before compiling", example=False, default=False
                    ),
                },
            ),
            required=False,
            description="Optional build configuration flags",
        ),
    },
)
BUILD_POST_STATS = api.model(
    "BUILD_POST_STATS",
    {
        "build_time": fields.Float(
            required=True, description="The build time for the payload, in seconds", example=6.7
        ),
    },
)
BUILD_POST_MODEL = api.model(
    "BUILD_POST_MODEL",
    {
        "build_uuid": fields.String(description="The UUID of the initiated build job", example="019c..."),
        "build_stats": fields.Nested(model=BUILD_POST_STATS, description="Stats related to the build job"),
    },
)
BUILD_POST_RESPONSE = wrap_response_single(api, BUILD_POST_MODEL)


######################################################################
# Class: BuildJobs
# Routes: GET /jobs/<uuid>
######################################################################

# GET /jobs/<uuid>
BUILDJOBS_GET_MODEL = api.model(
    "BUILDJOBS_GET_MODEL",
    {
        "build_uuid": fields.String(
            example="00000000-0000-0000-0000-000000000000",
            description="The UUID of the build",
        ),
        "build_status": fields.String(
            enum=["failed", "complete", "building"],
            example="complete",
            description="The status of the Payload building",
        ),
        "payload_name": fields.String(
            example="metadata_test",
            description="The name of the payload in the Database",
        ),
        "payload_hash": fields.String(
            example="7f3df637f39704c04d49d12906407ce8",
            description="The MD5 hash of the Payload.",
        ),
        "payload_listener_uuids": fields.List(
            fields.String,
            description="Listener UUIDs (strategies) compiled into this payload",
            default=[],
        ),
    },
)
BUILDJOBS_GET_RESPONSE = wrap_response_single(api, BUILDJOBS_GET_MODEL)


######################################################################
# Class: BinaryActions
# Routes: DELETE /<hash> (GET is binary stream)
######################################################################

# DELETE /<hash>
BINARYACTIONS_DELETE_RESPONSE = wrap_response_empty(api, "BINARYACTIONS_DELETE_RESPONSE")


######################################################################
# Class: SourceActions
# Routes: GET /<hash>/source
######################################################################

# No JSON models needed for file download endpoints
