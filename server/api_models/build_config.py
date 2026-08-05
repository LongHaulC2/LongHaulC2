from flask_restx import fields

from ..instance import api
from .profile import wrap_response_empty, wrap_response_list, wrap_response_single

BUILD_CONFIG_LIST_ITEM_MODEL = api.model(
    "BUILD_CONFIG_LIST_ITEM_MODEL",
    {
        "artifact_uuid": fields.String(description="UUID of the build config"),
        "artifact_name": fields.String(description="Build config name", example="default_win64"),
        "content_hash": fields.String(description="SHA256 of config contents"),
        "created_at": fields.Integer(description="Creation time (epoch ms)"),
        "updated_at": fields.Integer(description="Last update time (epoch ms)"),
    },
)
BUILD_CONFIG_LIST_RESPONSE = wrap_response_list(api, BUILD_CONFIG_LIST_ITEM_MODEL)

BUILD_CONFIG_GET_MODEL = api.model(
    "BUILD_CONFIG_GET_MODEL",
    {
        "artifact_uuid": fields.String(description="UUID of the build config"),
        "artifact_name": fields.String(description="Build config name"),
        "artifact_contents": fields.String(description="Full JSON of the build config"),
        "content_hash": fields.String(description="SHA256 of config contents"),
        "created_at": fields.Integer(description="Creation time (epoch ms)"),
        "updated_at": fields.Integer(description="Last update time (epoch ms)"),
    },
)
BUILD_CONFIG_GET_RESPONSE = wrap_response_single(api, BUILD_CONFIG_GET_MODEL)

BUILD_CONFIG_UPLOAD_INPUT = api.model(
    "BUILD_CONFIG_UPLOAD_INPUT",
    {
        "config_name": fields.String(required=True, description="Build config name", example="default_win64"),
        "config_contents": fields.String(required=True, description="JSON string of the build configuration"),
    },
)
BUILD_CONFIG_UPLOAD_RESPONSE = wrap_response_single(api, BUILD_CONFIG_LIST_ITEM_MODEL)

BUILD_CONFIG_DELETE_RESPONSE = wrap_response_empty(api, "BUILD_CONFIG_DELETE_RESPONSE")
