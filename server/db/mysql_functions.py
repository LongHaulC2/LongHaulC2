import hashlib
import re
import time
from dataclasses import asdict
from typing import Literal

import bcrypt
import structlog
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..schemas.implant import Task
from ..utils.checks import check_type
from .mysql_models import ArtifactStore, FileStore, ImplantPayload, ImplantTask, UserLogin

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
        server_logger.debug("Retrieving all tasks for implant", implant_uuid=self.implant_uuid)

        tasks = self.session.query(ImplantTask).filter_by(implant_uuid=self.implant_uuid).all()

        return [
            {
                "task_uuid": task.task_uuid,
                "implant_uuid": task.implant_uuid,
                "task_request": task.task_request,
                "task_response": task.task_response,
            }
            for task in tasks
        ]

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
            }  # in api... data.task_x.whatever
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
        source_code_bytes: bytes,
        build_uuid: str = None,
    ) -> str:
        """
        Create an entry for a new payload.
        Calculates the MD5, stores it as bytes, but returns it as a Hex String.

        If build_uuid is provided, it checks for a pending row. If the pending row
        is already filled by a previous artifact, it inserts a new row.
        """
        server_logger.info("Registering new payload", payload_name=payload_name)

        check_type(payload_bytes, bytes, "payload_bytes")
        check_type(payload_name, str, "payload_name")

        # get hash of payload
        md5_obj = hashlib.md5(payload_bytes)
        hash_bytes = md5_obj.digest()
        hash_str = md5_obj.hexdigest()

        # ASYNC UPDATE PATH
        if build_uuid:
            server_logger.info("Finalizing build job with artifacts", build_uuid=build_uuid)

            # Find specifically the pending placeholder row (where bytes are None)
            pending_entry = (
                self.session.query(ImplantPayload).filter_by(build_uuid=build_uuid, payload_bytes=None).first()
            )

            if pending_entry:
                # We found the empty placeholder. Update it with the first artifact (e.g., .exe)
                pending_entry.payload_hash = hash_bytes
                pending_entry.payload_bytes = payload_bytes
                pending_entry.payload_source_code_bytes = source_code_bytes
                pending_entry.payload_name = payload_name
                pending_entry.build_status = "complete"

                self.session.commit()
                server_logger.info("Successfully updated placeholder build job", build_uuid=build_uuid, hash=hash_str)
                return hash_str

            # If we get here, the placeholder was already filled by a previous artifact.
            server_logger.info("Placeholder filled, creating additional artifact row", build_uuid=build_uuid)

        existing = self.session.query(ImplantPayload).filter_by(payload_hash=hash_bytes).first()

        if existing:
            server_logger.info("Payload with hash already exists. Returning existing hash.", hash=hash_str)
            return hash_str

        # Save to DB (Create new row)
        payload_entry = ImplantPayload(
            payload_hash=hash_bytes,
            payload_bytes=payload_bytes,
            payload_name=payload_name,
            payload_source_code_bytes=source_code_bytes,
            build_uuid=build_uuid,
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
        Updates build status for ALL rows associated with the build_uuid.
        """
        server_logger.info("Updating status of build", status=build_status, build_uuid=build_uuid)

        check_type(build_status, str, "status")
        check_type(build_uuid, str, "build_uuid")

        # UPDATE all rows matching the build_uuid
        updated_count = (
            self.session.query(ImplantPayload)
            .filter_by(build_uuid=build_uuid)
            .update({"build_status": build_status}, synchronize_session=False)
        )

        if updated_count == 0:
            server_logger.error("Could not find any build jobs to update", build_uuid=build_uuid)
            return

        self.session.commit()
        server_logger.info(
            "Successfully updated status", build_uuid=build_uuid, build_status=build_status, rows_affected=updated_count
        )

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
        server_logger.warning("No payload found for hash", payload_hash=payload_hash)
        return None

    def get_build_job_by_uuid(self, build_uuid: str) -> dict:
        """
        Retrieve a build job by its UUID
        """
        check_type(build_uuid, str, "build_uuid")

        server_logger.info("Retrieving build job status", build_uuid=build_uuid)

        payload = self.session.query(ImplantPayload).filter_by(build_uuid=build_uuid).first()  # .first()

        if payload:
            return payload.to_dict()
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


class MySQLImplantFileService:
    """
    Class for managing Files in sql
    """

    def __init__(self, session):
        self.session = session

    def register_file(self, file_name: str, file_bytes: bytes, file_uuid: str) -> str:
        """
        Create an entry for a new file
        Returns the UUID of the file added in the DB.
        """
        server_logger.info("Registering new file", file_name=file_name)

        check_type(file_bytes, bytes, "file_bytes")
        check_type(file_name, str, "file_name")

        # get hash of payload
        md5_obj = hashlib.md5(file_bytes)
        hash_bytes = md5_obj.digest()
        hash_str = md5_obj.hexdigest()

        # Save to DB
        file_entry = FileStore(
            file_hash=hash_bytes,
            file_bytes=file_bytes,
            file_name=file_name,
            file_uuid=file_uuid,
        )

        self.session.add(file_entry)
        self.session.commit()

        server_logger.info("Successfully committed file", file_hash=hash_str, file_uuid=file_uuid)

        return file_uuid

    def get_file_by_uuid(self, file_uuid: str):
        """
        Retrieve a payload object by file_uuid

        file_uuid: str
        """
        check_type(file_uuid, str, "file_uuid")

        server_logger.info("Retrieving payload for hash", file_uuid=file_uuid)

        file = self.session.query(FileStore).filter_by(file_uuid=file_uuid).first()

        if file:
            return file
        server_logger.warning("No file found for uuid", file_uuid=file_uuid)
        return None

    def get_all_files(self):
        """
        Retrieve ALL files currently registered in the database.
        Converts the binary hash in the DB to a hex string in the returned dict.
        """
        server_logger.info("Retrieving all payloads from database")

        payloads = self.session.query(FileStore).all()

        results = []
        for p in payloads:
            data = p.to_dict()
            # Convert the bytes hash to hex string for the final output
            if isinstance(data.get("file_hash"), bytes):
                data["file_hash"] = data["file_hash"].hex()

            # Remove file bytes cuz flask can't handle it as its bytes.
            # payloads can be downloaded with dedicated download endpoint.
            if "file_bytes" in data:
                del data["file_bytes"]

            results.append(data)

        return results

    def delete_file(self, file_uuid: str):
        """
        Delete a file by UUID.
        """
        check_type(file_uuid, str, "file_uuid")
        server_logger.info("Deleting payload", payloadfile_uuid_hash=file_uuid)

        file = self.session.query(FileStore).filter_by(file_uuid=file_uuid).first()

        if file:
            self.session.delete(file)
            self.session.commit()
            server_logger.info("file deleted successfully.")
        else:
            server_logger.warning("Attempted to delete non-existent file", file_uuid=file_uuid)


class MySQLArtifactService:
    def __init__(self, session):
        self.session = session

    def upsert_artifact(
        self, artifact_type: str, artifact_name: str, artifact_contents: str, artifact_uuid: str
    ) -> dict:
        check_type(artifact_type, str, "artifact_type")
        check_type(artifact_name, str, "artifact_name")
        check_type(artifact_contents, str, "artifact_contents")

        content_hash = hashlib.sha256(artifact_contents.encode()).hexdigest()
        now_ms = int(time.time() * 1000)

        existing = (
            self.session.query(ArtifactStore)
            .filter_by(artifact_type=artifact_type, artifact_name=artifact_name)
            .first()
        )

        if existing:
            if existing.content_hash == content_hash:
                return existing.to_dict()
            existing.artifact_contents = artifact_contents
            existing.content_hash = content_hash
            existing.updated_at = now_ms
            self.session.commit()
            server_logger.info("Artifact updated", artifact_name=artifact_name, artifact_type=artifact_type)
            return existing.to_dict()

        entry = ArtifactStore(
            artifact_uuid=artifact_uuid,
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            artifact_contents=artifact_contents,
            content_hash=content_hash,
            created_at=now_ms,
            updated_at=now_ms,
        )
        self.session.add(entry)
        self.session.commit()
        server_logger.info("Artifact created", artifact_name=artifact_name, artifact_type=artifact_type)
        return entry.to_dict()

    def get_artifact_by_name(self, artifact_type: str, artifact_name: str):
        check_type(artifact_type, str, "artifact_type")
        check_type(artifact_name, str, "artifact_name")
        return (
            self.session.query(ArtifactStore)
            .filter_by(artifact_type=artifact_type, artifact_name=artifact_name)
            .first()
        )

    def get_all_artifacts_by_type(self, artifact_type: str) -> list[dict]:
        check_type(artifact_type, str, "artifact_type")
        artifacts = self.session.query(ArtifactStore).filter_by(artifact_type=artifact_type).all()
        results = []
        for a in artifacts:
            d = a.to_dict()
            del d["artifact_contents"]
            results.append(d)
        return results

    def delete_artifact(self, artifact_type: str, artifact_name: str) -> bool:
        check_type(artifact_type, str, "artifact_type")
        check_type(artifact_name, str, "artifact_name")
        artifact = (
            self.session.query(ArtifactStore)
            .filter_by(artifact_type=artifact_type, artifact_name=artifact_name)
            .first()
        )
        if artifact:
            self.session.delete(artifact)
            self.session.commit()
            server_logger.info("Artifact deleted", artifact_name=artifact_name, artifact_type=artifact_type)
            return True
        server_logger.warning(
            "Artifact not found for deletion", artifact_name=artifact_name, artifact_type=artifact_type
        )
        return False


class MySQLUserService:
    """
    Class for managing Implant Payloads.

    Storage: Uses TINYBLOB(16) (Raw Bytes) for efficiency.
    Interface: Uses String (Hex) for human-readability.
    """

    def __init__(self, session):
        self.session = session

    def register_user(self, username: str, password: str) -> bool:
        """Register a user to the mysql db

        Args:
            username (str): username for new user
            password (str): password for new user

        Raises:
            IntegrityError: Returns false, does NOT raise.
            e: Raises error on any other exception

        Returns:
            bool: True = user was added succesfully, False = User already exists.
            Raises E on other errors
        """
        mysql_register_user_logger = server_logger.bind(username=username)

        check_type(username, str, "username")
        check_type(password, str, "password")

        mysql_register_user_logger.info("Registering user to DB")

        try:
            b_password = password.encode()
            password_hash = bcrypt.hashpw(b_password, bcrypt.gensalt())

            user = UserLogin(username=username, password_hash=password_hash)

            # Add and commit the task
            self.session.add(user)
            self.session.commit()
            return True

        except IntegrityError:
            # integ, such as if user already exists
            self.session.rollback()
            mysql_register_user_logger.warning("Registration failed: Username already exists")
            return False

        except SQLAlchemyError as e:
            # This triggers for other db errors
            self.session.rollback()
            mysql_register_user_logger.error("Database error occurred during registration", error=str(e))
            raise e

        except Exception as e:
            # catchall
            self.session.rollback()
            mysql_register_user_logger.error("An error occured", error=str(e))
            raise e

    def validate_password(self, username, password) -> bool:
        """Validate the incoming password against the listed user

        Args:
            username (str): username for new user
            password (str): password for new user

        Returns:
            bool: True = Success, password validated. False = Password not correct
        """
        mysql_valid_password_logger = server_logger.bind(username=username)

        check_type(username, str, "username")
        check_type(password, str, "password")

        try:
            # get hashed from db
            user_record = (
                self.session.query(UserLogin)
                .filter(
                    UserLogin.username == username,
                )
                .first()
            )

            if user_record is None:
                mysql_valid_password_logger.warning("User not found in DB")
                return False

            b_password = password.encode()
            b_stored_password = (user_record.password_hash).encode()
            return bcrypt.checkpw(b_password, b_stored_password)

        except Exception as e:
            mysql_valid_password_logger.error("An error occured", error=str(e))

    def delete_user(self, username: str) -> bool:
        """Delete a user from the mysql db

        Args:
            username (str): username for the user to delete

        Raises:
            SQLAlchemyError: Raises error on database exceptions
            Exception: Raises error on any other exception

        Returns:
            bool: True = user was deleted successfully, False = User not found.
        """
        mysql_delete_user_logger = server_logger.bind(username=username)

        check_type(username, str, "username")

        mysql_delete_user_logger.info("Attempting to delete user from DB")

        try:
            # Find the user in the db
            user_record = (
                self.session.query(UserLogin)
                .filter(
                    UserLogin.username == username,
                )
                .first()
            )

            # Prevent crash / False positive if user doesn't exist
            if user_record is None:
                mysql_delete_user_logger.warning("Deletion failed: User not found")
                return False

            # Delete the record and commit
            self.session.delete(user_record)
            self.session.commit()

            mysql_delete_user_logger.info("User deleted successfully")
            return True

        except SQLAlchemyError as e:
            # This triggers for unexpected db errors (connection drops, etc.)
            self.session.rollback()
            mysql_delete_user_logger.error("Database error occurred during deletion", error=str(e))
            raise e

        except Exception as e:
            self.session.rollback()
            mysql_delete_user_logger.error("An error occurred", error=str(e))
            raise e

    def create_initial_user(self, username, password) -> bool:
        """
        Creates initial user, only if there are no other users
        """
        check_type(username, str, "username")
        check_type(password, str, "password")

        # Use the session to perform the count
        user_count = self.session.query(UserLogin).count()

        if user_count == 0:
            server_logger.info("No users found. Creating initial admin user.")
            return self.register_user(username=username, password=password)

        return False
