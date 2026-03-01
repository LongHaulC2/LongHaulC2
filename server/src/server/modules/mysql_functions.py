import hashlib
import re
from dataclasses import asdict
from typing import Literal

import structlog
from sqlalchemy import or_, text

from ..db.mysql_models import ImplantPayload, ImplantTask
from ..schemas.implant import Task
from ..utils.checks import check_type

server_logger = structlog.getLogger("server")


class MySQLSearchService:
    def __init__(self, session):
        self.session = session

    def _prepare_boolean_term(self, search_term: str) -> str:
        """
        Strips MySQL boolean operators from user input to prevent syntax errors,
        then appends a wildcard (*) to each word to enable partial/prefix matching.
        """
        # Strip reserved characters used by MySQL Boolean Mode
        safe_term = re.sub(r"[+\-><\(\)~*\"@]+", " ", search_term).strip()
        if not safe_term:
            return ""

        # "scan network" becomes "scan* network*"
        return " ".join(f"{word}*" for word in safe_term.split())

    # deprecated, implants moved to neo4j
    # def search_implants(self, search_term: str) -> list[dict]:
    #     """
    #     Hybrid search for Implants.
    #     - Exact/Prefix matching for IPs and UUIDs.
    #     - FULLTEXT BOOLEAN matching for text fields (allows partial matches like 'msi' -> 'msiexec').
    #     """
    #     check_type(search_term, str, "search_term")

    #     like_term = f"%{search_term}%"
    #     bool_term = self._prepare_boolean_term(search_term)

    #     # Build the exact/LIKE filters for identifiers (Fast B-Tree searches)
    #     filters = [
    #         Implant.implant_uuid.like(
    #             like_term
    #         ),  # Using like() in case they search a partial UUID
    #         Implant.external_ip.like(like_term),
    #         Implant.internal_ip.like(like_term),
    #     ]

    #     # Add the FULLTEXT filter for text fields (Must match schema indexes)
    #     if bool_term:
    #         filters.append(
    #             text(
    #                 "MATCH(listener, user, system_hostname, notes, process, arch) AGAINST(:bool_term IN BOOLEAN MODE)"
    #             )
    #         )

    #     # Apply the OR condition
    #     query = self.session.query(Implant).filter(or_(*filters))

    #     # Bind the boolean term safely if it exists
    #     if bool_term:
    #         query = query.params(bool_term=bool_term)

    #     results = query.all()
    #     return [implant.to_dict() for implant in results]

    def search_tasks(self, search_term: str) -> list[dict]:
        """
        Hybrid search for Tasks.
        - Exact/Prefix matching for UUIDs.
        - FULLTEXT BOOLEAN matching for task request/response text.
        """
        check_type(search_term, str, "search_term")

        like_term = f"%{search_term}%"
        bool_term = self._prepare_boolean_term(search_term)

        filters = [
            ImplantTask.task_uuid.like(like_term),
            ImplantTask.implant_uuid.like(like_term),
        ]

        if bool_term:
            filters.append(text("MATCH(task_request_text, task_response_text) AGAINST(:bool_term IN BOOLEAN MODE)"))

        query = self.session.query(ImplantTask).filter(or_(*filters))

        if bool_term:
            query = query.params(bool_term=bool_term)

        results = query.all()
        return [task.to_dict() for task in results]


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
                "Task UUID is incorrect type, converting to string", task_uuid=task_uuid, type=type(task_uuid)
            )
            task_uuid = str(task_uuid)

        server_logger.info("Adding task to MySQL for implant", task_uuid=task_uuid)
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

        task_uuid: (string) UUID of the task - Prefferably a string, not a UUID object. The code
        *does* convert to a str though.

        request: A dataclass instance of Task.
        """
        server_logger.info("Updating MySQL task request for implant", task_uuid=task_uuid)

        check_type(task_uuid, str, "task_uuid")
        check_type(request, Task, "request")

        # convert the request Task object to a dict, recursively.
        data = asdict(request)

        if not isinstance(task_uuid, str):
            server_logger.warning(
                "Task UUID is incorrect type, converting to string", task_uuid=task_uuid, type=type(task_uuid)
            )
            task_uuid = str(task_uuid)

        # Fetch the task by key
        task = self.session.query(ImplantTask).filter_by(task_uuid=task_uuid, implant_uuid=self.implant_uuid).first()

        if task:
            # Update the task request field
            task.task_request = data
            # Commit the update
            self.session.commit()
        else:
            # If the task is not found, log an error or raise an exception
            raise ValueError(f"Task with ID {task_uuid} not found for agent {self.implant_uuid}.")

    def update_response(self, task_uuid: str, response: dict):
        """
        [Works, but undefined response structure.]
        Update the task response for the given task ID (key).

        task_uuid: (string) UUID of the task to update - Prefferably a string, not a UUID object.
        The code *does* convert to a str though.

        response: The response of the implant. Currently, there is no defined structure/dataclass for responses.
        """
        server_logger.info("Updating MySQL task response for implant", task_uuid=task_uuid)

        check_type(task_uuid, str, "task_uuid")
        check_type(response, Task, "response")

        if not isinstance(task_uuid, str):
            server_logger.warning(
                "Task UUID is incorrect type, converting to string.", task_uuid=task_uuid, type=type(task_uuid)
            )
            task_uuid = str(task_uuid)

        # Fetch the task by key
        task = self.session.query(ImplantTask).filter_by(id=task_uuid, implant_uuid=self.implant_uuid).first()

        if task:
            # Update the task response field
            task.task_response = response
            # Commit the update
            self.session.commit()
        else:
            # If the task is not found, log an error or raise an exception
            raise ValueError(f"Task with ID {task_uuid} not found for agent {self.implant_uuid}.")

    def get_all_tasks(self) -> list:
        """
        Retrieve all tasks for the given implant_uuid from MySQL and return them as a list of dictionaries.
        Returns:
            List of task dictionaries.
        """
        server_logger.info("Retrieving all tasks for implant", implant_uuid=self.implant_uuid)

        tasks = self.session.query(ImplantTask).filter_by(implant_uuid=self.implant_uuid).all()

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

    def get_task_by_uuid(self, task_uuid: str) -> dict | None:
        """
        Retrieve a specific task by its UUID for the current implant.

        task_uuid: (string) UUID of the task to retrieve.
        Returns: A dictionary containing the task data, or None if not found.
        """
        check_type(task_uuid, str, "task_uuid")

        if not isinstance(task_uuid, str):
            server_logger.warning(
                "Task UUID is incorrect type, converting to string.", task_uuid=task_uuid, type=type(task_uuid)
            )
            task_uuid = str(task_uuid)

        server_logger.info("Retrieving task for implant", task_uuid=task_uuid, implant_uuid=self.implant_uuid)

        # Fetch the task by task_uuid and implant_uuid
        task = self.session.query(ImplantTask).filter_by(task_uuid=task_uuid, implant_uuid=self.implant_uuid).first()

        if task:
            # match the dict mapping of get_all_tasks method instead of returning an object
            return {
                "task_uuid": task.task_uuid,
                "implant_uuid": task.implant_uuid,
                "task_request": task.task_request,
                "task_response": task.task_response,
            }
        return None


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
        # listener_uuid: str,
        source_code_bytes: bytes,
        build_uuid: str = None,
    ) -> str:
        """
        Create an entry for a new payload.
        Calculates the MD5, stores it as bytes, but returns it as a Hex String.

        If build_uuid is provided, it updates that existing 'pending' row with the artifacts.

        returns: The MD5 hex string of the payload
        """
        server_logger.info("Registering new payload", payload_name=payload_name)

        check_type(payload_bytes, bytes, "payload_bytes")
        # check_type(listener_uuid, str, "listener_uuid")
        check_type(payload_name, str, "payload_name")

        # get hash of payload
        md5_obj = hashlib.md5(payload_bytes)

        # We need the RAW BYTES for the Database (TINYBLOB)
        hash_bytes = md5_obj.digest()

        # We need the HEX STRING for the return value/logs
        hash_str = md5_obj.hexdigest()

        # ASYNC UPDATE PATH
        # If this is the result of an async build job, update the placeholder row.
        if build_uuid:
            server_logger.info("Finalizing build job with artifacts", build_uuid=build_uuid)

            # Find the pending row by UUID
            payload_entry = self.session.query(ImplantPayload).filter_by(build_uuid=build_uuid).first()

            if payload_entry:
                # Update the existing row with the real data
                payload_entry.payload_hash = hash_bytes
                payload_entry.payload_bytes = payload_bytes
                payload_entry.payload_source_code_bytes = source_code_bytes
                payload_entry.payload_name = payload_name
                # payload_entry.payload_listener_uuid = listener_uuid
                payload_entry.build_status = "complete"  # Mark job as done

                self.session.commit()
                server_logger.info("Successfully updated build job", build_uuid=build_uuid, hash=hash_str)
                return hash_str
            else:
                server_logger.error(
                    "Build UUID was provided, but no matching row was found. Falling back to new insert.",
                    build_uuid=build_uuid,
                )

        # STANDARD INSERT PATH
        # Deduplication check: See if this file hash already exists
        existing = self.session.query(ImplantPayload).filter_by(payload_hash=hash_bytes).first()

        if existing:
            server_logger.info("Payload with hash already exists. Returning existing hash.", hash=hash_str)
            return hash_str

        # Save to DB (Create new row)
        payload_entry = ImplantPayload(
            payload_hash=hash_bytes,
            payload_bytes=payload_bytes,
            # payload_listener_uuid=listener_uuid,
            payload_name=payload_name,
            payload_source_code_bytes=source_code_bytes,
            # If we fell through to here, it's a direct upload or successful "immediate" build
            build_status="complete",
        )

        self.session.add(payload_entry)
        self.session.commit()

        server_logger.info("Successfully committed payload", payload_hash=hash_str)

        return hash_str

    def register_build_start(self, payload_name: str, build_uuid: str) -> str:
        """
        Creates an initial 'placeholder' entry for a new payload build.
        Generates a UUID to track the build job, allowing the API to return immediately
        while the actual compilation happens in the background.

        returns: The new Build UUID (str)
        """
        server_logger.info("Registering new build task for payload", payload_name=payload_name)

        # check_type(listener_uuid, str, "listener_uuid")
        check_type(payload_name, str, "payload_name")

        # Create the row with the UUID, but leave the payload bytes Empty/Null for now.
        # Note: Ensure your SQL Model 'ImplantPayload' allows payload_bytes to be Nullable
        payload_entry = ImplantPayload(
            build_uuid=build_uuid,  # Saving the UUID instead of a Hash
            payload_name=payload_name,
            # payload_listener_uuid=None,  # switch to a list of uuids
            payload_bytes=None,  # Data not ready yet
            payload_source_code_bytes=None,  # Data not ready yet
        )

        self.session.add(payload_entry)
        self.session.commit()

        server_logger.info("Successfully initiated build job", build_uuid=build_uuid)

        return build_uuid

    def update_build_status(self, build_uuid, build_status: Literal["building", "complete", "failed"]):
        """
        Updates build status by querying the EXISTING row.
        """
        server_logger.info("Updating status of build", status=build_status, build_uuid=build_uuid)

        check_type(build_status, str, "status")
        check_type(build_uuid, str, "build_uuid")

        # FETCH the existing row
        payload_entry = self.session.query(ImplantPayload).filter_by(build_uuid=build_uuid).first()

        if not payload_entry:
            server_logger.error("Could not find build job to update", build_uuid=build_uuid)
            return

        # UPDATE the field on the existing object
        payload_entry.build_status = build_status

        # COMMIT (SQLAlchemy detects the change on the dirty object)
        self.session.commit()

        server_logger.info("Successfully updated status", build_uuid=build_uuid, build_status=build_status)

    def get_payload_by_hash(self, payload_hash: str):
        """
        Retrieve a payload object by its MD5 HEX STRING.
        The function encodes the string to bytes to query the DB.

        payload_hash: str (32 char hex string)
        """
        check_type(payload_hash, str, "payload_hash")

        server_logger.info("Retrieving payload for hash", payload_hash=payload_hash)

        try:
            # Encode string -> bytes for the lookup
            hash_bytes = bytes.fromhex(payload_hash)
        except ValueError:
            server_logger.error("Invalid hex string provided", payload_hash=payload_hash)
            return None

        payload = self.session.query(ImplantPayload).filter_by(payload_hash=hash_bytes).first()

        if payload:
            return payload
        else:
            server_logger.warning("No payload found for hash", payload_hash=payload_hash)
            return None

    def get_build_job_by_uuid(self, build_uuid: str) -> dict:
        """
        Retrieve a build job by its UUID
        """
        check_type(build_uuid, str, "build_uuid")

        server_logger.info("Retrieving build job status", build_uuid=build_uuid)

        payload = self.session.query(ImplantPayload).filter_by(build_uuid=build_uuid).first()

        if payload:
            return payload.to_dict()
        else:
            server_logger.warning("No build job found", build_uuid=build_uuid)
            return None

    def get_payloads_by_listener(self, listener_uuid: str) -> list:
        """
        Retrieve all payloads for a listener.
        Converts the binary hash in the DB to a hex string in the returned dict.
        """
        check_type(listener_uuid, str, "listener_name")

        server_logger.info("Retrieving all payloads for listener", listener_uuid=listener_uuid)

        payloads = self.session.query(ImplantPayload).filter_by(payload_listener=listener_uuid).all()

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
        server_logger.info("Deleting payload", payload_hash=payload_hash)

        try:
            # Encode string -> bytes for the lookup
            hash_bytes = bytes.fromhex(payload_hash)
        except ValueError:
            server_logger.error("Invalid hex string provided", payload_hash=payload_hash)
            return

        payload = self.session.query(ImplantPayload).filter_by(payload_hash=hash_bytes).first()

        if payload:
            self.session.delete(payload)
            self.session.commit()
            server_logger.info("Payload deleted successfully.")
        else:
            server_logger.warning("Attempted to delete non-existent payload", payload_hash=payload_hash)
