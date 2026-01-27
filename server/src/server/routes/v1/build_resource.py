import io
import logging
from dataclasses import asdict

from edwh_uuid7 import uuid7
from flask import request, send_file
from flask_restx import Namespace, Resource, fields

from ...db.mysql_connector import get_mysql_session
from ...instance import api
from ...listeners.supervisor import start_listener, stop_listener
from ...modules.implant_builder.build import build_implant
from ...modules.mysql_functions import MySQLImplantPayloadService
from ...schemas.listeners import ListenerCreate
from ...utils.checks import check_type
from ...utils.response import APIResponse

build_ns = Namespace("build", description="Build related operations")
api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")

# listener_spawn_model = api.model(
#     "ListenerSpawnModel",
#     {
#         "listener_host": fields.String(
#             required=True,
#             description="Host the listener will listen on (DNS Host, or IP address)",
#         ),
#         "listener_port": fields.Integer(
#             required=False, description="Port to spawn the listener on"
#         ),
#         "listener_type": fields.String(
#             required=True, description="What type of listener to spawn"
#         ),
#         "listener_name": fields.String(required=True, description="Name of listener"),
#         "listener_notes": fields.String(required=False, description="Listener notes"),
#         "listener_profile": fields.String(
#             required=False,
#             description="Listener malleable c2 profile",
#         ),
#     },
# )

# Api outline:
# POST /build          → generate a new implant
# GET /build           → list available builds
# GET /build/{HASH}      → download a specific implant binary
# DELETE /build/{HASH}   → remove a build

build_implant_model = build_ns.model(
    "BuildImplantInput",
    {
        "implant_variant": fields.String(
            required=True,
            description="The communication variant to use",
            example="http_wininet",
            # enum=["http_wininet", "http_curl"] # Optional: strictly enforce options
        ),
        "output_format": fields.String(
            required=True,
            description="The communication variant to use",
            example="exe",
            # enum=["http_wininet", "http_curl"] # Optional: strictly enforce options
        ),
        "implant_name": fields.String(
            required=True,
            description="The name of the implant",
            example="my_implant",
            # enum=["http_wininet", "http_curl"] # Optional: strictly enforce options
        ),
        "implant_listener_uuid": fields.String(
            required=True,
            description="The listener the implant will call back to. Important, as the implant is formatted with listener specific data.",
            example="0000000-0000-0000-0000-000000000000",
            # enum=["http_wininet", "http_curl"] # Optional: strictly enforce options
        ),
    },
)


