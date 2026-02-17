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


# Error handlers
@implants_ns.errorhandler(ValueError)
def handle_value_error(e):
    return {"status": "400", "message": str(e), "data": None}, 400


@implants_ns.errorhandler(Exception)
def handle_general_error(e):
    return {"status": "500", "message": "An internal error occurred", "data": None}, 500


# Internal Task models for validation (kept local if needed for custom logic,
# otherwise rely on the models imported from ...api_models.implants)
# ... [Kept your existing internal helper models if you use them for logic outside of restx validation] ...


class Implants(Resource):
    @implants_ns.doc(
        summary="Get all implants",
        description="Retrieve all implants the server knows about.",
        responses=COMMON_ERRORS,
    )
    @implants_ns.response(200, "All implants were retrieved", IMPLANTS_GET_RESPONSE)
    @implants_ns.marshal_with(IMPLANTS_GET_RESPONSE)
    def get(self):
        """
        Gets all implants
        """
        ip = request.remote_addr
        api_logger.info("Getting all implants", extra={"caller_ip": ip})

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.get_all()
            data = [i.to_dict() for i in implants]

        return APIResponse(status="200", message="Success", data=data)

    @implants_ns.doc(
        summary="Create a new implant entry.",
        description="Create a new implant entry. Returns an Implant ID.",
        responses=COMMON_ERRORS,
    )
    @implants_ns.response(200, "Entry created", IMPLANTS_POST_RESPONSE)
    @implants_ns.marshal_with(IMPLANTS_POST_RESPONSE)
    def post(self):
        """
        Create a new implant entry
        """
        ip = request.remote_addr
        api_logger.info("Creating an implant", extra={"caller_ip": ip})

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            data = ImplantCreate()
            implant_object = implant_service.create(data)
            implant_uuid = implant_object.implant_uuid

        data = {"uuid": implant_uuid}

        api_logger.info(f"Implant {implant_uuid} created", extra={"caller_ip": ip})
        return APIResponse(
            status="200", message=f"Implant {implant_uuid} created", data=data
        )


class Implant(Resource):
    @implants_ns.doc(
        summary="Get implant",
        description="Retrieve a single implant by its unique ID.",
        params={"uuid": {"description": "Agent ID", "in": "path"}},
        responses=COMMON_ERRORS,
    )
    @implants_ns.response(200, "The implant was retrieved", IMPLANT_GET_RESPONSE)
    @implants_ns.marshal_with(IMPLANT_GET_RESPONSE)
    def get(self, uuid):
        """
        Gets one implant based on user supplied ID
        """
        ip = request.remote_addr
        api_logger.info(f"Getting implant {uuid} data", extra={"caller_ip": ip})

        check_type(uuid, str, "uuid")

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.get_by_id(uuid)
            data = implants.to_dict()

        return APIResponse(status="200", message="Success", data=data)

    @implants_ns.doc(
        summary="Update implant",
        description="Update a single implant by its unique ID.",
        params={"uuid": {"description": "Agent ID", "in": "path"}},
        consumes=["application/json"],
        responses=COMMON_ERRORS,
    )
    @implants_ns.expect(IMPLANT_PUT_INPUT)
    @implants_ns.response(200, "Success", IMPLANT_PUT_RESPONSE)
    @implants_ns.marshal_with(IMPLANT_PUT_RESPONSE)
    def put(self, uuid):
        """
        Update a single implant by its unique ID.
        """
        ip = request.remote_addr
        api_logger.info(f"Updating implant {uuid}'s data", extra={"caller_ip": ip})
        check_type(uuid, str, "uuid")

        implant_data = ImplantUpdate(**api.payload)

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implant_service.update(uuid, implant_data)

        api_logger.info(f"Updated implant {uuid} successfully", extra={"caller_ip": ip})
        return APIResponse(status="200", message="Success")

    @implants_ns.doc(
        summary="Delete implant",
        description="Delete a single implant by its unique ID.",
        params={"uuid": {"description": "Agent ID", "in": "path"}},
        responses=COMMON_ERRORS,
    )
    @implants_ns.response(200, "Success", IMPLANT_DELETE_RESPONSE)
    @implants_ns.marshal_with(IMPLANT_DELETE_RESPONSE)
    def delete(self, uuid):
        """
        Deletes one implant based on user supplied ID
        """
        ip = request.remote_addr
        api_logger.info(f"Deleting implant {uuid}", extra={"caller_ip": ip})

        check_type(uuid, str, "uuid")

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implant_service.delete(uuid)

        api_logger.info(f"Implant {uuid} deleted successfully", extra={"caller_ip": ip})
        return APIResponse(status=200, message="Implant deleted successfully")


