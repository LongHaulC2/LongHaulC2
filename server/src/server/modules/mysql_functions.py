from datetime import time
from sqlalchemy import exc, text
import logging
from dataclasses import asdict

from ..db.mysql_models import Implant, ImplantTask, Listener
from ..schemas.implant import (
    ImplantUpdate,
    ImplantCreate,
    Task,
)
from ..schemas.listeners import ListenerCreate, ListenerUpdate
from edwh_uuid7 import uuid7

server_logger = logging.getLogger("server")


class ImplantService:
    def __init__(self, session):
        self.session = session

    def create(self, data: ImplantCreate) -> Implant:
        """
        Create a new implant entry.
        """
        server_logger.debug("Creating new implant entry")
        try:
            implant = Implant(**vars(data))
            self.session.add(implant)
            self.session.commit()
            self.session.refresh(implant)
            return implant

        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise

        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def get_by_id(self, implant_id: int) -> Implant | None:
        """
        Retrieve an implant by primary key.
        """
        try:
            server_logger.debug(f"Retrieving implant {implant_id} from MYSQL Database")
            return self.session.query(Implant).get(implant_id)

        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def get_all(self):
        """
        Gets all implants in the table.
        """
        try:
            server_logger.debug(f"Retrieving all implants from MYSQL Database")

            return self.session.query(Implant).all()

        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def update(self, implant_id: int, data: ImplantUpdate) -> Implant | None:
        """
        Update an implant by primary key.
        """
        server_logger.debug(
            f"Updating implant {implant_id} in MYSQL Database with {data}"
        )
        try:
            implant = self.get_by_id(implant_id)
            if not implant:
                return None

            # if value is not supplied, DO NOT update it in DB.
            # AKA, only apply supplied values.
            # NOTE: If you get an "vars() argument must have __dict__ attribute", that means you passed in a dict, NOT a ImplantUpdate dataclass as the
            # function requires.
            for field, value in vars(data).items():
                if value is not None:
                    setattr(implant, field, value)

            self.session.commit()
            return implant
        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def delete(self, implant_id: int) -> bool:
        """
        Delete an implant by primary key.
        """
        server_logger.debug(f"Deleting implant {implant_id} in MYSQL Database")

        try:
            implant = self.get_by_id(implant_id)
            if not implant:
                return False

            self.session.delete(implant)
            self.session.commit()
            return True
        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def search(self, search_term: str) -> list[dict]:
        """
        Search for, and return all implants that have the search_term string in them. Uses MySQL's FULLTEXT on
        the following fields: `external_ip, internal_ip, listener, user, system_hostname, notes, process, arch`

        Note: Longer/wordlike searches work best, ex:
            Target: `msiexec.exe`
            msi     -> DOES NOT WORK
            msiexec -> DOES WORK

        :param search_term: The term to match against the implants.
        :type search_term: str

        :return: A list of implants that match the query.
        :rtype: list[dict[Any, Any]]
        """

        query = (
            self.session.query(Implant)
            .filter(
                text(
                    "MATCH(external_ip, internal_ip, listener, user, system_hostname, notes, process, arch) AGAINST(:term IN NATURAL LANGUAGE MODE)"
                )
            )
            .params(term=search_term)
        )

        # Execute the query and get the results
        results = query.all()

        # Convert each Implant instance to a dictionary using the `to_dict` method
        results_dict = [implant.to_dict() for implant in results]

        return results_dict


