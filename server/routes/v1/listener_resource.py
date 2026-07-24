from dataclasses import asdict

import structlog
from edwh_uuid7 import uuid7
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from werkzeug.exceptions import abort

from ...api_models.error import COMMON_ERRORS
from ...api_models.listener import (
    LISTENER_DELETE_RESPONSE,
    LISTENER_GET_RESPONSE,
    LISTENER_PATCH_INPUT,
    LISTENER_PATCH_RESPONSE,
    LISTENERS_GET_RESPONSE,
    LISTENERS_POST_INPUT,
    LISTENERS_POST_RESPONSE,
)
from ...db.audit import log_audit
from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLArtifactService
from ...db.neo4j_functions import Neo4jListenerNodeService
from ...instance import api
from ...listeners.supervisor import start_listener, stop_listener
from ...schemas.listeners import ListenerCreate
from ...utils.checks import check_type
from ...utils.response import APIResponse

listener_ns = Namespace("listeners", description="Listener related operations")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


class Listener(Resource):
    @jwt_required()
    @listener_ns.doc(
        summary="Get listener",
        description="Retrieve a single listener by its unique ID.",
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path", "format": "uuid"}},
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @listener_ns.response(200, "Retrieved listener data successfully", LISTENER_GET_RESPONSE)
    @listener_ns.marshal_with(LISTENER_GET_RESPONSE)
    def get(self, uuid):
        """
        Gets one listener based on user supplied ID
        """
        ip = request.remote_addr

        api_logger.info("Getting listener data", listener_uuid=uuid, caller_ip=ip)
        check_type(uuid, str, "uuid")

        listener_service = Neo4jListenerNodeService()
        listeners = listener_service.get_by_id(uuid)

        # The helper 'wrap_response_single' defaults data to {},
        # but explicit empty dict is fine too.
        data = {} if listeners is None else listeners.to_dict()

        # in the event we don't have any data here for this specific listener, just 404
        if not data:
            abort(404, "Not Found")

        return APIResponse(
            status="200",
            message="Success",
            data=data,
        )

    @jwt_required()
    @listener_ns.doc(
        summary="Stop a listener",
        description="Stops one listener based on user supplied ID",
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path", "format": "uuid"}},
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @listener_ns.response(200, "The listener was deleted successfully", LISTENER_DELETE_RESPONSE)
    @listener_ns.marshal_with(LISTENER_DELETE_RESPONSE)
    def delete(self, uuid):  # delete one listener based on ID
        """
        Deletes/Stops one listener based on user supplied ID
        """
        ip = request.remote_addr

        api_logger.info("Stopping listener", listener_uuid=uuid, caller_ip=ip)
        check_type(uuid, str, "uuid")

        # if successful, remove from db
        stop_listener(listener_uuid=uuid)

        listener_service = Neo4jListenerNodeService()
        listener_service.delete(uuid)

        log_audit(get_jwt_identity(), "listener_deleted", "listener", uuid)

        api_logger.info("Listener deleted successfully", listener_uuid=uuid, caller_ip=ip)

        return APIResponse(status=200, message="Listener deleted successfully", data="")

    @jwt_required()
    @listener_ns.doc(
        summary="Restart a listener",
        description="Restart a listener",
        responses=COMMON_ERRORS,
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path", "format": "uuid"}},
        security="Bearer Auth",
    )
    @listener_ns.expect(LISTENER_PATCH_INPUT)
    @listener_ns.response(200, "The listener was restarted successfully", LISTENER_PATCH_RESPONSE)
    @listener_ns.marshal_with(LISTENER_PATCH_RESPONSE)
    def patch(self, uuid):
        """
        Update a listener's active state. Using PATCH as the resource is being updated.

        Payload: { "active": true } or { "active": false }
        """
        # extract the target state from the payload
        payload = api.payload or {}
        if "active" not in payload:
            abort(400, "Missing field in payload")
            # return APIResponse(status=400, message="Missing 'active' field in payload"), 400

        # check to make sure this a bool first. If not, throw err.
        active_val = payload.get("active")
        if not isinstance(active_val, bool):
            abort(400, "Incorrect Type")

        user_wants_active = active_val

        # Open one database session for the entire operation
        listener_service = Neo4jListenerNodeService()
        listener = listener_service.get_by_id(uuid)

        if listener is None:
            # api_logger.warning(f"Listener does not exist: {uuid}")
            abort(404, "Listener does not exist")
            # 404 on no listener

        is_currently_active = listener.listener_active

        # Check if the listener is ALREADY in the desired state
        if user_wants_active and is_currently_active:
            return APIResponse(status=200, message="Listener already online")
        if not user_wants_active and not is_currently_active:
            return APIResponse(status=200, message="Listener already offline")

        # Perform the state change
        if user_wants_active:
            # Start listener workflow
            listener_data = listener.to_dict()
            listener_dataclass = ListenerCreate(**listener_data)

            start_listener(listener_dataclass)
            listener_service.set_active(uuid, active=True)
            message = "Listener started successfully"
            log_audit(get_jwt_identity(), "listener_started", "listener", uuid)

        else:
            # Stop listener workflow
            stop_listener(listener_uuid=uuid)
            listener_service.set_active(uuid, active=False)
            message = "Listener stopped successfully"
            log_audit(get_jwt_identity(), "listener_stopped", "listener", uuid)

        return APIResponse(status=200, message=message), 200


class Listeners(Resource):
    @jwt_required()
    @listener_ns.doc(
        summary="Get all Listeners",
        description="Retrieve all listeners in the DB.",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @listener_ns.response(200, "Retrieved all listener data successfully", LISTENERS_GET_RESPONSE)
    @listener_ns.marshal_with(LISTENERS_GET_RESPONSE)
    def get(self):
        """
        Gets all listeners
        """
        ip = request.remote_addr

        api_logger.debug("Getting all listeners", caller_ip=ip)

        listener_service = Neo4jListenerNodeService()
        listeners = listener_service.get_all()
        data = [] if listeners is None else [i.to_dict() for i in listeners]

        return APIResponse(
            status="200",
            message="Success",
            data=data,
        )

    @jwt_required()
    @listener_ns.doc(
        summary="Spawn a new listener",
        description="Create a new listener. Returns a listener ID to use with that listener",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @listener_ns.expect(LISTENERS_POST_INPUT)
    @listener_ns.response(200, "Successfully created a new listener", LISTENERS_POST_RESPONSE)
    @listener_ns.marshal_with(LISTENERS_POST_RESPONSE)
    def post(self):
        """
        Spawn a new listener
        """
        ip = request.remote_addr

        api_logger.info("Creating a listener", caller_ip=ip)

        listener_uuid = str(uuid7())
        listener_dataclass = ListenerCreate(
            **api.payload,
            listener_uuid=listener_uuid,
        )

        # try to start listener, if successful, put into db
        start_listener(listener_dataclass)

        # get a session
        listener_service = Neo4jListenerNodeService()
        listener = listener_service.create(listener_dataclass)
        listener_id = listener.listener_uuid

        # update listener to be active in the DB
        listener_service.set_active(listener_id, active=True)
        # and in the dataclass for the response
        listener_dataclass.listener_active = True

        if listener_dataclass.listener_profile_name and listener_dataclass.listener_profile_contents:
            try:
                with get_mysql_session() as session:
                    artifact_service = MySQLArtifactService(session)
                    artifact_service.upsert_artifact(
                        artifact_type="profile",
                        artifact_name=listener_dataclass.listener_profile_name,
                        artifact_contents=listener_dataclass.listener_profile_contents,
                        artifact_uuid=str(uuid7()),
                    )
            except Exception:
                server_logger.warning("Failed to save profile to artifact store", listener_uuid=listener_id)

        data = asdict(listener_dataclass)

        api_response = APIResponse(
            status="200",
            message=f"Listener {listener_id} started",
            data=data,
        )

        log_audit(
            get_jwt_identity(), "listener_created", "listener", listener_id, detail=listener_dataclass.listener_name
        )

        api_logger.info("Listener started", listener_uuid=listener_id, caller_ip=ip)

        return api_response


listener_ns.add_resource(Listener, "/<string:uuid>")
listener_ns.add_resource(Listeners, "/")

api.add_namespace(listener_ns)
