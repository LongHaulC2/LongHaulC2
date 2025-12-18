from ...instance import env_config, app, api
from flask_restx import Resource, Namespace, fields
from ...utils.response import APIResponse
from ...modules.mysql_functions import ImplantService
from ...schemas.implant import ImplantCreate, ImplantUpdate
from ...db.mysql_connector import get_mysql_engine, get_mysql_session
import logging

implants_ns = Namespace("implants", description="Implant related operations")

api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")

from flask_restx import fields

implant_update_model = api.model(
    "ImplantCreate",
    {
        "external_ip": fields.String(
            description="External IP address (IPv4/IPv6)", example="203.0.113.10"
        ),
        "internal_ip": fields.String(
            description="Internal IP address", example="10.0.0.15"
        ),
        "listener": fields.String(
            description="Listener address (IP or DNS)", example="c2.example.com:443"
        ),
        "user": fields.String(description="User account name", example="SYSTEM"),
        "system_hostname": fields.String(
            description="Hostname of the system", example="WIN-ABC123"
        ),
        "notes": fields.String(
            description="Operator notes", example="Initial check-in"
        ),
        "process": fields.String(description="Process name", example="svchost.exe"),
        "pid": fields.Integer(description="Process ID", example=1234),
        "arch": fields.String(description="CPU architecture", example="x64"),
        "last_checkin": fields.String(
            description="Last check-in time (HH:MM:SS)", example="22:31:05"
        ),
        "sleep_value": fields.Integer(
            description="Sleep interval in seconds", example=60
        ),
    },
)


# Implant list
class Implants(Resource):
    # gets all  implants
    @implants_ns.doc(
        summary="Get all implants",
        description="Retrieve all implants the server knows about.",
    )
    def get(self):
        """
        Gets all implants

        1. Gets a MYSQL Session

        2. Retrieves all records in 'implant' table

        3. Returns said data in JSON  format.

        Note: There is no pagination on this. If there's a lot of entries, this request may take a while.

        """
        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.get_all()
            data = [i.to_dict() for i in implants]

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        return api_response.jsonify()

    # create an implant in DB
    @implants_ns.doc(
        summary="Create a new implant entry.",
        description="Create a new implant entry. Returns an Implant ID to use with that implant",
    )
    def post(self):
        """
        Create a new implant entry

        1. Gets a MYSQL Session

        2. Creates a new record in the 'implants' table

        3. Returns ID of new record in response

        Note: This will create "ghost" sessions with no metadata. Metadata gets updated when 'PUT /v1/api/implants/{id}/' is called.
        """
        # get a seession
        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            # data = ImplantCreate(notes="TESTNOTES")
            data = ImplantCreate()
            implant_object = implant_service.create(data)
            implant_id = implant_object.id

        # need to get ID from DB
        data = {"id": implant_id}

        api_response = APIResponse(
            status="200",
            message="Implant created",
            data=data,
        )

        return api_response.jsonify()


# individual implaant
class Implant(Resource):
    @implants_ns.doc(
        summary="Get implant",
        description="Retrieve a single implant by its unique ID.",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    def get(self, id):  # get one implant
        """
        Gets one implant based on user supplied ID

        1. Gets a MYSQL Session

        2. Retrieves 1 record in 'implant' table based on ID

        3. Returns said data in JSON format.

        """
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

    @implants_ns.doc(
        summary="Update implant",
        description="Update a single implant by its unique ID. Data is supplied in the body of the request.",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    @implants_ns.expect(implant_update_model)
    def put(self, id):  # update one implant based on ID
        """
        Update a single implant by its unique ID.
        """
        # create dataclass from passed in data.
        implant_data = ImplantUpdate(**api.payload)
        implant_id = id

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implant_service.update(implant_id, implant_data)

        api_response = APIResponse(
            status="200",
            message="Success",
        )
        return api_response.jsonify()

    @implants_ns.doc(
        summary="Delete implant",
        description="Delete a single implant by its unique ID.",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    def delete(self, id):  # delete one implant based on ID
        """
        Deletes one implant based on user supplied ID

        1. Gets a MYSQL Session

        2. Deletes 1 record in 'implant' table based on ID

        3. Returns said data in JSON format.

        Note: Operationally, it might be best to not delete old records unless the user wants to.
            ID's are NOT reused after deleting, so if you delete record 1, said ID will NOT be reused upon calling `POST /v1/api/implants/`

        """
        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.delete(id)

        api_response = APIResponse(
            status=200,
            message="Implant deleted successfully",
        )
        return api_response.jsonify()


# individual implaant
class ImplantTask(Resource):
    @implants_ns.doc(
        summary="Get next task implant",
        description="Retrieve the next task for the implant",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    def get(self, id):  # get one implant
        """
        [not implemented] Gets next task of implant


        1. ...
        2. ...
        """
        ...

    @implants_ns.doc(
        summary="Add a task",
        description="Add a task to a single implant by its unique ID. Data is supplied in the body of the request.",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    # @implants_ns.expect(implant_update_model) # add expected field here
    def post(self, id):  # Create a new  command
        """
        [not implemented] Add a new task to an agent

        """

        ...


class ImplantTasks(Resource):
    @implants_ns.doc(
        summary="Gets all tasks of implant",
        description="Retrieve all tasks for the implant",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    def get(self, id):  # get one implant
        """
        [not implemented] Gets all tasks of implant


        1. ...
        2. ...
        """
        ...

    @implants_ns.doc(
        summary="Delete all the tasks of an implant",
        description="Delete all the tasks of an implant",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    def delete(self, id):  #  Delete all tasks of agent
        """
        [not implemented] Delete all the tasks of an agent.

        """


# Add the HelloWorld resource to the API
implants_ns.add_resource(Implants, "/")
implants_ns.add_resource(Implant, "/<int:id>")
implants_ns.add_resource(ImplantTask, "/<int:id>/task")
implants_ns.add_resource(ImplantTasks, "/<int:id>/tasks")

api.add_namespace(implants_ns)
