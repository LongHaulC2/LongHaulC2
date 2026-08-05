from flask_restx import fields

from ..instance import api
from .profile import wrap_response_empty, wrap_response_list, wrap_response_single

MODULE_LIST_ITEM_MODEL = api.model(
    "MODULE_LIST_ITEM_MODEL",
    {
        "artifact_uuid": fields.String(description="UUID of the module"),
        "artifact_name": fields.String(description="Module name", example="ls"),
        "content_hash": fields.String(description="SHA256 of module contents"),
        "created_at": fields.Integer(description="Creation time (epoch ms)"),
        "updated_at": fields.Integer(description="Last update time (epoch ms)"),
    },
)
MODULE_LIST_RESPONSE = wrap_response_list(api, MODULE_LIST_ITEM_MODEL)

MODULE_GET_MODEL = api.model(
    "MODULE_GET_MODEL",
    {
        "artifact_uuid": fields.String(description="UUID of the module"),
        "artifact_name": fields.String(description="Module name"),
        "artifact_contents": fields.String(description="Full JSON bundle of the module"),
        "content_hash": fields.String(description="SHA256 of module contents"),
        "created_at": fields.Integer(description="Creation time (epoch ms)"),
        "updated_at": fields.Integer(description="Last update time (epoch ms)"),
    },
)
MODULE_GET_RESPONSE = wrap_response_single(api, MODULE_GET_MODEL)

MODULE_UPLOAD_INPUT = api.model(
    "MODULE_UPLOAD_INPUT",
    {
        "module_name": fields.String(required=True, description="Module name", example="ls"),
        "module_contents": fields.String(required=True, description="JSON bundle of the module"),
    },
)
MODULE_UPLOAD_RESPONSE = wrap_response_single(api, MODULE_LIST_ITEM_MODEL)

MODULE_DELETE_RESPONSE = wrap_response_empty(api, "MODULE_DELETE_RESPONSE")

MODULE_SEED_RESPONSE = wrap_response_single(
    api,
    api.model(
        "MODULE_SEED_RESULT",
        {
            "created": fields.Integer(description="Number of new modules created"),
            "unchanged": fields.Integer(description="Number of modules already up to date"),
            "updated": fields.Integer(description="Number of modules updated"),
        },
    ),
)
