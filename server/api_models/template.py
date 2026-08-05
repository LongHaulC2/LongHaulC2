from flask_restx import fields

from ..instance import api
from .profile import wrap_response_list, wrap_response_single

TEMPLATE_BUILD_MODEL = api.model(
    "TEMPLATE_BUILD_MODEL",
    {
        "entrypoints": fields.List(fields.String(), description="Available entrypoint types", example=["exe", "dll"]),
        "default_modules": fields.List(
            fields.String(),
            description="Module names included by default",
            example=["ls", "cd", "files", "metadata", "bof"],
        ),
    },
)

TEMPLATE_ITEM_MODEL = api.model(
    "TEMPLATE_ITEM_MODEL",
    {
        "name": fields.String(description="Template directory name", example="win_x64"),
        "display_name": fields.String(description="Human-readable name", example="Windows x64 (Standard)"),
        "description": fields.String(description="Template description"),
        "platform": fields.String(description="Target platform", example="windows"),
        "arch": fields.String(description="Target architecture", example="x64"),
        "docker_image": fields.String(description="Docker image used for compilation", example="win_x64"),
        "version": fields.String(description="Template version", example="1.2.0"),
        "build": fields.Nested(TEMPLATE_BUILD_MODEL, description="Build configuration"),
    },
)

TEMPLATE_LIST_RESPONSE = wrap_response_list(api, TEMPLATE_ITEM_MODEL)
TEMPLATE_GET_RESPONSE = wrap_response_single(api, TEMPLATE_ITEM_MODEL)
