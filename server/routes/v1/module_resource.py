import json
import re
from pathlib import Path

import structlog
from edwh_uuid7 import uuid7
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from werkzeug.exceptions import abort

from ...api_models.error import COMMON_ERRORS
from ...api_models.module import (
    MODULE_DELETE_RESPONSE,
    MODULE_GET_RESPONSE,
    MODULE_LIST_RESPONSE,
    MODULE_SEED_RESPONSE,
    MODULE_UPLOAD_INPUT,
    MODULE_UPLOAD_RESPONSE,
)
from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLArtifactService
from ...instance import api
from ...utils.response import APIResponse

module_ns = Namespace("modules", description="Implant module operations")
api_logger = structlog.getLogger("api")

_VALID_MODULE_NAME = re.compile(r"^[a-zA-Z0-9_\-]+$")
_RESERVED_NAMES = {"seed"}
_SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds" / "modules"


def _validate_module_name(name: str) -> str | None:
    if not name or name.lower() in _RESERVED_NAMES:
        return "Reserved or empty module name"
    if not _valid_module_name(name):
        return "Module name must contain only alphanumeric characters, dashes, and underscores"
    return None


def _valid_module_name(name: str) -> bool:
    return bool(_VALID_MODULE_NAME.match(name))


class ModuleCollection(Resource):
    @jwt_required()
    @module_ns.doc(
        summary="List all modules",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @module_ns.response(200, "List of modules", MODULE_LIST_RESPONSE)
    @module_ns.marshal_with(MODULE_LIST_RESPONSE)
    def get(self):
        """List all stored modules (metadata only, no contents)."""
        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            data = service.get_all_artifacts_by_type("module")
        return APIResponse(status="200", message="Success", data=data)

    @jwt_required()
    @module_ns.doc(
        summary="Upload or update a module",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @module_ns.expect(MODULE_UPLOAD_INPUT, validate=True)
    @module_ns.response(200, "Module saved", MODULE_UPLOAD_RESPONSE)
    @module_ns.marshal_with(MODULE_UPLOAD_RESPONSE)
    def post(self):
        """Upload a new module or update an existing one by name."""
        payload = module_ns.payload
        module_name = payload.get("module_name", "").strip()
        module_contents = payload.get("module_contents", "")

        err = _validate_module_name(module_name)
        if err:
            abort(400, err)

        if not module_contents:
            abort(400, "Missing module_contents")

        try:
            json.loads(module_contents)
        except json.JSONDecodeError:
            abort(400, "module_contents must be valid JSON")

        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            data = service.upsert_artifact(
                artifact_type="module",
                artifact_name=module_name,
                artifact_contents=module_contents,
                artifact_uuid=str(uuid7()),
            )

        return APIResponse(status="200", message="Module saved", data=data)


class ModuleItem(Resource):
    @jwt_required()
    @module_ns.doc(
        summary="Get a module by name",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @module_ns.response(200, "Module contents", MODULE_GET_RESPONSE)
    @module_ns.marshal_with(MODULE_GET_RESPONSE)
    def get(self, module_name):
        """Download full module bundle by name."""
        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            artifact = service.get_artifact_by_name("module", module_name)
            if not artifact:
                return APIResponse(status="404", message="Module not found", data={})
            return APIResponse(status="200", message="Success", data=artifact.to_dict())

    @jwt_required()
    @module_ns.doc(
        summary="Delete a module by name",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @module_ns.response(200, "Deletion successful", MODULE_DELETE_RESPONSE)
    @module_ns.marshal_with(MODULE_DELETE_RESPONSE)
    def delete(self, module_name):
        """Delete a module by name."""
        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            deleted = service.delete_artifact("module", module_name)
            if not deleted:
                return APIResponse(status="404", message="Module not found")
        return APIResponse(status="200", message="Module deleted")


class ModuleSeed(Resource):
    @jwt_required()
    @module_ns.doc(
        summary="Seed default modules from server-side JSON files",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @module_ns.response(200, "Seed complete", MODULE_SEED_RESPONSE)
    @module_ns.marshal_with(MODULE_SEED_RESPONSE)
    def post(self):
        """Load default module bundles from server/seeds/modules/ into the database."""
        created = 0
        unchanged = 0
        updated = 0

        if not _SEEDS_DIR.exists():
            return APIResponse(
                status="200", message="No seed directory found", data={"created": 0, "unchanged": 0, "updated": 0}
            )

        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            for seed_file in sorted(_SEEDS_DIR.glob("*.json")):
                try:
                    raw = seed_file.read_text(encoding="utf-8")
                    bundle = json.loads(raw)
                except Exception as e:
                    api_logger.warning("Skipping malformed seed file", file=seed_file.name, error=str(e))
                    continue

                name = bundle.get("module", {}).get("name", "")
                if not name or not _valid_module_name(name):
                    continue

                existing = service.get_artifact_by_name("module", name)
                result = service.upsert_artifact(
                    artifact_type="module",
                    artifact_name=name,
                    artifact_contents=raw,
                    artifact_uuid=str(uuid7()),
                )
                if existing is None:
                    created += 1
                elif existing.content_hash == result["content_hash"]:
                    unchanged += 1
                else:
                    updated += 1

        return APIResponse(
            status="200",
            message="Seed complete",
            data={"created": created, "unchanged": unchanged, "updated": updated},
        )


module_ns.add_resource(ModuleCollection, "/")
module_ns.add_resource(ModuleSeed, "/seed")
module_ns.add_resource(ModuleItem, "/<string:module_name>")
api.add_namespace(module_ns)
