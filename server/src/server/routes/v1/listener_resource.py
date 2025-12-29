from ...instance import env_config, app, api
from flask_restx import Resource, Namespace, fields, abort
from flask import request
from ...utils.response import APIResponse
from ...modules.mysql_functions import ImplantService, MySQLImplantTaskService
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

        2. Retrieves 1 record in 'implant' table based on ID

        3. Returns said data in JSON format.

        """
        ip = request.remote_addr

        api_logger.info(
            f"Getting implant {id} data",
            extra={
                "caller_ip": ip,
            },
        )

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.get_by_id(id)
            data = implants.to_dict()

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        return api_response.jsonify()


# listener_ns.add_resource(Implants, "/")
listener_ns.add_resource(Listener, "/<int:id>")

api.add_namespace(listener_ns)