class ListenerService:
    def __init__(self, session):
        self.session = session

    def create(self, data: ListenerCreate) -> Listener:
        """
        Create a new listener entry.
        """
        server_logger.debug("Creating new listener entry")
        try:
            listener = Listener(**vars(data))
            self.session.add(listener)
            self.session.commit()
            self.session.refresh(listener)
            return listener

        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise

        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def get_by_id(self, listener_id: uuid7) -> Listener | None:
        """
        Retrieve an implant by primary key.
        """
        try:
            server_logger.debug(
                f"Retrieving listener {listener_id} from MYSQL Database"
            )
            return self.session.query(Listener).get(listener_id)

        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def get_all(self):
        """
        Gets all implants in the table.
        """
        try:
            server_logger.debug(f"Retrieving all listeners from MYSQL Database")

            return self.session.query(Listener).all()

        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def update(self, listener_id: uuid7, data: ListenerUpdate) -> Listener | None:
        """
        Update an implant by primary key.
        """
        server_logger.debug(
            f"Updating implant {listener_id} in MYSQL Database with {data}"
        )
        try:
            listener = self.get_by_id(listener_id)
            if not listener:
                return None

            # if value is not supplied, DO NOT update it in DB.
            # AKA, only apply supplied values.
            # NOTE: If you get an "vars() argument must have __dict__ attribute", that means you passed in a dict, NOT a ImplantUpdate dataclass as the
            # function requires.
            for field, value in vars(data).items():
                if value is not None:
                    setattr(listener, field, value)

            self.session.commit()
            return listener
        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def set_active(self, listener_id: uuid7, active: bool):
        server_logger.debug(
            f"Setting listener {listener_id} state: active={active} in MYSQL Database"
        )

        listener = self.get_by_id(listener_id)
        if not listener:
            return None

        listener.listener_active = active
        self.session.commit()

    def delete(self, listener_id: uuid7) -> bool:
        """
        Delete an implant by primary key.
        """
        server_logger.debug(f"Deleting listener {listener_id} in MYSQL Database")

        try:
            listener = self.get_by_id(listener_id)
            if not listener:
                return False

            self.session.delete(listener)
            self.session.commit()
            return True
        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    # implement later. Just need to add index code & use "listener" instead of "implant"
    # def search(self, search_term: str) -> list[dict]:
    #     """
    #     Search for, and return all implants that have the search_term string in them. Uses MySQL's FULLTEXT on
    #     the following fields: `external_ip, internal_ip, listener, user, system_hostname, notes, process, arch`

    #     Note: Longer/wordlike searches work best, ex:
    #         Target: `msiexec.exe`
    #         msi     -> DOES NOT WORK
    #         msiexec -> DOES WORK

    #     :param search_term: The term to match against the implants.
    #     :type search_term: str

    #     :return: A list of implants that match the query.
    #     :rtype: list[dict[Any, Any]]
    #     """

    #     query = (
    #         self.session.query(Implant)
    #         .filter(
    #             text(
    #                 "MATCH(external_ip, internal_ip, listener, user, system_hostname, notes, process, arch) AGAINST(:term IN NATURAL LANGUAGE MODE)"
    #             )
    #         )
    #         .params(term=search_term)
    #     )

    #     # Execute the query and get the results
    #     results = query.all()

    #     # Convert each Implant instance to a dictionary using the `to_dict` method
    #     results_dict = [implant.to_dict() for implant in results]

    #     return results_dict


class MySQLImplantTaskService:
    """
    Class for managing tasks? Have this handle sql and redis updates?
    """

    def __init__(self, implant_id: int, session):
        self.implant_id = implant_id
        self.session = session

    def create_entry(self, task_uuid):
        """
        Create an entry for the task in mysql

        returns task id

        """
        server_logger.info(f"Adding task to MySQL for implant {task_uuid}")
        task = ImplantTask(
            implant_id=self.implant_id,
            task_uuid=task_uuid,
            task_request=None,
            task_response=None,
        )

        # Add and commit the task
        self.session.add(task)
        self.session.commit()

    def update_request(self, task_uuid, request: Task):
        """
        Update the task request for the given task ID (key).

        task_uuid: The UUID of the task
        request: A dataclass instance of Task.
        """
        server_logger.info(f"Updating MySQL task request for implant {task_uuid}")

        # convert the request Task object to a dict, recursively.
        data = asdict(request)

        # Fetch the task by key
        task = (
            self.session.query(ImplantTask)
            .filter_by(task_uuid=task_uuid, implant_id=self.implant_id)
            .first()
        )

        if task:
            # Update the task request field
            task.task_request = data
            # Commit the update
            self.session.commit()
        else:
            # If the task is not found, log an error or raise an exception
            raise ValueError(
                f"Task with ID {task_uuid} not found for agent {self.implant_id}."
            )

    def update_response(self, task_uuid, response: dict):
        """
        [Works, but undefined response structure.]
        Update the task response for the given task ID (key).

        task_uuid: UUID of the task to update
        response: The response of the implant. Currently, there is no defined structure/dataclass for responses.
        """
        server_logger.info(f"Updating MySQL task response for implant {task_uuid}")

        # Fetch the task by key
        task = (
            self.session.query(ImplantTask)
            .filter_by(id=task_uuid, implant_id=self.implant_id)
            .first()
        )

        if task:
            # Update the task response field
            task.task_response = response
            # Commit the update
            self.session.commit()
        else:
            # If the task is not found, log an error or raise an exception
            raise ValueError(
                f"Task with ID {task_uuid} not found for agent {self.implant_id}."
            )

    def get_all_tasks(self) -> list:
        """
        Retrieve all tasks for the given implant_id from MySQL and return them as a list of dictionaries.
        Returns:
            List of task dictionaries.
        """
        server_logger.info(f"Retrieving all tasks for implant {self.implant_id}")

        tasks = (
            self.session.query(ImplantTask).filter_by(implant_id=self.implant_id).all()
        )

        task_list = [
            {
                "task_uuid": task.task_uuid,
                "implant_id": task.implant_id,
                "task_request": task.task_request,
                "task_response": task.task_response,
            }
            for task in tasks
        ]

        return task_list

    def bulk_update_responses(self, responses: list[dict]):
        """
        responses = [
            {
                "task_uuid": "...",
                "task_response": {...}
            },
            ...
        ]
        """
        if not responses:
            return

        self.session.bulk_update_mappings(
            ImplantTask,
            [
                {
                    "task_uuid": r["task_uuid"],
                    "implant_id": self.implant_id,
                    "task_response": r["task_response"],
                }
                for r in responses
            ],
        )

        self.session.commit()
