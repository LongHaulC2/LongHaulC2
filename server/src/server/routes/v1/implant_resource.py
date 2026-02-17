import base64
import logging

import msgpack
from edwh_uuid7 import uuid7
from flask import request
from flask_restx import Namespace, Resource, fields

from ...api_models.error import *
from ...api_models.implants import *
from ...db.mysql_connector import get_mysql_session
from ...instance import api
from ...modules.mysql_functions import (
    ImplantService,
    MySQLImplantTaskService,
    MySQLSearchService,
)
from ...modules.redis_functions import RedisImplantTaskService
from ...modules.task.task import TaskService
from ...schemas.implant import *
from ...utils.checks import check_type
from ...utils.response import APIResponse

implants_ns = Namespace("implants", description="Implant related operations")

api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")

from flask_restx import fields


# Error handlers - tldr, on exception, these will flag
# can remove try/except
@implants_ns.errorhandler(ValueError)
def handle_value_error(e):
    return {"status": "400", "message": str(e), "data": None}, 400


@implants_ns.errorhandler(Exception)
def handle_general_error(e):
    return {"status": "500", "message": "An internal error occurred", "data": None}, 500


implant_update_model = api.model(
    # these are req'd false, as they are not technically all needed to make the req
    "ImplantCreate",
    {
        "external_ip": fields.String(
            description="External IP address (IPv4/IPv6)",
            example="203.0.113.10",
            required=False,
        ),
        "internal_ip": fields.String(
            description="Internal IP address", example="10.0.0.15", required=False
        ),
        "listener": fields.String(
            description="Listener address (IP or DNS)",
            example="c2.example.com:443",
            required=False,
        ),
        "user": fields.String(
            description="User account name", example="SYSTEM", required=False
        ),
        "system_hostname": fields.String(
            description="Hostname of the system", example="WIN-ABC123", required=False
        ),
        "notes": fields.String(
            description="Operator notes", example="Initial check-in", required=False
        ),
        "process": fields.String(
            description="Process name", example="svchost.exe", required=False
        ),
        "pid": fields.Integer(description="Process ID", example=1234, required=False),
        "arch": fields.String(
            description="CPU architecture", example="x64", required=False
        ),
        "last_checkin": fields.String(
            description="Last check-in time (unix)", example="11223344", required=False
        ),
        "sleep_value": fields.Integer(
            description="Sleep interval in seconds", example=60, required=False
        ),
    },
)

# Task model
task_args_model = api.model(
    "TaskArgs",
    {
        "cli": fields.String(required=True, description="Command line to execute"),
    },
)

task_detail_model = api.model(
    "TaskDetail",
    {
        "task_name": fields.String(required=True, description="Task type/name"),
        "args": fields.Nested(
            task_args_model, required=True, description="Task arguments"
        ),
    },
)

implant_task_model = api.model(
    "Task",
    {
        # "task_uuid": fields.String(
        #     required=False,  # added by server
        #     description="Task UUID (assigned by server)",
        # ),
        "implant_uuid": fields.String(required=True, description="Implant UUID"),
        "task": fields.Nested(task_detail_model, required=True),
    },
)

search_model = api.model(
    "SearchModel",
    {
        "search_term": fields.String(required=True, description="Term to search for."),
    },
)


