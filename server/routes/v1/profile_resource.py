import tomllib

import structlog
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from werkzeug.exceptions import abort

from ...api_models.error import COMMON_ERRORS
from ...api_models.profile import (
    PROFILE_PREVIEW_INPUT,
    PROFILE_PREVIEW_RESPONSE,
    PROFILE_RAW_ENTRY_MODEL,  # noqa: F401 — imported to ensure model is registered
)
from ...instance import api
from ...listeners.transform import apply_python_transforms
from ...utils.response import APIResponse

profile_ns = Namespace("profiles", description="Network profile operations")
api_logger = structlog.getLogger("api")

# Sample payload used for transform chain visualization
_PREVIEW_PAYLOAD = b"PREVIEW_PAYLOAD"


def _apply_transforms_with_steps(data: bytes, transforms_list: list[dict] | None) -> list[dict]:
    """
    Apply each transform one at a time and record the intermediate result.
    Used exclusively for preview/display — not part of the live traffic path.
    """
    steps = []
    current = data
    for step in transforms_list or []:
        current = apply_python_transforms(current, [step])
        try:
            display = current.decode("utf-8")
        except UnicodeDecodeError:
            display = current.hex()
        record: dict = {"op": step.get("op", "unknown"), "result_display": display}
        if "val" in step:
            record["val"] = str(step["val"])
        steps.append(record)
    return steps


def _build_smb(smb_block: dict) -> dict:
    return {
        "inbox_pipe_name": smb_block.get("get", {}).get("pipe_name", "inbox"),
        "outbox_pipe_name": smb_block.get("post", {}).get("pipe_name", "outbox"),
    }


def _build_raw_get(get_block: dict) -> dict:
    metadata_transforms = get_block.get("client", {}).get("metadata", {}).get("transforms", [])
    server_output_transforms = get_block.get("server", {}).get("output", {}).get("transforms", [])
    body = get_block.get("body", "<METADATA>")
    return {
        "proto": get_block.get("proto", "tcp"),
        "client": {
            "body": body,
            "metadata_token_location": "body" if "<METADATA>" in body else "not_found",
            "metadata_transforms": _apply_transforms_with_steps(_PREVIEW_PAYLOAD, metadata_transforms),
        },
        "server": {
            "body": get_block.get("server", {}).get("body", "<OUTPUT>"),
            "output_transforms": _apply_transforms_with_steps(_PREVIEW_PAYLOAD, server_output_transforms),
        },
    }


def _build_raw_post(post_block: dict) -> dict:
    output_transforms = post_block.get("client", {}).get("output", {}).get("transforms", [])
    id_transforms = post_block.get("client", {}).get("id", {}).get("transforms", [])
    server_output_transforms = post_block.get("server", {}).get("output", {}).get("transforms", [])
    body = post_block.get("body", "<OUTPUT>")
    return {
        "proto": post_block.get("proto", "tcp"),
        "client": {
            "body": body,
            "output_token_location": "body" if "<OUTPUT>" in body else "not_found",
            "output_transforms": _apply_transforms_with_steps(_PREVIEW_PAYLOAD, output_transforms),
            "id_transforms": _apply_transforms_with_steps(_PREVIEW_PAYLOAD, id_transforms),
        },
        "server": {
            "body": post_block.get("server", {}).get("body", ""),
            "output_transforms": _apply_transforms_with_steps(_PREVIEW_PAYLOAD, server_output_transforms),
        },
    }


def _build_all_raw(raw_block: dict) -> list[dict]:
    """Parse the [raw] TOML block (top-level [raw.get]/[raw.post] only)."""
    if not raw_block:
        return []
    get_data = _build_raw_get(raw_block.get("get", {})) if raw_block.get("get") else None
    post_data = _build_raw_post(raw_block.get("post", {})) if raw_block.get("post") else None
    return [{"name": "default", "get": get_data, "post": post_data}]


def _validate(parsed: dict) -> dict:
    missing = []
    warnings = []

    raw_block = parsed.get("raw", {})
    if not raw_block.get("get"):
        missing.append("[raw.get]")
    if not raw_block.get("post"):
        missing.append("[raw.post]")

    if not parsed.get("smb"):
        warnings.append("[smb] section not present — SMB chaining will not be configured")

    if not parsed.get("raw"):
        warnings.append("[raw] section not present — no C2 channel configured")

    return {"parse_ok": True, "parse_error": None, "missing_fields": missing, "warnings": warnings}


class ProfilePreview(Resource):
    @profile_ns.doc(
        summary="Preview a network profile",
        description=(
            "Parse a TOML network profile and return a structured preview: request/response templates, "
            "header lists, and step-by-step transform chain output for each protocol section."
        ),
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @profile_ns.expect(PROFILE_PREVIEW_INPUT, validate=False)
    @profile_ns.response(200, "Preview rendered successfully", PROFILE_PREVIEW_RESPONSE)
    @profile_ns.marshal_with(PROFILE_PREVIEW_RESPONSE)
    @jwt_required()
    def post(self):
        """Render a TOML network profile into a structured human-readable preview."""
        ip = request.remote_addr
        payload = profile_ns.payload

        if not payload or not payload.get("profile_contents"):
            abort(400, "Missing profile_contents in request body")

        profile_contents = payload["profile_contents"]
        api_logger.info("Rendering profile preview", caller_ip=ip)

        # Attempt TOML parse — return a structured error rather than a 400 so the
        # client can display the parse error message directly in the UI.
        try:
            parsed = tomllib.loads(profile_contents)
        except Exception as e:
            api_logger.warning("Profile TOML parse failed", error=str(e), caller_ip=ip)
            return APIResponse(
                status="200",
                message="Profile preview rendered with errors",
                data={
                    "profile_name": "",
                    "profile_author": "",
                    "smb": None,
                    "raw_profiles": [],
                    "validation": {
                        "parse_ok": False,
                        "parse_error": str(e),
                        "missing_fields": [],
                        "warnings": [],
                    },
                },
            )

        profile_meta = parsed.get("profile", {})
        smb_data = _build_smb(parsed["smb"]) if parsed.get("smb") else None
        raw_profiles_data = _build_all_raw(parsed.get("raw", {}))

        return APIResponse(
            status="200",
            message="Profile preview rendered successfully",
            data={
                "profile_name": profile_meta.get("name", ""),
                "profile_author": profile_meta.get("author", ""),
                "smb": smb_data,
                "raw_profiles": raw_profiles_data,
                "validation": _validate(parsed),
            },
        )


profile_ns.add_resource(ProfilePreview, "/preview")
api.add_namespace(profile_ns)
