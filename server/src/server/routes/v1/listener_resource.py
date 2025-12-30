from ...instance import env_config, app, api
from flask_restx import Resource, Namespace, fields, abort
from flask import request
from ...utils.response import APIResponse
from ...modules.mysql_functions import ListenerService
from ...modules.redis_functions import RedisImplantTaskService
from ...schemas.listeners import ListenerCreate
from ...db.mysql_connector import get_mysql_engine, get_mysql_session
from ...listeners.supervisor import start_listener, stop_all, stop_listener

import logging
import base64
from edwh_uuid7 import uuid7
from dataclasses import dataclass, asdict

listener_ns = Namespace("listeners", description="Listener related operations")
api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")

listener_spawn_model = api.model(
    "ListenerSpawnModel",
    {
        "listener_host": fields.String(
            required=True,
            description="Host the listener will listen on (DNS Host, or IP address)",
        ),
        "listener_port": fields.Integer(
            required=False, description="Port to spawn the listener on"
        ),
        "listener_type": fields.String(
            required=True, description="What type of listener to spawn"
        ),
        "listener_name": fields.String(required=True, description="Name of listener"),
        "listener_notes": fields.String(required=False, description="Listener notes"),
    },
)


class Listener(Resource):
    @listener_ns.doc(
        summary="Get listener",
        description="Retrieve a single listener by its unique ID.",
        params={"id": {"description": "Listener ID (uuid)", "in": "path"}},
    )
    def get(self, id):  # get one implant
        """
        Gets one listener based on user supplied ID

        1. Gets a MYSQL Session

        2. Retrieves 1 record in 'listeners' table based on ID

        3. Returns said data in JSON format.

        """
        ip = request.remote_addr

        api_logger.info(
            f"Getting implant {id} data",
            extra={
                "caller_ip": ip,
            },
        )

        # note, 500's on empty listeners.
        with get_mysql_session() as session:
            listener_service = ListenerService(session)
            listeners = listener_service.get_by_id(id)
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

    def delete(self, id):  # delete one implant based on ID
        """
        Deletes/Stops one listener based on user supplied ID

        1. Gets a MYSQL Session

        2. Deletes 1 record in 'listener' table based on ID

        3. Returns said data in JSON format.
        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} is deleting implant {id}")

        api_logger.info(
            f"Stopping listener {id}",
            extra={
                "caller_ip": ip,
            },
        )

        # if successful, remove from db, else, maybe return a warning/degredaded listener state
        stop_listener(listener_uuid=id)

        with get_mysql_session() as session:
            listener_service = ListenerService(session)

            # next, update listener to be inactive in the DB
            # listener_service.set_active(id, active=False)

            # nuke the record, no need to set to inactive
            listener_service.delete(id)

        api_logger.info(
            f"Listener {id} deleted successfully",
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
    )
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
    )
    @listener_ns.expect(listener_spawn_model)
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
            # add on a task id
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


listener_ns.add_resource(Listener, "/<string:id>")
listener_ns.add_resource(Listeners, "/")

api.add_namespace(listener_ns)