class Build(Resource):
    @build_ns.doc(
        summary="Build an Implant",
        description="Builds an Implant to the spec of a listener",
        params={
            "uuid": {
                "description": "Listener ID (uuid) to build implant to",
                "in": "path",
            }
        },
        responses={
            200: "Success",
            404: "Not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    @build_ns.expect(build_implant_model, validate=True)  # flip to True to enforce
    def post(self):
        """
        Submit a build task to build a payload.
        """
        data = build_ns.payload

        listener_uuid = data["implant_listener_uuid"]
        variant = data["implant_variant"]
        implant_name = data["implant_name"]
        output_format = data["output_format"]

        api_logger.info(
            f"Build requested for listener {listener_uuid} (Variant: {variant})",
            extra={"caller_ip": request.remote_addr},
        )

        # 3. Trigger Build
        build_uuid = str(uuid7())

        build_implant(implant_name, listener_uuid, variant, output_format, build_uuid)

        response = {"build_uuid": build_uuid}
        # 4. Return immediately
        return APIResponse(
            status="200", message="Build process initiated successfully", data=response
        ).jsonify()

    def get(self):  # get one implant
        """
        Get a list of all payloads in the Database
        """
        ip = request.remote_addr

        api_logger.info(
            f"Getting all payloads",
            extra={
                "caller_ip": ip,
            },
        )

        # sql call to get implant data, return it as a dict (including bin data)
        with get_mysql_session() as session:
            ips = MySQLImplantPayloadService(session)

            data = ips.get_all_payloads()

        api_response = APIResponse(status="200", message="Success", data=data)
        return api_response.jsonify()


class BuildJobs(Resource):
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

        api_logger.info(
            f"Getting status of build job {build_uuid}",
            extra={
                "caller_ip": ip,
            },
        )

        check_type(build_uuid, str, "build_uuid")

        # sql call to get implant data, return it as a dict (including bin data)
        with get_mysql_session() as session:
            ips = MySQLImplantPayloadService(session)

            data = ips.get_build_job_by_uuid(build_uuid)

            if isinstance(data.get("payload_hash"), bytes):
                data["payload_hash"] = data["payload_hash"].hex()
            # remove bytes (payload and source)
            if "payload_bytes" in data:
                del data["payload_bytes"]

            if "payload_source_code_bytes" in data:
                del data["payload_source_code_bytes"]

        api_response = APIResponse(status="200", message="Success", data=data)
        return api_response.jsonify()


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
        responses={
            200: "Success",
            404: "Not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    def get(self, hash):
        """
        Download a specific payload artifact, based on the provided hash
        """
        ip = request.remote_addr

        # 1. Validation
        check_type(hash, str, "hash")

        api_logger.info(
            f"Download requested for hash {hash}",
            extra={"caller_ip": ip},
        )

        # 2. Fetch Data
        with get_mysql_session() as session:
            service = MySQLImplantPayloadService(session)
            payload = service.get_payload_by_hash(hash)

            if not payload:
                api_logger.warning(f"Payload not found: {hash}")
                return APIResponse(status="404", message="Payload not found").jsonify()

            # 3. Serve File
            # We wrap the bytes in BytesIO so Flask can treat it like a file
            return send_file(
                io.BytesIO(payload.payload_bytes),
                mimetype="application/octet-stream",
                as_attachment=True,
                download_name=payload.payload_name or f"{hash}.bin",
            )

    @build_ns.doc(
        summary="[Not Implemented] Delete an implant",
        description="Deletes a single implant",
        params={
            "hash": {
                "description": "Hash of implant",
                "in": "path",
            }
        },
        responses={
            200: "Success",
            404: "Not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    def delete(self, hash):  # get one implant
        """
        Delete a specific payload artifact, based on the provided hash

        """
        ip = request.remote_addr

        api_logger.info(
            f"Getting implant {hash}",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(hash, str, "hash")

        # sql call to get implant data, return it as a dict (including bin data)

        api_response = APIResponse(
            status="200",
            message="Success",
        )
        return api_response.jsonify()


class SourceActions(Resource):
    @build_ns.doc(
        summary="Download the source of an implant",
        description="Download the source of an implant",
        params={
            "hash": {
                "description": "Hash of implant",
                "in": "path",
            }
        },
        responses={
            200: "Success",
            404: "Not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    def get(self, hash):
        """
        Download a specific payload artifact, based on the provided hash
        """
        ip = request.remote_addr

        # 1. Validation
        check_type(hash, str, "hash")

        api_logger.info(
            f"Download requested for hash {hash}",
            extra={"caller_ip": ip},
        )

        # 2. Fetch Data
        with get_mysql_session() as session:
            service = MySQLImplantPayloadService(session)
            payload = service.get_payload_by_hash(hash)

            if not payload:
                api_logger.warning(f"Payload not found: {hash}")
                return APIResponse(status="404", message="Payload not found").jsonify()

            # 3. Serve File
            # We wrap the bytes in BytesIO so Flask can treat it like a file
            return send_file(
                io.BytesIO(payload.payload_source_code_bytes),
                mimetype="application/octet-stream",
                as_attachment=True,
                download_name=f"{payload.payload_name}_source.zip" or f"{hash}.zip",
            )


build_ns.add_resource(Build, "/")
build_ns.add_resource(BuildJobs, "/jobs/<string:build_uuid>")
build_ns.add_resource(BinaryActions, "/<string:hash>")
build_ns.add_resource(SourceActions, "/<string:hash>/source")

api.add_namespace(build_ns)