class ImplantTask(Resource):
    @implants_ns.doc(
        summary="Add a task",
        description="Add a task to a single implant by its unique ID.",
        params={"uuid": {"description": "Agent ID", "in": "path"}},
        responses=COMMON_ERRORS,
        consumes=["application/json", "application/msgpack"],
    )
    @implants_ns.expect(IMPLANT_TASK_POST_INPUT, validate=False)
    @implants_ns.response(200, "The task was queued", IMPLANT_TASK_POST_RESPONSE)
    @implants_ns.marshal_with(IMPLANT_TASK_POST_RESPONSE)
    def post(self, uuid):
        """
        Add a task to a single implant by its unique ID.
        """
        ip = request.remote_addr
        api_logger.info(f"Enqueued a task for {uuid}", extra={"caller_ip": ip})
        check_type(uuid, str, "uuid")

        if request.content_type == "application/msgpack":
            data = msgpack.unpackb(request.data, raw=False)
        else:
            data = request.json

        task_uuid = str(uuid7())
        task = Task(**data, task_uuid=task_uuid)

        with get_mysql_session() as session:
            task_service = TaskService(task=task, session=session)
            task_service.push_task()

        task_uuid = task_service.task.task_uuid
        data = {"task_uuid": task_uuid}

        api_logger.info(
            f"Task {task_uuid} for {uuid} enqueued", extra={"caller_ip": ip}
        )
        return APIResponse(status="200", message="Queued task successfully", data=data)


class ImplantTasks(Resource):
    @implants_ns.doc(
        summary="Peeks all currently queued tasks of implant",
        description="Peeks all currently queued tasks of implant",
        params={"uuid": {"description": "Agent ID", "in": "path"}},
        responses=COMMON_ERRORS,
    )
    @implants_ns.response(
        200, "A list of tasks for the current implant", IMPLANT_TASKS_GET_RESPONSE
    )
    @implants_ns.marshal_with(IMPLANT_TASKS_GET_RESPONSE)
    def get(self, uuid):
        """
        Peek all currently queued tasks of implant.
        """
        ip = request.remote_addr
        api_logger.info(
            f"Getting queued tasks for implant {uuid}", extra={"caller_ip": ip}
        )
        check_type(uuid, str, "uuid")

        its = RedisImplantTaskService(uuid)
        task_queue_length = its.queue_length()
        tasks = its.peek_queue(task_queue_length)

        if tasks is None:
            return APIResponse(status="200", message="Success", data=[])

        data = []
        for task_bytes in tasks:
            task_b64 = base64.b64encode(task_bytes).decode("ascii")
            data.append({"task": task_b64})

        return APIResponse(status="200", message="Success", data=data)

    @implants_ns.doc(
        summary="Delete all the currently queued tasks of an implant",
        description="Delete all the tasks of an implant",
        params={"uuid": {"description": "Agent ID", "in": "path"}},
        responses=COMMON_ERRORS,
    )
    @implants_ns.response(
        200, "The tasks for the implant were cleared", IMPLANT_TASKS_DELETE_RESPONSE
    )
    @implants_ns.marshal_with(IMPLANT_TASKS_DELETE_RESPONSE)
    def delete(self, uuid):
        """
        Delete all the currently queued tasks of an agent.
        """
        ip = request.remote_addr
        api_logger.info(
            f"Deleting all tasks for implant {uuid}", extra={"caller_ip": ip}
        )
        check_type(uuid, str, "uuid")

        its = RedisImplantTaskService(uuid)
        its.clear_queue()

        api_logger.info(
            f"All pending tasks for {uuid} deleted", extra={"caller_ip": ip}
        )
        return APIResponse(
            status="200", message=f"Cleared all pending tasks from implant {uuid}"
        )


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
        description="Gets task history.",
        params={"uuid": {"description": "Agent ID", "in": "path"}},
        responses=COMMON_ERRORS,
    )
    @implants_ns.expect(history_parser)
    @implants_ns.response(200, "History retrieved", IMPLANT_HISTORY_GET_RESPONSE)
    @implants_ns.marshal_with(IMPLANT_HISTORY_GET_RESPONSE)
    def get(self, uuid):
        """
        Gets ALL history of an implant from the DB.
        """
        ip = request.remote_addr
        args = history_parser.parse_args()
        since = args.get("since")
        check_type(uuid, str, "uuid")

        with get_mysql_session() as session:
            mysql_implant_service = MySQLImplantTaskService(
                implant_uuid=uuid, session=session
            )
            if since:
                api_logger.info(
                    f"Requesting history since {since} for {uuid}",
                    extra={"caller_ip": ip},
                )
                tasks = mysql_implant_service.get_tasks_since_previous_uuid_of_implant(
                    implant_uuid=uuid, last_task_uuid=since
                )
            else:
                api_logger.info(
                    f"Requesting history for {uuid}", extra={"caller_ip": ip}
                )
                tasks = mysql_implant_service.get_all_tasks()

        return APIResponse(status="200", message="Success", data=tasks)


