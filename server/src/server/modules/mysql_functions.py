import hashlib
import logging
from dataclasses import asdict

from edwh_uuid7 import uuid7
from sqlalchemy import exc, inspect, text

from ..db.mysql_models import Implant, ImplantPayload, ImplantTask, Listener
from ..schemas.implant import ImplantCreate, ImplantUpdate, Task
from ..schemas.listeners import ListenerCreate, ListenerUpdate
from ..utils.checks import check_type

server_logger = logging.getLogger("server")


class ImplantService:
    def __init__(self, session):
        self.session = session

    def create(self, data: ImplantCreate) -> Implant:
        """
        Create a new implant entry.
        """
        server_logger.debug("Creating new implant entry")
        check_type(data, ImplantCreate, "data")

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

    def get_by_id(self, implant_uuid: int) -> Implant | None:
        """
        Retrieve an implant by primary key.
        """
        check_type(implant_uuid, int, "implant_uuid")

        try:
            server_logger.debug(
                f"Retrieving implant {implant_uuid} from MYSQL Database"
            )
            return self.session.query(Implant).get(implant_uuid)

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
            # server_logger.debug(f"Retrieving all implants from MYSQL Database")

            return self.session.query(Implant).all()

        except exc.SQLAlchemyError as sqle:
            server_logger.error(f"SQLAlchemy Error: {sqle}")
            self.session.rollback()
            raise
        except Exception as e:
            server_logger.error(f"{self.__class__.__name__} Error: {e}")
            raise

    def update(self, implant_uuid: int, data: ImplantUpdate) -> Implant | None:
        """
        Update an implant by primary key.
        """

        check_type(implant_uuid, int, "implant_uuid")
        check_type(data, ImplantUpdate, "data")

        server_logger.debug(
            f"Updating implant {implant_uuid} in MYSQL Database with {data}"
        )
        try:
            implant = self.get_by_id(implant_uuid)
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

    def delete(self, implant_uuid: int) -> bool:
        """
        Delete an implant by primary key.
        """
        server_logger.debug(f"Deleting implant {implant_uuid} in MYSQL Database")
        check_type(implant_uuid, int, "implant_uuid")

        try:
            implant = self.get_by_id(implant_uuid)
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


class ListenerService:
    def __init__(self, session):
        self.session = session

    def create(self, data: ListenerCreate) -> Listener:
        """
        Create a new listener entry.
        """
        server_logger.debug("Creating new listener entry")

        check_type(data, ListenerCreate, "data")

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

    def get_by_id(self, listener_id: str) -> Listener | None:
        """
        Retrieve an implant by primary key.
        """
        check_type(listener_id, str, "listener_id")

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

    def update(self, listener_id: str, data: ListenerUpdate) -> Listener | None:
        """
        Update an implant by primary key.
        """
        server_logger.debug(
            f"Updating implant {listener_id} in MYSQL Database with {data}"
        )
        check_type(listener_id, str, "listener_id")
        check_type(data, ListenerUpdate, "data")

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

    def set_active(self, listener_id: str, active: bool):
        server_logger.debug(
            f"Setting listener {listener_id} state: active={active} in MYSQL Database"
        )
        check_type(listener_id, str, "listener_id")
        check_type(active, bool, "active")

        listener = self.get_by_id(listener_id)
        if not listener:
            return None

        listener.listener_active = active
        self.session.commit()

    def delete(self, listener_id: str) -> bool:
        """
        Delete an implant by primary key.
        """
        server_logger.debug(f"Deleting listener {listener_id} in MYSQL Database")
        check_type(listener_id, str, "listener_id")

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


class MySQLSearchService:
    def __init__(self, session):
        self.session = session

    def search_implants(self, search_term: str) -> list[dict]:
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
        check_type(search_term, str, "search_term")
        query = (
            self.session.query(Implant)
            .filter(
                text(
                    "MATCH(external_ip, internal_ip, listener, user, system_hostname, notes, process, arch, implant_uuid) AGAINST(:term IN NATURAL LANGUAGE MODE)"
                )
            )
            .params(term=search_term)
        )

        # Execute the query and get the results
        results = query.all()

        # Convert each Implant instance to a dictionary using the `to_dict` method
        results_dict = [implant.to_dict() for implant in results]

        return results_dict

    def search_tasks(self, search_term: str) -> list[dict]:
        """
        Search for, and return all tasks that have the search_term string in them. Uses MySQL's FULLTEXT on
        the following fields: `task_request, task_response, task_uuid`.

        Note: Longer/wordlike searches work best, ex:
            Target: `scan`
            scan    -> DOES WORK
            sc      -> DOES NOT WORK

        :param search_term: The term to match against the tasks.
        :type search_term: str

        :return: A list of tasks that match the query.
        :rtype: list[dict[Any, Any]]
        """
        check_type(search_term, str, "search_term")
        query = (
            self.session.query(ImplantTask)
            .filter(
                text(
                    "MATCH(task_request_text, task_response_text, task_uuid, implant_uuid) AGAINST(:term IN NATURAL LANGUAGE MODE)"
                )
            )
            .params(term=search_term)
        )

        # Execute the query and get the results
        results = query.all()

        # Convert each ImplantTask instance to a dictionary using the `to_dict` method
        results_dict = [task.to_dict() for task in results]

        return results_dict


