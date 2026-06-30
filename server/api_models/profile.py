from flask_restx import fields

from ..instance import api


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


def wrap_response_list(api, inner_model):
    name = f"{inner_model.name}ListWrapper"
    return api.model(
        name,
        {
            "data": fields.List(fields.Nested(inner_model), default=[]),
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
# Shared
######################################################################

PROFILE_TRANSFORM_STEP_MODEL = api.model(
    "PROFILE_TRANSFORM_STEP_MODEL",
    {
        "op": fields.String(description="Transform operation name", example="base64"),
        "val": fields.String(
            description="Optional value for the operation (e.g. prepend/append string)",
            allow_null=True,
            example="session=",
        ),
        "result_display": fields.String(
            description="Data after this step — UTF-8 string or hex if binary", example="UFJFVKLFY19QQVlMT0FE"
        ),
    },
)

######################################################################
# SMB
######################################################################

PROFILE_SMB_MODEL = api.model(
    "PROFILE_SMB_MODEL",
    {
        "inbox_pipe_name": fields.String(description="SMB named pipe for inbound tasks", example="inbox"),
        "outbox_pipe_name": fields.String(description="SMB named pipe for outbound responses", example="outbox"),
    },
)

######################################################################
# RAW GET / POST
######################################################################

PROFILE_RAW_GET_CLIENT_MODEL = api.model(
    "PROFILE_RAW_GET_CLIENT_MODEL",
    {
        "body": fields.String(description="Wire body template (contains <METADATA> token)", example="<METADATA>"),
        "metadata_token_location": fields.String(description="Always 'body' for raw profiles", example="body"),
        "metadata_transforms": fields.List(
            fields.Nested(PROFILE_TRANSFORM_STEP_MODEL),
            description="Step-by-step transform chain applied to beacon metadata before wire send",
        ),
    },
)

PROFILE_RAW_GET_SERVER_MODEL = api.model(
    "PROFILE_RAW_GET_SERVER_MODEL",
    {
        "body": fields.String(
            description="Server response body template (contains <OUTPUT> token)", example="<OUTPUT>"
        ),
        "output_transforms": fields.List(
            fields.Nested(PROFILE_TRANSFORM_STEP_MODEL),
            description="Step-by-step transform chain applied to server task output",
        ),
    },
)

PROFILE_RAW_GET_MODEL = api.model(
    "PROFILE_RAW_GET_MODEL",
    {
        "proto": fields.String(description="Socket protocol", example="tcp", enum=["tcp", "udp"]),
        "client": fields.Nested(PROFILE_RAW_GET_CLIENT_MODEL),
        "server": fields.Nested(PROFILE_RAW_GET_SERVER_MODEL),
    },
)

PROFILE_RAW_POST_CLIENT_MODEL = api.model(
    "PROFILE_RAW_POST_CLIENT_MODEL",
    {
        "body": fields.String(description="Wire body template (contains <OUTPUT> token)", example="<OUTPUT>"),
        "output_token_location": fields.String(description="Always 'body' for raw profiles", example="body"),
        "output_transforms": fields.List(
            fields.Nested(PROFILE_TRANSFORM_STEP_MODEL),
            description="Step-by-step transform chain applied to exfil output before wire send",
        ),
        "id_transforms": fields.List(
            fields.Nested(PROFILE_TRANSFORM_STEP_MODEL),
            description="Step-by-step transform chain applied to implant ID",
        ),
    },
)

PROFILE_RAW_POST_SERVER_MODEL = api.model(
    "PROFILE_RAW_POST_SERVER_MODEL",
    {
        "body": fields.String(description="Server ACK body template", example=""),
        "output_transforms": fields.List(
            fields.Nested(PROFILE_TRANSFORM_STEP_MODEL),
            description="Step-by-step transform chain applied to server ACK output",
        ),
    },
)

PROFILE_RAW_POST_MODEL = api.model(
    "PROFILE_RAW_POST_MODEL",
    {
        "proto": fields.String(description="Socket protocol", example="tcp", enum=["tcp", "udp"]),
        "client": fields.Nested(PROFILE_RAW_POST_CLIENT_MODEL),
        "server": fields.Nested(PROFILE_RAW_POST_SERVER_MODEL),
    },
)

PROFILE_RAW_ENTRY_MODEL = api.model(
    "PROFILE_RAW_ENTRY_MODEL",
    {
        "name": fields.String(
            description="Sub-profile name ('default' for top-level [raw.*], or the named key e.g. 'ntp')",
            example="default",
        ),
        "get": fields.Nested(PROFILE_RAW_GET_MODEL, allow_null=True),
        "post": fields.Nested(PROFILE_RAW_POST_MODEL, allow_null=True),
    },
)

######################################################################
# Validation
######################################################################

PROFILE_VALIDATION_MODEL = api.model(
    "PROFILE_VALIDATION_MODEL",
    {
        "parse_ok": fields.Boolean(description="Whether the TOML parsed without error", example=True),
        "parse_error": fields.String(
            description="TOML parse error message if parse failed", allow_null=True, example=None
        ),
        "missing_fields": fields.List(fields.String(), description="Required fields absent from the profile"),
        "warnings": fields.List(fields.String(), description="Non-fatal issues detected in the profile"),
    },
)

######################################################################
# Top-level preview response
# Future protocols (e.g. NTP) are added as new nullable Nested fields here.
######################################################################

PROFILE_PREVIEW_DATA_MODEL = api.model(
    "PROFILE_PREVIEW_DATA_MODEL",
    {
        "profile_name": fields.String(description="Profile name from [profile] block", example="HTTP Mimicry"),
        "profile_author": fields.String(description="Profile author from [profile] block", example="@operator"),
        "smb": fields.Nested(PROFILE_SMB_MODEL, allow_null=True, description="SMB chaining pipe configuration"),
        "raw_profiles": fields.List(
            fields.Nested(PROFILE_RAW_ENTRY_MODEL),
            description="Raw socket profiles found in [raw.*] sections",
        ),
        "validation": fields.Nested(PROFILE_VALIDATION_MODEL, description="Parse status and detected issues"),
    },
)

######################################################################
# Input model
######################################################################

PROFILE_PREVIEW_INPUT = api.model(
    "PROFILE_PREVIEW_INPUT",
    {
        "profile_contents": fields.String(
            required=True,
            description="Raw TOML string of the network profile to preview",
            example='[profile]\nname = "Example"\n\n[raw.get]\nproto = "tcp"\nbody = "<METADATA>"',
        ),
    },
)

PROFILE_PREVIEW_RESPONSE = wrap_response_single(api, PROFILE_PREVIEW_DATA_MODEL)


######################################################################
# Profile CRUD models
######################################################################

PROFILE_LIST_ITEM_MODEL = api.model(
    "PROFILE_LIST_ITEM_MODEL",
    {
        "artifact_uuid": fields.String(description="UUID of the profile", example="019abc12-..."),
        "artifact_name": fields.String(description="Profile filename", example="raw_http_profile.toml"),
        "content_hash": fields.String(description="SHA256 of profile contents"),
        "created_at": fields.Integer(description="Creation time (epoch ms)"),
        "updated_at": fields.Integer(description="Last update time (epoch ms)"),
    },
)
PROFILE_LIST_RESPONSE = wrap_response_list(api, PROFILE_LIST_ITEM_MODEL)

PROFILE_UPLOAD_INPUT = api.model(
    "PROFILE_UPLOAD_INPUT",
    {
        "profile_name": fields.String(required=True, description="Profile filename", example="raw_http_profile.toml"),
        "profile_contents": fields.String(required=True, description="Raw TOML content of the profile"),
    },
)
PROFILE_UPLOAD_RESPONSE = wrap_response_single(api, PROFILE_LIST_ITEM_MODEL)

PROFILE_GET_MODEL = api.model(
    "PROFILE_GET_MODEL",
    {
        "artifact_uuid": fields.String(description="UUID of the profile"),
        "artifact_name": fields.String(description="Profile filename"),
        "artifact_contents": fields.String(description="Full TOML text of the profile"),
        "content_hash": fields.String(description="SHA256 of profile contents"),
        "created_at": fields.Integer(description="Creation time (epoch ms)"),
        "updated_at": fields.Integer(description="Last update time (epoch ms)"),
    },
)
PROFILE_GET_RESPONSE = wrap_response_single(api, PROFILE_GET_MODEL)

PROFILE_DELETE_RESPONSE = wrap_response_empty(api, "PROFILE_DELETE_RESPONSE")

PROFILE_SEED_ENTRY = api.model(
    "PROFILE_SEED_ENTRY",
    {
        "profile_name": fields.String(required=True, description="Profile filename"),
        "profile_contents": fields.String(required=True, description="Raw TOML content"),
    },
)
PROFILE_SEED_INPUT = api.model(
    "PROFILE_SEED_INPUT",
    {
        "profiles": fields.List(
            fields.Nested(PROFILE_SEED_ENTRY),
            required=True,
            description="List of profiles to seed",
        ),
    },
)
PROFILE_SEED_RESPONSE = wrap_response_single(
    api,
    api.model(
        "PROFILE_SEED_RESULT",
        {
            "created": fields.Integer(description="Number of new profiles created"),
            "unchanged": fields.Integer(description="Number of profiles already up to date"),
            "updated": fields.Integer(description="Number of profiles updated"),
        },
    ),
)