class ImplantSearch(Resource):
    @implants_ns.doc(
        summary="Search for an implant",
        description="Search for an implant with fields that match the supplied term.",
        responses=COMMON_ERRORS,
    )
    @implants_ns.expect(IMPLANT_SEARCH_POST_INPUT)
    @implants_ns.response(
        200, "A list of all resulting implants", IMPLANT_SEARCH_POST_RESPONSE
    )
    @implants_ns.marshal_with(IMPLANT_SEARCH_POST_RESPONSE)
    def post(self):
        """
        Search for an implant
        """
        ip = request.remote_addr
        implant_data = Search(**api.payload)
        api_logger.info(
            f"Searching implants: {implant_data.search_term}", extra={"caller_ip": ip}
        )

        with get_mysql_session() as session:
            implant_service = MySQLSearchService(session)
            search_results = implant_service.search_implants(
                search_term=implant_data.search_term
            )

        return APIResponse(status="200", message="Success", data=search_results)


class TaskSearch(Resource):
    @implants_ns.doc(
        summary="Search for a task",
        description="Search for a task with fields that match the supplied term.",
        responses=COMMON_ERRORS,
    )
    @implants_ns.expect(TASK_SEARCH_POST_INPUT)
    @implants_ns.response(200, "Search results", TASK_SEARCH_POST_RESPONSE)
    @implants_ns.marshal_with(TASK_SEARCH_POST_RESPONSE)
    def post(self):
        """
        Search for a task
        """
        ip = request.remote_addr
        search_data = Search(**api.payload)
        api_logger.info(
            f"Searching tasks: {search_data.search_term}", extra={"caller_ip": ip}
        )

        with get_mysql_session() as session:
            implant_service = MySQLSearchService(session)
            search_results = implant_service.search_tasks(
                search_term=search_data.search_term
            )

        return APIResponse(status="200", message="Success", data=search_results)


implants_ns.add_resource(Implants, "/")
implants_ns.add_resource(Implant, "/<string:uuid>")
implants_ns.add_resource(ImplantTask, "/<string:uuid>/task")
implants_ns.add_resource(ImplantTasks, "/<string:uuid>/tasks")
implants_ns.add_resource(ImplantHistory, "/<string:uuid>/tasks/history")
implants_ns.add_resource(ImplantSearch, "/search")
implants_ns.add_resource(TaskSearch, "/history/search")

api.add_namespace(implants_ns)
