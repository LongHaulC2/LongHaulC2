from ...instance import env_config, app, api
from flask_restx import Resource, Namespace, fields, abort
from flask import request
from ...utils.response import APIResponse
from ...modules.mysql_functions import ImplantService, MySQLImplantTaskService
from ...modules.redis_functions import RedisImplantTaskService
from ...schemas.implant import ImplantCreate, ImplantUpdate, Task, TaskData
from ...db.mysql_connector import get_mysql_engine, get_mysql_session
import logging
import base64
from edwh_uuid7 import uuid7

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

implant_task_model = api.model(
    "TaskModel",
    {
        "task": fields.String(
            required=True, description="Name of the task to be performed"
        ),
        "data": fields.Raw(required=True, description="Dynamic key/value pairs"),
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
        ip = request.remote_addr
        # api_logger.info(f"{ip} requested all implants")

        api_logger.info(
            "Getting all implants",
            extra={
                "caller_ip": ip,
            },
        )

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
        ip = request.remote_addr
        # api_logger.info(f"{ip} created an implant")

        api_logger.info(
            "Creating an implant",
            extra={
                "caller_ip": ip,
            },
        )

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
            message=f"Implant {implant_id} created",
            data=data,
        )

        api_logger.info(
            f"Implant {implant_id} created",
            extra={
                "caller_ip": ip,
            },
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
        ip = request.remote_addr
        # api_logger.info(f"{ip} is retrieving implant {id}")

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
        ip = request.remote_addr
        # api_logger.info(f"{ip} is updating implant {id}")

        api_logger.info(
            f"Updating implant {id}'s data",
            extra={
                "caller_ip": ip,
            },
        )

        # create dataclass from passed in data.
        implant_data = ImplantUpdate(**api.payload)
        implant_id = id

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implant_service.update(implant_id, implant_data)

        api_logger.info(
            f"Updated implant {id}'s data successfully",
            extra={
                "caller_ip": ip,
            },
        )

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
        ip = request.remote_addr
        # api_logger.info(f"{ip} is deleting implant {id}")

        api_logger.info(
            f"Deleting implant {id}",
            extra={
                "caller_ip": ip,
            },
        )

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.delete(id)

        # api_logger.info(f"Implant {id} deleted successfully")

        api_logger.info(
            f"Implant {id} deleted successfully",
            extra={
                "caller_ip": ip,
            },
        )

        api_response = APIResponse(
            status=200,
            message="Implant deleted successfully",
        )
        return api_response.jsonify()


"""
Quick notes: 

Task struct:

{
  "task": "example_task",
  "data": {
    "some_var_1": "",
    "user": "bob",
    "hash": "..."
  }
}

or a list version (later):

{
  [
    {
    "task": "example_task",
    "data": {
        "some_var_1": "",
        "user": "bob",
        "hash": "..."
        }
    }
  ]
}


Need an input model to match this, maybe a dataclass too.

One request = one task submitted. This is then encoded into msgpack,
and stored into redis to the correct implant's queue. 

Once that is hahed out, can complete thee POST task, and DELETE tasks endpoints. 

"""


# individual implaant
class ImplantTask(Resource):

    @implants_ns.doc(
        summary="Get next task implant",
        description="Retrieve the next task for the implant",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    def get(self, id):  # get one implant
        """
        [Needs marshalling & testing] Gets next task of implant. Task is returned as a base64 encoded, MSGPACK blob

        Meant to be called by listeners, to get the next task to forward to the implant.

        1. Spins up a new RedisImplantTaskService instance
        2. Dequeus next task
        3. Converts each task into base64 (From MSGPACK blob)
        4. Return response with task in data field: `{"task":"AABB=="}`
        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} requested a task for {id}")
        api_logger.info(
            f"Requesting a task for {id}",
            extra={
                "caller_ip": ip,
            },
        )

        its = RedisImplantTaskService(id)
        task = its.dequeue_task()

        if task == None:
            api_response = APIResponse(
                status="200",
                message="No task available",
                data=None,  # on no tasks, return a none
            )
            # api_logger.debug(f"API Response: {api_response}")
            return api_response.jsonify()

        # no task_id right now for simplicity, can be added later with adjustments if needed.
        # could account for sub tasks for nested implants by adding more fields, HOWEVER, this is not the place to do it
        task_b64_bytes = base64.b64encode(task)
        task_b64_str = task_b64_bytes.decode()

        data = {"task": task_b64_str}

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        # api_logger.debug(f"API Response: {api_response}")
        return api_response.jsonify()

    @implants_ns.doc(
        summary="Add a task",
        description="Add a task to a single implant by its unique ID. Data is supplied in the body of the request.",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    # @implants_ns.expect(implant_update_model) # add expected field here
    @implants_ns.expect(implant_task_model)
    def post(self, id):  # Create a new  command
        """
        Add a task to a single implant by its unique ID. Data is supplied in the body of the request.

        """
        ip = request.remote_addr

        api_logger.info(
            f"Enqueued a task for {id}",
            extra={
                "caller_ip": ip,
            },
        )

        try:
            # create task ID here
            # Need to stringify as msgpack needs it as a str, and it's stored as a str in mysql db
            task_uuid = str(uuid7())
            task = Task(
                # unwrap data into a dataclass
                **api.payload,
                # add on a task id
                uuid=task_uuid,
            )

        except TypeError as exc:
            api_response = APIResponse(
                status="400",
                message="Data failed validation",
                data=None,
            )
            return api_response.jsonify()

        # queue into redis
        task_service = RedisImplantTaskService(id)
        task_service.enqueue_task(task)

        # Log task into mysql
        # create blank row in mysql, get taskID (which mysql generates, sequentially), append to task.
        with get_mysql_session() as session:
            mysql_implant_service = MySQLImplantTaskService(
                implant_id=id, session=session
            )
            mysql_implant_service.create_entry(task_uuid=task_uuid)
            mysql_implant_service.update_request(task_uuid=task_uuid, request=task)

        api_response = APIResponse(
            status="200",
            message="Queued task successfully",
        )

        api_logger.info(
            f"Task {task_uuid} for {id} enqueued successfully",
            extra={
                "caller_ip": ip,
            },
        )

        return api_response.jsonify()


class ImplantTasks(Resource):
    @implants_ns.doc(
        summary="Gets all tasks of implant",
        description="Retrieve all tasks for the implant",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    def get(self, id):  # get one implant
        """
        [needs marshalling & testing] Peek all tasks of implant. Tasks are returned as a list of tasks,
        with the task being a base64 encoded MSGPACK blob.


        1. Gets how many tasks are queued
        2. Peeks that many tasks and returns them (as MSGPACK blob)
        3. Converts each task into base64
        4. Returns list of tasks `[{"task":"AABB=="},{"task":"AABB=="}]`

        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} requested all tasks for implant {id}")

        api_logger.info(
            f"Getting all tasks for implant {id}",
            extra={
                "caller_ip": ip,
            },
        )

        # get length of queue
        its = RedisImplantTaskService(id)
        task_queue_length = its.queue_length()

        tasks = its.peek_queue(task_queue_length)

        if tasks == None:
            api_response = APIResponse(
                status="200",
                message="Success",
                data=[],  # on no tasks, return an empty list
            )
            # api_logger.debug(f"API Response: {api_response}")
            return api_response.jsonify()

        # Add tasks to task lists and base64 encode
        data = []
        for task_bytes in tasks:
            # Base64 encode
            task_b64 = base64.b64encode(task_bytes).decode("ascii")

            # Wrap in dict
            data.append({"task": task_b64})

        api_response = APIResponse(
            status="200",
            message="Success",
            data=data,
        )
        # api_logger.debug(f"API Response: {api_response}")
        return api_response.jsonify()

    @implants_ns.doc(
        summary="Delete all the tasks of an implant",
        description="Delete all the tasks of an implant",
        params={"id": {"description": "Agent ID (64-bit integer)", "in": "path"}},
    )
    def delete(self, id):  #  Delete all tasks of agent
        """
        Delete all the tasks of an agent.

        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} is clearing task queue for implant {id}")
        api_logger.info(
            f"Deleting all tasks for implant {id}",
            extra={
                "caller_ip": ip,
            },
        )

        its = RedisImplantTaskService(id)
        its.clear_queue()

        api_response = APIResponse(
            status="200",
            message=f"Cleared all pending tasks from implant {id}",
        )

        api_logger.info(
            f"All tasks for implant {id} successfully deleted",
            extra={
                "caller_ip": ip,
            },
        )

        # api_logger.debug(f"API Response: {api_response}")
        return api_response.jsonify()


# Add the HelloWorld resource to the API
implants_ns.add_resource(Implants, "/")
implants_ns.add_resource(Implant, "/<int:id>")
implants_ns.add_resource(ImplantTask, "/<int:id>/task")
implants_ns.add_resource(ImplantTasks, "/<int:id>/tasks")

api.add_namespace(implants_ns)
