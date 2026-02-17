import logging
from dataclasses import asdict

from edwh_uuid7 import uuid7
from flask import request
from flask_restx import Namespace, Resource, fields

from ...api_models.error import *
from ...api_models.listener import *
from ...db.mysql_connector import get_mysql_session
from ...instance import api
from ...listeners.supervisor import start_listener, stop_listener
from ...modules.mysql_functions import ListenerService
from ...schemas.listeners import ListenerCreate
from ...utils.checks import check_type
from ...utils.response import APIResponse

listener_ns = Namespace("listeners", description="Listener related operations")
api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")


# Error handlers
@listener_ns.errorhandler(ValueError)
def handle_value_error(e):
    return {"status": "400", "message": str(e), "data": None}, 400


@listener_ns.errorhandler(Exception)
def handle_general_error(e):
    return {"status": "500", "message": "An internal error occurred", "data": None}, 500


class Listener(Resource):
    @listener_ns.doc(
        summary="Get listener",
        description="Retrieve a single listener by its unique ID.",
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path"}},
        responses=COMMON_ERRORS,
    )
    @listener_ns.response(
        200, "Retrieved listener data successfully", LISTENER_GET_RESPONSE
    )
    @listener_ns.marshal_with(LISTENER_GET_RESPONSE)
    def get(self, uuid):
        """
        Gets one listener based on user supplied ID
        """
        ip = request.remote_addr

        api_logger.info(
            f"Getting listener {uuid} data",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            listeners = listener_service.get_by_id(uuid)

            if listeners is None:
                # The helper 'wrap_response_single' defaults data to {},
                # but explicit empty dict is fine too.
                data = {}
            else:
                data = listeners.to_dict()

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        return api_response

    @listener_ns.doc(
        summary="Stop a listener",
        description="Stops one listener based on user supplied ID",
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path"}},
        responses=COMMON_ERRORS,
    )
    @listener_ns.response(
        200, "The listener was deleted successfully", LISTENER_DELETE_RESPONSE
    )
    @listener_ns.marshal_with(LISTENER_DELETE_RESPONSE)
    def delete(self, uuid):  # delete one listener based on ID
        """
        Deletes/Stops one listener based on user supplied ID
        """
        ip = request.remote_addr

        api_logger.info(
            f"Stopping listener {uuid}",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        # if successful, remove from db
        stop_listener(listener_uuid=uuid)

        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            listener_service.delete(uuid)

        api_logger.info(
            f"Listener {uuid} deleted successfully",
            extra={
                "caller_ip": ip,
            },
        )

        api_response = APIResponse(
            status=200,
            message="Listener deleted successfully",
        )
        return api_response

    @listener_ns.doc(
        summary="Restart a listener",
        description="Restart a listener",
        responses=COMMON_ERRORS,
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path"}},
    )
    @listener_ns.response(
        200, "The listener was restarted successfully", LISTENER_PATCH_RESPONSE
    )
    @listener_ns.marshal_with(LISTENER_PATCH_RESPONSE)
    def patch(self, uuid):
        """
        Restart a listener. Using PATCH as the resource is being updated, not replaced, as PUT dictates

        """

        # get listener uuid

        # get data of that listener
        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            listeners = listener_service.get_by_id(uuid)

            if listeners is None:
                # can raise, and flask will handle the err for us
                raise ValueError

            listener_data = listeners.to_dict()

        # stop it
        stop_listener(listener_uuid=uuid)

        # put together data again
        listener_dataclass = ListenerCreate(**listener_data)

        # set as inactive, just in case it bugs out and doesn't restart
        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            # update listener to be active in the DB
            listener_service.set_active(uuid, active=False)

        # try to start listener, if successful, put into db
        start_listener(listener_dataclass)

        # get a session
        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            # update listener to be active in the DB
            listener_service.set_active(uuid, active=True)
            # and in the dataclass for the response
            listener_dataclass.listener_active = True

        api_response = APIResponse(
            status=200,
            message="Listener restarted successfully",
        )
        return api_response


class Listeners(Resource):
    @listener_ns.doc(
        summary="Get all Listeners",
        description="Retrieve all listeners in the DB.",
        responses=COMMON_ERRORS,
    )
    @listener_ns.response(
        200, "Retrieved all listener data successfully", LISTENERS_GET_RESPONSE
    )
    @listener_ns.marshal_with(LISTENERS_GET_RESPONSE)
    def get(self):
        """
        Gets all listeners
        """
        ip = request.remote_addr

        api_logger.info(
            "Getting all listeners",
            extra={
                "caller_ip": ip,
            },
        )

        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            listeners = listener_service.get_all()
            if listeners is None:
                data = []
            else:
                data = [i.to_dict() for i in listeners]

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
    @listener_ns.response(
        200, "Successfully created a new listener", LISTENERS_POST_RESPONSE
    )
    @listener_ns.marshal_with(LISTENERS_POST_RESPONSE)
    def post(self):
        """
        Spawn a new listener
        """
        ip = request.remote_addr

        api_logger.info(
            "Creating a listener",
            extra={
                "caller_ip": ip,
            },
        )

        listener_uuid = str(uuid7())
        listener_dataclass = ListenerCreate(
            **api.payload,
            listener_uuid=listener_uuid,
        )

        # try to start listener, if successful, put into db
        start_listener(listener_dataclass)

        # get a session
        with get_mysql_session() as session:
            listener_service = ListenerService(session)
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

        api_logger.info(
            f"Listener {listener_id} started",
            extra={
                "caller_ip": ip,
            },
        )

        return api_response


listener_ns.add_resource(Listener, "/<string:uuid>")
listener_ns.add_resource(Listeners, "/")

api.add_namespace(listener_ns)
