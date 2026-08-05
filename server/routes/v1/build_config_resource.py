import json
import re

import structlog
from edwh_uuid7 import uuid7
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from werkzeug.exceptions import abort

from ...api_models.build_config import (
    BUILD_CONFIG_DELETE_RESPONSE,
    BUILD_CONFIG_GET_RESPONSE,
    BUILD_CONFIG_LIST_RESPONSE,
    BUILD_CONFIG_UPLOAD_INPUT,
    BUILD_CONFIG_UPLOAD_RESPONSE,
)
from ...api_models.error import COMMON_ERRORS
from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLArtifactService
from ...instance import api
from ...utils.response import APIResponse

build_config_ns = Namespace("build-configs", description="Saved build configuration operations")
api_logger = structlog.getLogger("api")

_VALID_CONFIG_NAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def _validate_config_name(name: str) -> str | None:
    if not name:
        return "Empty config name"
    if not _VALID_CONFIG_NAME.match(name):
        return "Config name must contain only alphanumeric characters, dashes, underscores, and dots"
    return None


class BuildConfigCollection(Resource):
    @jwt_required()
    @build_config_ns.doc(
        summary="List all build configs",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @build_config_ns.response(200, "List of build configs", BUILD_CONFIG_LIST_RESPONSE)
    @build_config_ns.marshal_with(BUILD_CONFIG_LIST_RESPONSE)
    def get(self):
        """List all saved build configurations."""
        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            data = service.get_all_artifacts_by_type("build_config")
        return APIResponse(status="200", message="Success", data=data)

    @jwt_required()
    @build_config_ns.doc(
        summary="Save a build configuration",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @build_config_ns.expect(BUILD_CONFIG_UPLOAD_INPUT, validate=True)
    @build_config_ns.response(200, "Config saved", BUILD_CONFIG_UPLOAD_RESPONSE)
    @build_config_ns.marshal_with(BUILD_CONFIG_UPLOAD_RESPONSE)
    def post(self):
        """Save a new build configuration or update an existing one."""
        payload = build_config_ns.payload
        config_name = payload.get("config_name", "").strip()
        config_contents = payload.get("config_contents", "")

        err = _validate_config_name(config_name)
        if err:
            abort(400, err)

        if not config_contents:
            abort(400, "Missing config_contents")

        try:
            json.loads(config_contents)
        except json.JSONDecodeError:
            abort(400, "config_contents must be valid JSON")

        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            data = service.upsert_artifact(
                artifact_type="build_config",
                artifact_name=config_name,
                artifact_contents=config_contents,
                artifact_uuid=str(uuid7()),
            )

        return APIResponse(status="200", message="Config saved", data=data)


class BuildConfigItem(Resource):
    @jwt_required()
    @build_config_ns.doc(
        summary="Get a build config by name",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @build_config_ns.response(200, "Config contents", BUILD_CONFIG_GET_RESPONSE)
    @build_config_ns.marshal_with(BUILD_CONFIG_GET_RESPONSE)
    def get(self, config_name):
        """Get full build configuration by name."""
        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            artifact = service.get_artifact_by_name("build_config", config_name)
            if not artifact:
                return APIResponse(status="404", message="Build config not found", data={})
            return APIResponse(status="200", message="Success", data=artifact.to_dict())

    @jwt_required()
    @build_config_ns.doc(
        summary="Delete a build config by name",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @build_config_ns.response(200, "Deletion successful", BUILD_CONFIG_DELETE_RESPONSE)
    @build_config_ns.marshal_with(BUILD_CONFIG_DELETE_RESPONSE)
    def delete(self, config_name):
        """Delete a build configuration by name."""
        with get_mysql_session() as session:
            service = MySQLArtifactService(session)
            deleted = service.delete_artifact("build_config", config_name)
            if not deleted:
                return APIResponse(status="404", message="Build config not found")
        return APIResponse(status="200", message="Config deleted")


build_config_ns.add_resource(BuildConfigCollection, "/")
build_config_ns.add_resource(BuildConfigItem, "/<string:config_name>")
api.add_namespace(build_config_ns)