# Implant list
class Implants(Resource):
    # gets all  implants
    @implants_ns.doc(
        summary="Get all implants",
        description="Retrieve all implants the server knows about.",
        responses={
            200: "Success",
            404: "Implant not found",
            500: "Server Error",
            405: "Method Not Allowed",
        },
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
        responses=COMMON_ERRORS,
    )
    @implants_ns.response(
        200, "An entry was created in the database", IMPLANT_POST_SUCCESS_MODEL
    )
    @implants_ns.marshal_with(IMPLANT_POST_SUCCESS_MODEL)
    def post(self):
        """
        Create a new implant entry

        1. Gets a MYSQL Session

        2. Creates a new record in the 'implants' table

        3. Returns ID of new record in response

        Note: This will create "ghost" sessions with no metadata. Metadata gets updated when 'PUT /v1/api/implants/{uuid}/' is called.
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
            implant_uuid = implant_object.implant_uuid

        # need to get ID from DB
        data = {"uuid": implant_uuid}

        api_response = APIResponse(
            status="200",
            message=f"Implant {implant_uuid} created",
            data=data,
        )

        api_logger.info(
            f"Implant {implant_uuid} created",
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
        params={"uuid": {"description": "Agent ID (64-bit integer)", "in": "path"}},
        responses={
            200: "Success",
            404: "Implant not found",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    def get(self, uuid):  # get one implant
        """
        Gets one implant based on user supplied ID

        1. Gets a MYSQL Session

        2. Retrieves 1 record in 'implant' table based on ID

        3. Returns said data in JSON format.

        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} is retrieving implant {uuid}")

        api_logger.info(
            f"Getting implant {uuid} data",
            extra={
                "caller_ip": ip,
            },
        )

        check_type(uuid, str, "uuid")

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.get_by_id(uuid)
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
        params={"uuid": {"description": "Agent ID (64-bit integer)", "in": "path"}},
        responses={
            200: "Success",
            404: "Implant not found",
            400: "Bad Request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    @implants_ns.expect(implant_update_model)
    def put(self, uuid):  # update one implant based on ID
        """
        Update a single implant by its unique ID.
        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} is updating implant {uuid}")

        api_logger.info(
            f"Updating implant {uuid}'s data",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        # create dataclass from passed in data.

        implant_data = ImplantUpdate(**api.payload)
        implant_uuid = uuid

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implant_service.update(implant_uuid, implant_data)

        api_logger.info(
            f"Updated implant {uuid}'s data successfully",
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
        params={"uuid": {"description": "Agent ID (64-bit integer)", "in": "path"}},
        responses={
            200: "Success",
            404: "Implant not found",
            400: "Bad Request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    def delete(self, uuid):  # delete one implant based on ID
        """
        Deletes one implant based on user supplied ID

        1. Gets a MYSQL Session

        2. Deletes 1 record in 'implant' table based on ID

        3. Returns said data in JSON format.

        Note: Operationally, it might be best to not delete old records unless the user wants to.
            ID's are NOT reused after deleting, so if you delete record 1, said ID will NOT be reused upon calling `POST /v1/api/implants/`

        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} is deleting implant {uuid}")

        api_logger.info(
            f"Deleting implant {uuid}",
            extra={
                "caller_ip": ip,
            },
        )

        check_type(uuid, str, "uuid")

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.delete(uuid)

        # api_logger.info(f"Implant {uuid} deleted successfully")

        api_logger.info(
            f"Implant {uuid} deleted successfully",
            extra={
                "caller_ip": ip,
            },
        )

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
        params={"uuid": {"description": "Agent ID (64-bit integer)", "in": "path"}},
        responses={
            200: "Success",
            404: "Task not found",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    def get(self, uuid):  # get one implant
        """
        Gets next task of implant. Task is returned as a base64 encoded, MSGPACK blob

        This will DEQUEUE the next task, NOT peek.

        Meant to be called by listeners, to get the next task to forward to the implant.

        1. Spins up a new RedisImplantTaskService instance
        2. Dequeus next task
        3. Converts each task into base64 (From MSGPACK blob)
        4. Return response with task in data field: `{"task":"AABB=="}`
        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} requested a task for {uuid}")
        api_logger.info(
            f"Requesting a task for {uuid}",
            extra={
                "caller_ip": ip,
            },
        )

        check_type(uuid, str, "uuid")

        its = RedisImplantTaskService(uuid)
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
        params={"uuid": {"description": "Agent ID (64-bit integer)", "in": "path"}},
        responses={
            200: "Success",
            404: "Task not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    # @implants_ns.expect(implant_update_model) # add expected field here
    @implants_ns.expect(implant_task_model)
    def post(self, uuid):  # Create a new  command
        """
        Add a task to a single implant by its unique ID. Data is supplied in the body of the request.

        Returns a task_uuid for tracking the task:

        {"task_uuid": task_uuid}

        Note, this accepts a task in the form of a JSON body, OR a MSGPACK blob (with content-type header of application/msgpack). The server will convert the task into a MSGPACK blob before putting it in the queue, so either format can be used by the client.
        """
        ip = request.remote_addr

        api_logger.info(
            f"Enqueued a task for {uuid}",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        # tldr, allow messagepack, which may be passed sometimes, for binary data.

        if request.content_type == "application/msgpack":
            data = msgpack.unpackb(request.data, raw=False)
        else:
            data = request.json

        # create task ID here
        # Need to stringify as msgpack needs it as a str, and it's stored as a str in mysql db
        task_uuid = str(uuid7())
        task = Task(
            # unwrap data into a dataclass
            **data,
            # add on a task uuid
            task_uuid=task_uuid,
        )

        with get_mysql_session() as session:
            task_service = TaskService(task=task, session=session)
            task_service.push_task()

        task_uuid = task_service.task.task_uuid

        data = {"task_uuid": task_uuid}

        api_response = APIResponse(
            status="200", message="Queued task successfully", data=data
        )

        api_logger.info(
            f"Task {task_uuid} for {uuid} enqueued successfully",
            extra={
                "caller_ip": ip,
            },
        )

        return api_response.jsonify()


class ImplantTasks(Resource):
    @implants_ns.doc(
        summary="Peeks all currently queued tasks of implant",
        description="Peeks all currently queued tasks of implant",
        params={"uuid": {"description": "Agent ID (64-bit integer)", "in": "path"}},
        responses={
            200: "Success",
            404: "Task not found",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    def get(self, uuid):  # get one implant
        """
        Peek all currently queued tasks of implant. Tasks are returned as a list of tasks,
        with the task being a base64 encoded MSGPACK blob.


        1. Gets how many tasks are queued
        2. Peeks that many tasks and returns them (as MSGPACK blob)
        3. Converts each task into base64
        4. Returns list of tasks `[{"task":"AABB=="},{"task":"AABB=="}]`

        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} requested all tasks for implant {uuid}")

        api_logger.info(
            f"Getting all currently queued tasks for implant {uuid}",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        # get length of queue
        its = RedisImplantTaskService(uuid)
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
        summary="Delete all the currently queued tasks of an implant",
        description="Delete all the tasks of an implant",
        params={"uuid": {"description": "Agent ID (64-bit integer)", "in": "path"}},
        responses={
            200: "Success",
            404: "Task not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    def delete(self, uuid):  #  Delete all tasks of agent
        """
        Delete all the currently queued tasks of an agent.

        """
        ip = request.remote_addr
        # api_logger.info(f"{ip} is clearing task queue for implant {uuid}")
        api_logger.info(
            f"Deleting all tasks for implant {uuid}",
            extra={
                "caller_ip": ip,
            },
        )
        check_type(uuid, str, "uuid")

        its = RedisImplantTaskService(uuid)
        its.clear_queue()

        api_response = APIResponse(
            status="200",
            message=f"Cleared all pending tasks from implant {uuid}",
        )

        api_logger.info(
            f"All pending tasks for implant {uuid} successfully deleted",
            extra={
                "caller_ip": ip,
            },
        )

        # api_logger.debug(f"API Response: {api_response}")
        return api_response.jsonify()


"""
ImplantHistory, for getting task info.

GET /api/v1/{uuid}/tasks/history - Get a list of stored/historical tasks for the implant (uuid).

GET /api/v1/{uuid}/tasks/history/{task_id} - Get ONE stored/historical task for the implant (uuid).

"""
from flask_restx import reqparse

history_parser = reqparse.RequestParser()
history_parser.add_argument(
    "since",
    type=str,
    required=False,
    help="Return tasks with task_uuid greater than this UUIDv7",
)


class ImplantHistory(Resource):
    @implants_ns.doc(
        summary="Gets task history of implant from the DB.",
        description="Gets task history of implant from the DB. Provide 'since' parameter, with a uuid, to lookup since a previous uuid7, otherwise all history is returned",
        params={"uuid": {"description": "Agent ID (64-bit integer)", "in": "path"}},
        responses={
            200: "Success",
            404: "Not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    @implants_ns.expect(history_parser)
    def get(self, uuid):  # GET /api/v1/{uuid}/tasks/history
        """
        Gets ALL history of an implant from the DB.

        1. Queries MySQL DB
        2. Returns results as a list of tasks

        Ex:
        ```
        {
            "data": [
                {
                    "implant_uuid": 1,
                    "task_request": {
                        "data": {
                            "somevar": "1234"
                        },
                        "task": "cmd",
                        "uuid": "019b46f8-e066-76ff-bb2f-0a1f0daa318c"
                    },
                    "task_response": null,
                    "task_uuid": "019b46f8-e066-76ff-bb2f-0a1f0daa318c"
                },
            ]
        }
        ```

        """
        ip = request.remote_addr

        args = history_parser.parse_args()
        since = args.get("since")
        check_type(uuid, str, "uuid")

        #
        if since:

            api_logger.info(
                f"Requesting task history since {since} for {uuid}",
                extra={
                    "caller_ip": ip,
                },
            )

            # get data from db
            with get_mysql_session() as session:
                mysql_implant_service = MySQLImplantTaskService(
                    implant_uuid=uuid, session=session
                )
                tasks = mysql_implant_service.get_tasks_since_previous_uuid_of_implant(
                    implant_uuid=uuid, last_task_uuid=since
                )

            api_response = APIResponse(
                status="200",
                message="Success",
                data=tasks,
            )
            return api_response.jsonify()

        else:
            api_logger.info(
                f"Requesting task history for {uuid}",
                extra={
                    "caller_ip": ip,
                },
            )

            # get data from db
            with get_mysql_session() as session:
                mysql_implant_service = MySQLImplantTaskService(
                    implant_uuid=uuid, session=session
                )
                tasks = mysql_implant_service.get_all_tasks()

            api_response = APIResponse(
                status="200",
                message="Success",
                data=tasks,
            )
            return api_response.jsonify()


# Implant & task Search


# POST /api/v1/search/implants
class ImplantSearch(Resource):
    @implants_ns.doc(
        summary="Search for an implant with fields that match the supplied term.",
        description="Search for an implant with fields that match the supplied term. Returns a list of dicts, with implants that have said term in them.",
        responses={
            200: "Success",
            404: "Not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    @implants_ns.expect(search_model)
    def post(self):
        """
        Search for an implant with fields that match the supplied term. Returns a list of dicts, with implants that have said term in them.
        """
        ip = request.remote_addr

        implant_data = Search(**api.payload)

        api_logger.info(
            f"Searching implants with term: {implant_data.search_term}",
            extra={
                "caller_ip": ip,
            },
        )

        # get a seession
        with get_mysql_session() as session:
            implant_service = MySQLSearchService(session)
            search_results = implant_service.search_implants(
                search_term=implant_data.search_term
            )

        api_response = APIResponse(
            status="200",
            message="Success",
            data=search_results,
        )

        return api_response.jsonify()


# not implemented
class TaskSearch(Resource):
    @implants_ns.doc(
        summary="Search for an task with fields that match the supplied term.",
        description="Search for an implant with fields that match the supplied term. Returns a list of dicts, with implants that have said term in them.",
        responses={
            200: "Success",
            404: "Not found",
            400: "Bad request",
            500: "Server Error",
            405: "Method Not Allowed",
        },
    )
    @implants_ns.expect(search_model)
    def post(self):
        """
        Search for an task with fields that match the supplied term. Returns a list of dicts, with implants that have said term in them.
        """
        ip = request.remote_addr

        # create dataclass from passed in data.
        search_data = Search(**api.payload)

        api_logger.info(
            f"Searching implants with term: {search_data.search_term}",
            extra={
                "caller_ip": ip,
            },
        )

        # get a seession
        with get_mysql_session() as session:
            implant_service = MySQLSearchService(session)
            search_results = implant_service.search_tasks(
                search_term=search_data.search_term
            )

        api_response = APIResponse(
            status="200",
            message="Success",
            data=search_results,
        )

        return api_response.jsonify()


# Add the HelloWorld resource to the API
implants_ns.add_resource(Implants, "/")
implants_ns.add_resource(Implant, "/<string:uuid>")
implants_ns.add_resource(ImplantTask, "/<string:uuid>/task")
implants_ns.add_resource(ImplantTasks, "/<string:uuid>/tasks")
implants_ns.add_resource(ImplantHistory, "/<string:uuid>/tasks/history")

# search endpoints, maybe move to a new file
implants_ns.add_resource(ImplantSearch, "/search")
implants_ns.add_resource(TaskSearch, "/history/search")  # next


api.add_namespace(implants_ns)
