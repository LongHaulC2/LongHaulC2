from datetime import time
from sqlalchemy import exc
import logging
from dataclasses import asdict

from ..db.mysql_models import Implant, ImplantTask
from ..schemas.implant import ImplantUpdate, ImplantCreate, Task

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
            server_logger.error(f"Error: {e}")
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
            server_logger.error(f"Error: {e}")
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
            server_logger.error(f"Error: {e}")
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
            server_logger.error(f"Error: {e}")
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
            server_logger.error(f"Error: {e}")
            raise


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
        [not implemented]
        Update the task response for the given task ID (key).
        """
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
