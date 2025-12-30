from ...instance import env_config, app, api
from flask_restx import Resource, Namespace, fields, abort
from flask import request
from ...utils.response import APIResponse
from ...modules.mysql_functions import ListenerService
from ...modules.redis_functions import RedisImplantTaskService
from ...schemas.implant import ImplantCreate, ImplantUpdate, Task, TaskData, Search
from ...db.mysql_connector import get_mysql_engine, get_mysql_session
import logging
import base64
from edwh_uuid7 import uuid7

listener_ns = Namespace("listeners", description="Listener related operations")
api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")


class Listener(Resource):
    @listener_ns.doc(
        summary="Get listener",
        description="Retrieve a single listener by its unique ID.",
        params={"id": {"description": "Listener ID (uuid)", "in": "path"}},
    )
    def get(self, id):  # get one implant
        """
        Gets one implant based on user supplied ID

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


# listener_ns.add_resource(Implants, "/")
listener_ns.add_resource(Listener, "/<int:id>")
listener_ns.add_resource(Listeners, "/")

api.add_namespace(listener_ns)
