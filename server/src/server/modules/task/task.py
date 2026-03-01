"""
Task service, all the logic around tasks

Tasks are defined in dataclasses in schemas.implant.py

"""

from dataclasses import asdict

import msgpack
import structlog

from ...db.mysql_functions import MySQLImplantTaskService
from ...db.redis_functions import RedisImplantTaskService
from ...schemas.implant import Task, TaskDetail
from ...utils.checks import check_type

server_logger = structlog.getLogger("server")


class TaskService:
    """
    Task Structure
    {
        "task_uuid": "1234",
        "implant_uuid": 9999,
        "task": {
            "name": "cmd",
            "args": {
            "cli": "whoami"
            }
        }
    }

    """

    def __init__(self, task: Task, session):
        """_summary_

        Args:
            task (Task): A Task dataclass instance that has the current task in it
            session (_type_): A session for the MySQL db. Passed in, for consistent session usage (hit a bug where I
            was re-initing the session and it caused DB errors)
        """
        self.task = task
        self.session = session  # mysql session for consistent session useage

    @staticmethod
    def create_task(
        task_uuid: str,
        implant_uuid: str,
        task_name: str,
        task_args: dict,
        convert_to_msgpack: bool = False,
    ) -> Task | bytes:
        """
        Create a task payload.

        Builds a task structure containing the task UUID, target implant UUID,
        and task definition.

        Args:
            task_uuid: Unique identifier for the task.
            implant_uuid: Identifier of the intended target implant.
            task_name: Name of the task to execute.
            task_args: Dictionary of task-specific arguments.
            convert_to_msgpack: If True, return the task encoded as msgpack bytes.
                                If False (default), return the task as a Python dict.

        Returns:
            A Task dataclass instance , or msgpack-encoded bytes if
            convert_to_msgpack is True.
        """
        check_type(task_uuid, str, "task_uuid")
        check_type(implant_uuid, str, "implant_uuid")
        check_type(task_name, str, "task_name")
        check_type(task_args, dict, "task_args")
        check_type(convert_to_msgpack, bool, "convert_to_msgpack")

        # using dataclass for sanity here
        task_detail = TaskDetail(task_name=task_name, args=task_args)
        task = Task(task_uuid=task_uuid, implant_uuid=implant_uuid, task=task_detail)

        if convert_to_msgpack:
            task_dict = asdict(task)
            return msgpack.packb(task_dict)

        return task

    def get_as_dict(self) -> dict:
        """Returns task as dict."""
        try:
            return asdict(self.task)
        except Exception as exc:
            raise TypeError("Failed to convert Task to dict") from exc

    def get_as_msgpack(self) -> bytes:
        """Returns task as msgpack bytes."""
        try:
            task_dict = asdict(self.task)
            return msgpack.packb(task_dict)
        except (TypeError, ValueError) as exc:
            raise ValueError("Failed to serialize Task to msgpack") from exc

    def push_task(self):
        """Push a task to redis and save in SQL

        Args:
            task (Task): An instance of the dataclass "task" which defines the task structure
        """
        server_logger.debug("Pushing task to redis")
        self._save_to_mysql()
        self._save_to_redis()

    def _save_to_mysql(self):
        """Save task to MYSQL"""
        server_logger.debug("Pushing task to mysql")
        implant_uuid = self.task.implant_uuid
        task_uuid = self.task.task_uuid

        # Log task into mysql
        # create blank row in mysql, get taskID (which mysql generates, sequentially), append to task.
        # with get_mysql_session() as session:
        mysql_implant_service = MySQLImplantTaskService(implant_uuid=implant_uuid, session=self.session)
        mysql_implant_service.create_entry(task_uuid=task_uuid)
        mysql_implant_service.update_request(task_uuid=task_uuid, request=self.task)

    def _save_to_redis(self):
        """Push task to redis"""
        server_logger.debug("Pushing task to redis")
        implant_uuid = self.task.implant_uuid

        task_service = RedisImplantTaskService(implant_uuid)
        task_service.enqueue_task(self.task)


class TaskResponseService:
    """
    Task Response Structure
    {
        "task_uuid": <uuid>,
        "implant_uuid": <int>,
        "result": {
            "data_type": "binary" | "text",
            "data": <any>
        }
    }
    """

    ...


class MetadataService:
    """
    Metadata Structure
    {
        "implant_uuid": <uuid>,
        ...
    }
    """

    ...