class MySQLImplantTaskService:
    """
    Class for managing tasks? Have this handle sql and redis updates?
    """

    def __init__(self, implant_uuid: str, session):
        self.implant_uuid = implant_uuid
        self.session = session

        check_type(implant_uuid, str, "implant_uuid")

    def create_entry(self, task_uuid: str):
        """
        Create an entry for the task in mysql

        task_uuid: UUID of task

        returns task id

        """
        check_type(task_uuid, str, "task_uuid")

        if not isinstance(task_uuid, str):
            server_logger.warning(
                f"Task UUID {task_uuid} is type {type(task_uuid)}, converting to string."
            )
            task_uuid = str(task_uuid)

        server_logger.info(f"Adding task to MySQL for implant {task_uuid}")
        task = ImplantTask(
            implant_uuid=self.implant_uuid,
            task_uuid=task_uuid,
            task_request=None,
            task_response=None,
        )

        # Add and commit the task
        self.session.add(task)
        self.session.commit()

    def update_request(self, task_uuid: str, request: Task):
        """
        Update the task request for the given task ID (key).

        task_uuid: (string) UUID of the task - Prefferably a string, not a UUID object. The code *does* convert to a str though.
        request: A dataclass instance of Task.
        """
        server_logger.info(f"Updating MySQL task request for implant {task_uuid}")

        check_type(task_uuid, str, "task_uuid")
        check_type(request, Task, "request")

        # convert the request Task object to a dict, recursively.
        data = asdict(request)

        if not isinstance(task_uuid, str):
            server_logger.warning(
                f"Task UUID {task_uuid} is type {type(task_uuid)}, converting to string."
            )
            task_uuid = str(task_uuid)

        # Fetch the task by key
        task = (
            self.session.query(ImplantTask)
            .filter_by(task_uuid=task_uuid, implant_uuid=self.implant_uuid)
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
                f"Task with ID {task_uuid} not found for agent {self.implant_uuid}."
            )

    def update_response(self, task_uuid: str, response: dict):
        """
        [Works, but undefined response structure.]
        Update the task response for the given task ID (key).

        task_uuid: (string) UUID of the task to update - Prefferably a string, not a UUID object. The code *does* convert to a str though.
        response: The response of the implant. Currently, there is no defined structure/dataclass for responses.
        """
        server_logger.info(f"Updating MySQL task response for implant {task_uuid}")

        check_type(task_uuid, str, "task_uuid")
        check_type(response, Task, "response")

        if not isinstance(task_uuid, str):
            server_logger.warning(
                f"Task UUID {task_uuid} is type {type(task_uuid)}, converting to string."
            )
            task_uuid = str(task_uuid)

        # Fetch the task by key
        task = (
            self.session.query(ImplantTask)
            .filter_by(id=task_uuid, implant_uuid=self.implant_uuid)
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
                f"Task with ID {task_uuid} not found for agent {self.implant_uuid}."
            )

    def get_all_tasks(self) -> list:
        """
        Retrieve all tasks for the given implant_uuid from MySQL and return them as a list of dictionaries.
        Returns:
            List of task dictionaries.
        """
        server_logger.info(f"Retrieving all tasks for implant {self.implant_uuid}")

        tasks = (
            self.session.query(ImplantTask)
            .filter_by(implant_uuid=self.implant_uuid)
            .all()
        )

        task_list = [
            {
                "task_uuid": task.task_uuid,
                "implant_uuid": task.implant_uuid,
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
                    "implant_uuid": self.implant_uuid,
                    "task_response": r["result"],
                }
                for r in responses
            ],
        )

        self.session.commit()

    def get_tasks_since_previous_uuid_of_implant(
        self,
        implant_uuid: str,
        last_task_uuid: str,
        # limit=1000,
    ) -> list:
        check_type("implant_uuid", str, "implant_uuid")
        check_type("last_task_uuid", str, "last_task_uuid")

        results = (
            self.session.query(ImplantTask)
            .filter(
                ImplantTask.implant_uuid == implant_uuid,
                ImplantTask.task_uuid > last_task_uuid,
            )
            .order_by(ImplantTask.task_uuid.asc())
            # .limit(limit)
            .all()
        )  # .to_dict()

        # loop over objects (all returns objects) and return dicts
        return [r.to_dict() for r in results]


