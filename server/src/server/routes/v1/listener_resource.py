from dataclasses import asdict

import structlog
from edwh_uuid7 import uuid7
from flask import request
from flask_restx import Namespace, Resource
from werkzeug.exceptions import BadRequest, abort

from ...api_models.error import COMMON_ERRORS, ERROR_MODEL
from ...api_models.listener import (
    LISTENER_DELETE_RESPONSE,
    LISTENER_GET_RESPONSE,
    LISTENER_PATCH_INPUT,
    LISTENER_PATCH_RESPONSE,
    LISTENERS_GET_RESPONSE,
    LISTENERS_POST_INPUT,
    LISTENERS_POST_RESPONSE,
)
from ...instance import api
from ...listeners.supervisor import start_listener, stop_listener
from ...modules.neo4j_functions import Neo4jListenerNodeService
from ...schemas.listeners import ListenerCreate
from ...utils.checks import check_type
from ...utils.response import APIResponse

listener_ns = Namespace("listeners", description="Listener related operations")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


@listener_ns.errorhandler(BadRequest)
@listener_ns.marshal_with(ERROR_MODEL)
def handle_bad_request_and_abort(e):
    """
    Catches all Werkzeug/RESTX aborts and ensures they
    match our {status, message, data} format. This will not catch
    things like "raise valueerror", hence why there are other error handlers  too
    """
    server_logger.error("An error occured", error=e, message=str(e))

    return {
        "status": str(e.code),
        "message": getattr(e, "message", str(e)),
    }, e.code


@listener_ns.errorhandler(Exception)
@listener_ns.marshal_with(ERROR_MODEL)
def handle_general_error(e):
    server_logger.exception("An error occured", error=e)
    return {"status": "500", "message": "An internal error occurred"}, 500


class Listener(Resource):
    @listener_ns.doc(
        summary="Get listener",
        description="Retrieve a single listener by its unique ID.",
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path", "format": "uuid"}},
        responses=COMMON_ERRORS,
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
            abort(404, message="Not Found", data={})

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        return api_response

    @listener_ns.doc(
        summary="Stop a listener",
        description="Stops one listener based on user supplied ID",
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path", "format": "uuid"}},
        responses=COMMON_ERRORS,
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

        api_logger.info("Listener deleted successfully", listener_uuid=uuid, caller_ip=ip)

        api_response = APIResponse(status=200, message="Listener deleted successfully", data="")
        return api_response

    @listener_ns.doc(
        summary="Restart a listener",
        description="Restart a listener",
        responses=COMMON_ERRORS,
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path", "format": "uuid"}},
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
            abort(400, message="Missing field in payload")
            # return APIResponse(status=400, message="Missing 'active' field in payload"), 400

        # check to make sure this a bool first. If not, throw err.
        active_val = payload.get("active")
        if not isinstance(active_val, bool):
            abort(400, message="Incorrect Type")

        user_wants_active = active_val

        # Open one database session for the entire operation
        listener_service = Neo4jListenerNodeService()
        listener = listener_service.get_by_id(uuid)

        if listener is None:
            # api_logger.warning(f"Listener does not exist: {uuid}")
            abort(404, message="Listener does not exist")
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

        else:
            # Stop listener workflow
            stop_listener(listener_uuid=uuid)
            listener_service.set_active(uuid, active=False)
            message = "Listener stopped successfully"

        return APIResponse(status=200, message=message), 200


class Listeners(Resource):
    @listener_ns.doc(
        summary="Get all Listeners",
        description="Retrieve all listeners in the DB.",
        responses=COMMON_ERRORS,
    )
    @listener_ns.response(200, "Retrieved all listener data successfully", LISTENERS_GET_RESPONSE)
    @listener_ns.marshal_with(LISTENERS_GET_RESPONSE)
    def get(self):
        """
        Gets all listeners
        """
        ip = request.remote_addr

        api_logger.info("Getting all listeners", caller_ip=ip)

        listener_service = Neo4jListenerNodeService()
        listeners = listener_service.get_all()
        data = [] if listeners is None else [i.to_dict() for i in listeners]

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        return api_response

    @listener_ns.doc(
        summary="Spawn a new listener",
        description="Create a new listener. Returns a listener ID to use with that listener",
        responses=COMMON_ERRORS,
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

        data = asdict(listener_dataclass)

        api_response = APIResponse(
            status="200",
            message=f"Listener {listener_id} started",
            data=data,
        )

        api_logger.info("Listener started", listener_uuid=listener_id, caller_ip=ip)

        return api_response


listener_ns.add_resource(Listener, "/<string:uuid>")
listener_ns.add_resource(Listeners, "/")

api.add_namespace(listener_ns)
