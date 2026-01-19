import logging
from dataclasses import asdict

from edwh_uuid7 import uuid7
from flask import request
from flask_restx import Namespace, Resource, fields

from ...db.mysql_connector import get_mysql_session
from ...instance import api
from ...listeners.supervisor import start_listener, stop_listener
from ...modules.implant_builder.build import build_implant
from ...modules.mysql_functions import ListenerService
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
    def post(self, uuid):  # get one implant
        """
        ...

        """
        ip = request.remote_addr

        api_logger.info(
            f"Getting implant {uuid} data",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        build_implant(uuid)

        # return immediatly, don't send hash to not wait on build.
        # client will get hash with get req
        api_response = APIResponse(
            status="200",
            message="Success",
        )
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
    def get(self, hash):  # get one implant
        """
        ...
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
        ...

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


build_ns.add_resource(Build, "/")
build_ns.add_resource(BinaryActions, "/<string:hash>")

api.add_namespace(build_ns)