class MySQLImplantPayloadService:
    """
    Class for managing Implant Payloads.

    Storage: Uses TINYBLOB(16) (Raw Bytes) for efficiency.
    Interface: Uses String (Hex) for human-readability.
    """

    def __init__(self, session):
        self.session = session

    def register_payload(
        self,
        payload_name: str,
        payload_bytes: bytes,
        listener_uuid: str,
        source_code_bytes: bytes,
    ) -> str:
        """
        Create an entry for a new payload.
        Calculates the MD5, stores it as bytes, but returns it as a Hex String.

        returns: The MD5 hex string of the payload
        """
        server_logger.info(f"Registering new payload for listener {listener_uuid}")

        check_type(payload_bytes, bytes, "payload_bytes")
        check_type(listener_uuid, str, "listener_uuid")
        check_type(payload_name, str, "payload_name")

        # get hash of payload
        md5_obj = hashlib.md5(payload_bytes)

        # We need the RAW BYTES for the Database (TINYBLOB)
        hash_bytes = md5_obj.digest()

        # We need the HEX STRING for the return value/logs
        hash_str = md5_obj.hexdigest()

        existing = (
            self.session.query(ImplantPayload)
            .filter_by(payload_hash=hash_bytes)
            .first()
        )

        if existing:
            server_logger.info(
                f"Payload with hash {hash_str} already exists. Returning existing hash."
            )
            return hash_str

        # Save to DB (using hash_bytes)
        payload_entry = ImplantPayload(
            payload_hash=hash_bytes,
            payload_bytes=payload_bytes,
            payload_listener_uuid=listener_uuid,
            payload_name=payload_name,
            payload_source_code_bytes=source_code_bytes,
        )

        self.session.add(payload_entry)
        self.session.commit()

        server_logger.info(f"Successfully committed payload: {hash_str}")

        return hash_str

    def get_payload_by_hash(self, payload_hash: str):
        """
        Retrieve a payload object by its MD5 HEX STRING.
        The function encodes the string to bytes to query the DB.

        payload_hash: str (32 char hex string)
        """
        check_type(payload_hash, str, "payload_hash")

        server_logger.info(f"Retrieving payload for hash {payload_hash}")

        try:
            # Encode string -> bytes for the lookup
            hash_bytes = bytes.fromhex(payload_hash)
        except ValueError:
            server_logger.error(f"Invalid hex string provided: {payload_hash}")
            return None

        payload = (
            self.session.query(ImplantPayload)
            .filter_by(payload_hash=hash_bytes)
            .first()
        )

        if payload:
            return payload
        else:
            server_logger.warning(f"No payload found for hash {payload_hash}")
            return None

    def get_payloads_by_listener(self, listener_uuid: str) -> list:
        """
        Retrieve all payloads for a listener.
        Converts the binary hash in the DB to a hex string in the returned dict.
        """
        check_type(listener_uuid, str, "listener_name")

        server_logger.info(f"Retrieving all payloads for listener {listener_uuid}")

        payloads = (
            self.session.query(ImplantPayload)
            .filter_by(payload_listener=listener_uuid)
            .all()
        )

        results = []
        for p in payloads:
            data = p.to_dict()
            # Convert the bytes hash to hex string for the final output
            if isinstance(data.get("payload_hash"), bytes):
                data["payload_hash"] = data["payload_hash"].hex()
            results.append(data)

        return results

    def get_all_payloads(self):
        """
        Retrieve ALL payloads currently registered in the database.
        Converts the binary hash in the DB to a hex string in the returned dict.
        """
        server_logger.info("Retrieving all payloads from database")

        payloads = self.session.query(ImplantPayload).all()

        results = []
        for p in payloads:
            data = p.to_dict()
            # Convert the bytes hash to hex string for the final output
            if isinstance(data.get("payload_hash"), bytes):
                data["payload_hash"] = data["payload_hash"].hex()

            # Remove payload bytes cuz flask can't handle it as its bytes.
            # payloads canbe downloaded with dedicated donwload endpoint.
            if "payload_bytes" in data:
                del data["payload_bytes"]
            if "payload_source_code_bytes" in data:
                del data["payload_source_code_bytes"]

            # Optional: Don't send the massive 4GB bytes field if this is just for a UI list
            # data.pop("payload_bytes", None)

            results.append(data)

        return results

    def delete_payload(self, payload_hash: str):
        """
        Delete a payload by hash (Hex String).
        """
        check_type(payload_hash, str, "payload_hash")
        server_logger.info(f"Deleting payload {payload_hash}")

        try:
            # Encode string -> bytes for the lookup
            hash_bytes = bytes.fromhex(payload_hash)
        except ValueError:
            server_logger.error(f"Invalid hex string provided: {payload_hash}")
            return

        payload = (
            self.session.query(ImplantPayload)
            .filter_by(payload_hash=hash_bytes)
            .first()
        )

        if payload:
            self.session.delete(payload)
            self.session.commit()
            server_logger.info("Payload deleted successfully.")
        else:
            server_logger.warning(
                f"Attempted to delete non-existent payload {payload_hash}."
            )
