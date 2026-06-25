import io

import structlog
from edwh_uuid7 import uuid7
from flask import request, send_file
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from ...api_models.build import (
    BINARYACTIONS_DELETE_RESPONSE,
    BUILD_GET_RESPONSE,
    BUILD_POST_INPUT,
    BUILD_POST_RESPONSE,
    BUILDJOBS_GET_RESPONSE,
)
from ...api_models.error import COMMON_ERRORS
from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLImplantPayloadService
from ...instance import api
from ...modules.implant_builder.build import build_implant
from ...utils.checks import check_type
from ...utils.response import APIResponse

build_ns = Namespace("build", description="Build related operations")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


# come back to this for models later lol
class Build(Resource):
    @build_ns.doc(
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @build_ns.expect(BUILD_POST_INPUT, validate=False)  # flip to True to enforce
    @build_ns.response(200, "Build initiated", BUILD_POST_RESPONSE)
    @build_ns.marshal_with(BUILD_POST_RESPONSE)
    @jwt_required()
    def post(self):
        """
        Submit a task to build a new C2 implant payload.

        This endpoint accepts a JSON configuration defining the implant's properties,
        including its name, output format, and a dictionary of listeners it should communicate with.

        The build process is asynchronous. This endpoint returns immediately with a `build_uuid`
        which can be used to poll the status via `GET /builds/{build_uuid}`.
        """

        data = build_ns.payload

        # change this to a dict
        """

        listeners_dict: Dict[
            str, BuildRequestListener
        ]

        """

        # print(data)
        # listener_uuid = data["implant_listener_uuid"]
        # variant = data["implant_variant"]
        implant_name = data["implant_name"]
        # output_format = data["output_format"]
        # listener_dict = data.get("listener_dict", {})
        listener_uuids = data.get("listener_uuids", [])

        initial_get_profile_listener_uuid = data.get("initial_get_profile_listener_uuid", None)
        initial_post_profile_listener_uuid = data.get("initial_post_profile_listener_uuid", None)

        options_dict = data.get("options", {})
        enable_debug: bool = options_dict.get("enable_debug", None)  # noqa
        clear_build_cache: bool = options_dict.get("enable_debug", None)  # noqa

        api_logger.info("Build requested", caller_ip=request.remote_addr)

        # Trigger Build
        build_uuid = str(uuid7())

        build_stats = build_implant(
            implant_name,
            listener_uuids,
            # output_format,
            build_uuid,
            initial_get_profile_listener_uuid,
            initial_post_profile_listener_uuid,
            options=options_dict,
        )

        response = {"build_uuid": build_uuid, "build_stats": build_stats}
        # Return immediately
        return APIResponse(status="200", message="Build process initiated successfully", data=response)

    @build_ns.doc(
        summary="Get all builds",
        description="Get a list of all payloads in the Database",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @build_ns.response(200, "List of builds", BUILD_GET_RESPONSE)
    @build_ns.marshal_with(BUILD_GET_RESPONSE)
    @jwt_required()
    def get(self):  # get one implant
        """
        Get a list of all payloads in the Database
        """
        ip = request.remote_addr

        api_logger.info("Getting all payloads", caller_ip=ip)

        # sql call to get implant data, return it as a dict (including bin data)
        with get_mysql_session() as session:
            ips = MySQLImplantPayloadService(session)

            data = ips.get_all_payloads()

        return APIResponse(status="200", message="Success", data=data)


class BuildJobs(Resource):
    @build_ns.doc(
        summary="Get build job status",
        description="Get the status of a specific build job.",
        responses=COMMON_ERRORS,
        params={"build_uuid": {"description": "The UUID of the build", "in": "path", "format": "uuid"}},
        security="Bearer Auth",
    )
    @build_ns.response(200, "Build job status", BUILDJOBS_GET_RESPONSE)
    @build_ns.marshal_with(BUILDJOBS_GET_RESPONSE)
    @jwt_required()
    def get(self, build_uuid):  # get one implant
        """
        Get the status of a build job

        Contains all of the information about a build, except for payload bytes, and zip bytes.

        If you are looking for the payload/source code,
        Please use:

         - `GET /api/v1/build/{payload_hash}` to get the payload as a file (bytes)
         - `GET /api/v1/build/{payload_hash}/source` to get the source code zip

        """
        ip = request.remote_addr

        api_logger.info("Getting status of build job", build_uuid=build_uuid, caller_ip=ip)

        check_type(build_uuid, str, "build_uuid")

        # sql call to get implant data, return it as a dict (including bin data)
        with get_mysql_session() as session:
            ips = MySQLImplantPayloadService(session)

            data = ips.get_build_job_by_uuid(build_uuid)

            if isinstance(data.get("payload_hash"), bytes):
                data["payload_hash"] = data["payload_hash"].hex()
            # remove bytes (payload and source), as flask can't handle them/encode them as responses.
            # There are endpoints for this specifically that send as a file
            if "payload_bytes" in data:
                del data["payload_bytes"]

            if "payload_source_code_bytes" in data:
                del data["payload_source_code_bytes"]

        return APIResponse(status="200", message="Success", data=data)


# GET /build/hash: Get singular binary
# DELETE /build/hash: Delete singular binary
# note: Bins shuold be stored in the DB, as a binary/blob field
class BinaryActions(Resource):
    @build_ns.doc(
        summary="[Not Implemented] Download an implant",
        description="Downloads a single implant",
        params={
            "hash": {
                "description": "Hash of implant",
                "in": "path",
            }
        },
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @build_ns.produces(["application/octet-stream"])
    @build_ns.response(
        200,
        "Binary File Stream",
        headers={"Content-Disposition": "attachment; filename=payload.bin"},
    )
    @jwt_required()
    @build_ns.response(404, "Payload Not Found")
    def get(self, hash):
        """
        Download a specific payload artifact, based on the provided hash
        """
        ip = request.remote_addr

        # Validation
        check_type(hash, str, "hash")

        api_logger.info(
            "Download requested for hash",
            hash=hash,
            caller_ip=ip,
        )

        # Fetch Data
        with get_mysql_session() as session:
            service = MySQLImplantPayloadService(session)
            payload = service.get_payload_by_hash(hash)

            if not payload:
                api_logger.warning("Payload not found", hash=hash)
                return APIResponse(status="404", message="Payload not found")

            # Serve File
            # We wrap the bytes in BytesIO so Flask can treat it like a file
            return send_file(
                io.BytesIO(payload.payload_bytes),
                mimetype="application/octet-stream",
                as_attachment=True,
                download_name=payload.payload_name or f"{hash}.bin",
            )

    @build_ns.doc(
        summary="Delete an implant",
        description="Deletes a single implant",
        params={
            "hash": {
                "description": "Hash of implant",
                "in": "path",
            }
        },
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    # show a model for what happens when nothing is here
    @build_ns.response(200, "Deletion Successful", BINARYACTIONS_DELETE_RESPONSE)
    @build_ns.response(404, "Payload Not Found")
    # and then what to actually filter the output by
    @build_ns.marshal_with(BINARYACTIONS_DELETE_RESPONSE)
    @jwt_required()
    def delete(self, hash):
        """
        Delete a specific payload artifact, based on the provided hash

        """
        ip = request.remote_addr

        api_logger.info("Getting implant", hash=hash, caller_ip=ip)
        check_type(hash, str, "hash")

        # sql call to get implant data, return it as a dict (including bin data)

        return APIResponse(
            status="200",
            message="Success",
        )


class SourceActions(Resource):
    @build_ns.doc(
        summary="Download Implant Source Code",
        description="Retrieves the source code archive (ZIP) for a specific implant build.",
        params={"hash": "The MD5 hash of the payload source to download"},
        # keeping simpler responses here
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @build_ns.produces(["application/octet-stream", "application/zip"])
    # important to response options here
    @build_ns.response(
        200,
        "Source Code Archive (ZIP)",
        headers={"Content-Disposition": "attachment; filename=..._source.zip"},
    )
    @build_ns.response(404, "Source Code Not Found")
    @jwt_required()
    def get(self, hash):
        """
        Download the source code zip for a specific payload.
        """
        ip = request.remote_addr

        # Validation
        check_type(hash, str, "hash")

        api_logger.info(
            "Source download requested for hash",
            hash=hash,
            caller_ip=ip,
        )

        # Fetch Data
        with get_mysql_session() as session:
            service = MySQLImplantPayloadService(session)
            payload = service.get_payload_by_hash(hash)

            if not payload:
                api_logger.warning("Payload source not found", hash=hash)
                # Return JSON error
                return {"message": "Payload source not found"}, 404

            # Serve File
            # We wrap the bytes in BytesIO so Flask can treat it like a file
            return send_file(
                io.BytesIO(payload.payload_source_code_bytes),
                mimetype="application/octet-stream",
                as_attachment=True,
                download_name=(f"{payload.payload_name}_source.zip" if payload.payload_name else f"{hash}.zip"),
            )


build_ns.add_resource(Build, "/")
build_ns.add_resource(BuildJobs, "/jobs/<string:build_uuid>")
build_ns.add_resource(BinaryActions, "/<string:hash>")
build_ns.add_resource(SourceActions, "/<string:hash>/source")

api.add_namespace(build_ns)
