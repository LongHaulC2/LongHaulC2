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


# Error handlers - tldr, on exception, these will flag
# can remove try/except
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
        200, "Retrieved listener data successfully", LISTENER_GET_SUCCESS_MODEL
    )
    @api.marshal_with(LISTENER_GET_SUCCESS_MODEL)
    def get(self, uuid):
        """
        Gets one listener based on user supplied ID

        1. Gets a MYSQL Session

        2. Retrieves 1 record in 'listeners' table based on ID

        3. Returns said data in JSON format.

        """
        ip = request.remote_addr

        api_logger.info(
            f"Getting implant {uuid} data",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        # note, 500's on empty listeners.
        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            listeners = listener_service.get_by_id(uuid)
            # if no listeners
            if listeners == None:
                data = {}

            else:
                data = listeners.to_dict()

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        return api_response.jsonify()

    @listener_ns.doc(
        summary="Stop a listener",
        description="Stops one listener based on user supplied ID",
        params={"uuid": {"description": "Listener ID (uuid)", "in": "path"}},
        responses=COMMON_ERRORS,
    )
    @listener_ns.response(
        200, "The listener was deleted successfully", LISTENER_DELETE_SUCCESS_MODEL
    )
    @listener_ns.marshal_with(LISTENER_DELETE_SUCCESS_MODEL)
    def delete(self, uuid):  # delete one implant based on ID
        """
        Deletes/Stops one listener based on user supplied ID

        1. Gets a MYSQL Session

        2. Deletes 1 record in 'listener' table based on ID

        3. Returns said data in JSON format.
        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} is deleting implant {uuid}")

        api_logger.info(
            f"Stopping listener {uuid}",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        # if successful, remove from db, else, maybe return a warning/degredaded listener state
        stop_listener(listener_uuid=uuid)

        with get_mysql_session() as session:
            listener_service = ListenerService(session)

            # next, update listener to be inactive in the DB
            # listener_service.set_active(uuid, active=False)

            # nuke the record, no need to set to inactive
            listener_service.delete(uuid)

        api_logger.info(
            f"Listener {uuid} deleted successfully",
            extra={
                "caller_ip": ip,
            },
        )

        api_response = APIResponse(
            status=200,
            message="Implant deleted successfully",
        )
        return api_response.jsonify()


class Listeners(Resource):
    # gets all  implants
    @listener_ns.doc(
        summary="Get all Listeners",
        description="Retrieve all listeners in the DB.",
        responses=COMMON_ERRORS,
    )
    @listener_ns.response(
        200, "Retrieved all listener data successfully", LISTENERS_GET_SUCCESS_MODEL
    )
    @listener_ns.marshal_with(LISTENERS_GET_SUCCESS_MODEL)
    def get(self):
        """
        Gets all listeners

        1. Gets a MYSQL Session

        2. Retrieves all records in 'listeners' table

        3. Returns said data in JSON format.

        Note: There is no pagination on this. If there's a lot of entries, this request may take a while.

        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} requested all implants")

        api_logger.info(
            "Getting all implants",
            extra={
                "caller_ip": ip,
            },
        )

        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            listeners = listener_service.get_all()
            if listeners == None:
                data = []
            else:
                data = [i.to_dict() for i in listeners]

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        return api_response.jsonify()

    # create an implant in DB
    @listener_ns.doc(
        summary="Spawn a new listener, and Create a new listener entry.",
        description="Create a new listener. Returns an listener ID to use with that listener",
        responses=COMMON_ERRORS,
    )
    @listener_ns.expect(LISTENERS_POST_INPUT_MODEL)
    @listener_ns.response(
        200, "Successfully created a new listener", LISTENERS_POST_SUCCESS_MODEL
    )
    @listener_ns.marshal_with(LISTENERS_POST_SUCCESS_MODEL)
    def post(self):
        """
        Spawn a new listener

        1. Gets a MYSQL Session

        2. Creates a new record in the 'listeners' table

        3. Returns ID of new record in response
        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} created an implant")

        api_logger.info(
            "Creating an implant",
            extra={
                "caller_ip": ip,
            },
        )

        # data into dataclass
        listener_uuid = str(uuid7())
        listener_dataclass = ListenerCreate(
            # unwrap data into a dataclass
            **api.payload,
            # add on a listener UUID
            listener_uuid=listener_uuid,
        )

        # try to start listener, if successful, put into db
        start_listener(listener_dataclass)

        # get a session
        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            listener = listener_service.create(listener_dataclass)
            listener_id = listener.listener_uuid

            # next, update listener to be active in the DB
            listener_service.set_active(listener_id, active=True)
            # and in the dataclass for the response
            listener_dataclass.listener_active = True

        # experiement with returning dataclasses
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

        return api_response.jsonify()


listener_ns.add_resource(Listener, "/<string:uuid>")
listener_ns.add_resource(Listeners, "/")

api.add_namespace(listener_ns)
