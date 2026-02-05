import logging

import httpx
import structlog

from client.src.client.utils.url import generate_url

from ..utils.checks import check_type

server_log = logging.getLogger("server")

api_log = logging.getLogger("api")


async def queue_task(implant_uuid: str, task: dict):
    """
    Submit a new task to be executed by a specific implant.

    Args:
        implant_uuid (str): The unique identifier (UUID) of the target implant.
        task (dict): The task definition. Expected to contain 'taskname' (str) and 'args' (dict).

    Returns:
        httpx.Response: The HTTP response object. A successful task queueing (200 OK) returns the task details.
        Example return data structure (response.json()):
        {
            "taskname": "shell",
            "args": {"cli": "whoami"},
            "status": "queued"
        }
    """
    check_type(implant_uuid, str, "implant_uuid")
    # switch task to dataclass
    check_type(task, dict, "task")

    url = generate_url(f"/api/v1/implants/{implant_uuid}/task")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="POST", url=url, implant_uuid=implant_uuid, task=task
    )
    api_log.debug(f"Queueing a task for implant")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=task)
        return response


async def update_implant(implant_uuid: str, data: dict):
    """
    Update the metadata or status information for a specific implant.

    Args:
        implant_uuid (str): The unique identifier (UUID) of the implant to update.
        data (dict): The update data, such as notes or status changes.

    Returns:
        httpx.Response: The HTTP response object.
        Example return data structure (200 OK):
        {
            "status": "success",
            "message": "Implant updated"
        }
    """
    check_type(implant_uuid, str, "implant_uuid")
    check_type(data, dict, "data")

    url = generate_url(f"/api/v1/implants/{implant_uuid}")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="GET", url=url, implant_uuid=implant_uuid
    )
    api_log.debug(f"Updating data for implant")

    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data)
        return response


async def get_implant_data(implant_uuid: str) -> dict:
    """
    Retrieve detailed information and current status for a specific implant.

    Args:
        implant_uuid (str): The unique identifier (UUID) of the implant.

    Returns:
        dict: A dictionary containing the implant's metadata and check-in history.
        Example structure:
        {
            "implant_uuid": 00000000-0000-0000-0000-000000000000,
            "hostname": "WORKSTATION-01",
            "last_checkin": "2023-10-27T10:00:00Z",
            "ip_address": "192.168.1.5"
        }
    """
    check_type(implant_uuid, str, "implant_uuid")

    url = generate_url(f"/api/v1/implants/{implant_uuid}")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="GET", url=url, implant_uuid=implant_uuid
    )
    api_log.debug(f"Getting data for implant")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return data


async def get_all_implant_data() -> dict:
    """
    Retrieve a list of all implants currently registered in the database.

    Returns:
        dict: A dictionary (or list of dicts) containing data for all implants.
        Example structure:
        [
            {"implant_uuid": "uuid-1", "hostname": "PC-A"},
            {"implant_uuid": "uuid-2", "hostname": "PC-B"}
        ]
    """
    url = generate_url("/api/v1/implants/")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)
    api_log.debug(f"Getting all implant data")

    # get implants
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data


async def get_all_listener_data() -> dict:
    """
    Retrieve a list of all active and inactive listeners.

    Returns:
        dict: A dictionary containing the configuration and status of all listeners.
        Example structure:
        [
            {"listener_uuid": 00000000-0000-0000-0000-000000000000, "listener_name": "HTTP-80", "status": "running"},
            {"listener_uuid": 00000000-0000-0000-0000-000000000000, "listener_name": "HTTPS-443", "status": "stopped"}
        ]
    """
    url = generate_url("/api/v1/listeners/")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)
    api_log.debug(f"Getting all listener data")

    # get implants
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data


async def get_listener_data(listener_uuid: str) -> dict:
    """
    Retrieve the configuration and status details for a specific listener.

    Args:
        listener_uuid (str): The unique identifier (UUID) of the listener.

    Returns:
        dict: Information regarding the listener host, port, type, and profile.
        Example structure:
        {
            "listener_name": "C2_Primary",
            "listener_host": "0.0.0.0",
            "listener_port": 8080,
            "listener_type": "http",
            "listener_profile_name": "default",
            "listener_profile_contents": "http-get {\n  ... \n}..."
        }
    """
    check_type(listener_uuid, str, "listener_uuid")

    url = generate_url(f"/api/v1/listeners/{listener_uuid}")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="GET", url=url, listener_uuid=listener_uuid
    )
    api_log.debug(f"Getting data for listener")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return data


async def stop_listener(listener_uuid: str) -> dict:
    """
    Terminate/Stop a running listener.

    Args:
        listener_uuid (str): The unique identifier (UUID) of the listener to stop.

    Returns:
        dict: A status message indicating if the listener was successfully stopped.
        Example structure:
        {
            "status": "success",
            "message": "Listener stopped"
        }
    """
    check_type(listener_uuid, str, "listener_uuid")

    url = generate_url(f"/api/v1/listeners/{listener_uuid}")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="DELETE", url=url, listener_uuid=listener_uuid
    )
    api_log.debug(f"Getting data for listener")

    async with httpx.AsyncClient() as client:
        response = await client.delete(url)
        data = response.json()
        return data


async def start_listener(
    listener_host: str,
    listener_port: int,
    listener_type: str,
    listener_name: str,
    listener_notes: str,
    listener_profile_name: str,
    listener_profile_contents: str,
) -> dict:
    """
    Start/Spawn a new listener with the specified configuration.

    Args:
        listener_host (str): Host/IP the listener will bind to.
        listener_port (int): Port for the listener.
        listener_type (str): Type of listener (e.g., 'http').
        listener_name (str): Friendly name for the listener.
        listener_notes (str): Additional notes.
        listener_profile_name (str): Malleable C2 profile name.
        listener_profile_contents (str): The raw string content of the C2 profile.

    Returns:
        dict: The created listener's details, including its new UUID.
        Example structure:
        {
            "listener_uuid": "019baffa-c8c7-76ff-a40d-d2ec6c99306e",
            "status": "running"
        }
    """

    # --- validate inputs ---
    check_type(listener_host, str, "listener_host")
    check_type(listener_port, int, "listener_port")
    check_type(listener_type, str, "listener_type")
    check_type(listener_name, str, "listener_name")
    check_type(listener_notes, str, "listener_notes")
    check_type(listener_profile_name, str, "listener_profile_name")
    check_type(listener_profile_contents, str, "listener_profile_contents")

    listener_request_data = {
        "listener_host": listener_host,
        "listener_port": listener_port,
        "listener_type": listener_type,
        "listener_name": listener_name,
        "listener_notes": listener_notes,
        "listener_profile_name": listener_profile_name,
        "listener_profile_contents": listener_profile_contents,
    }

    # --- normalize / preprocess ---
    listener_host = listener_host.strip()
    listener_name = listener_name.strip()

    url = generate_url(f"/api/v1/listeners/")

    # --- core logic placeholder ---
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="POST", url=url)
    api_log.debug(f"Getting data for listener")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=listener_request_data)
        data = response.json()
        return data


async def build_implant(implant_name, listener_dict, output_format) -> dict:
    """
    Submit a task to build a new implant payload tailored to a specific listener.

    Args:
        implant_name (str): The name to give the built implant.
        listener_dict: dict of listener data: {
            listener_uuid: {"listener_variant":""},
            listener_uuid: {"listener_variant":""},

        }
            implant_listener_uuid (str): The UUID of the listener this implant should connect to.
            implant_variant (str): The variant or architecture of the implant.
        output_format (str): The desired file format (e.g., 'exe', 'dll').

    Returns:
        dict: Details of the build job, including a 'build_uuid' to track status.
        Example structure:
        {
            "build_uuid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "status": "building"
        }
    """

    # --- validate inputs ---
    check_type(implant_name, str, "implant_name")
    # check_type(implant_listener_uuid, str, "implant_listener_uuid")
    # check_type(implant_variant, str, "implant_variant")
    check_type(output_format, str, "output_format")
    check_type(listener_dict, dict, "listener_dict")

    build_request_data = {
        # "implant_name": implant_name,
        "listener_dict": listener_dict,
        "implant_name": implant_name,
        "output_format": output_format,
    }

    url = generate_url(f"/api/v1/build/")

    # --- core logic placeholder ---
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="POST", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=build_request_data, timeout=60)
        data = response.json()
        return data


async def get_build_status(build_uuid: str) -> dict:
    """
    Get the current status of an ongoing or completed build job.

    Args:
        build_uuid (str): The unique identifier (UUID) for the build job.

    Returns:
        dict: Information regarding build status, logs, and if finished, the payload hash.
        Example structure:
        {
            "build_uuid": 00000000-0000-0000-0000-000000000000,
            "status": "completed",
            "payload_hash": "abc123def..."
        }
    """
    url = generate_url(f"/api/v1/build/jobs/{build_uuid}")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data


async def get_payload_data() -> dict:
    """
    Retrieve a list of all built payloads available in the database.

    Returns:
        dict: Metadata for all payloads.
        Example structure:
        [
            {"payload_hash": "abcdabcdabcd==", "implant_name": "Alpha", "build_date": "..."},
            {"payload_hash": "abcdabcdabcd==", "implant_name": "Beta", "build_date": "..."}
        ]
    """
    url = generate_url(f"/api/v1/build/")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data


async def get_payload_bytes(payload_hash: str) -> dict:
    """
    Retrieve the actual compiled binary/bytes of a specific payload.

    Args:
        payload_hash (str): The unique hash identifying the payload.

    Returns:
        bytes: The raw binary content of the payload, or None if download fails.
        Example structure:
        b'\\x4d\\x5a\\x90...' (The actual executable bytes)
    """
    url = generate_url(f"/api/v1/build/{payload_hash}")
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            print(f"Error downloading: {response.text}")
            return None

        # Note: Use .content for binary, not .json()
        return response.content


async def get_payload_source_bytes(payload_hash: str) -> dict:
    """
    Retrieve the source code (typically as a zip) for a specific built payload.

    Args:
        payload_hash (str): The unique hash identifying the payload.

    Returns:
        bytes: The raw bytes of the source code archive, or None if download fails.
        Example structure:
        b'PK\\x03\\x04...' (The bytes of a ZIP file)
    """
    url = generate_url(f"/api/v1/build/{payload_hash}/source")
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            print(f"Error downloading: {response.text}")
            return None

        # Note: Use .content for binary, not .json()
        return response.content


async def get_implant_task_history_since_uuid(
    implant_uuid: str, since_task_uuid: str
) -> dict:
    """
    Retrieve task history for an implant that occurred after a specific task UUID.

    Args:
        implant_uuid (str): The unique identifier of the implant.
        since_task_uuid (str): The task UUID to start the history from.

    Returns:
        dict: A list of tasks and their results following the 'since' UUID.
        Example structure:
        [
            {"task_uuid":"", "implant_uuid": 9999, "result":{"data_type":binary|text, "data":"somedata"}}
        ]
    """
    url_params = {"since": since_task_uuid}
    url = generate_url(
        f"/api/v1/implants/{implant_uuid}/tasks/history", params=url_params
    )

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data


async def get_implant_task_history(implant_uuid: str) -> dict:
    """
    Retrieve the full task and execution history for a specific implant.

    Args:
        implant_uuid (str): The unique identifier (UUID) of the implant.

    Returns:
        dict: A collection of all tasks issued to and returned by the implant.
        Example structure:
        [
            {"task_uuid":"", "implant_uuid": 9999, "result":{"data_type":binary|text, "data":"somedata"}},
            {"task_uuid":"", "implant_uuid": 9999, "result":{"data_type":binary|text, "data":"somedata"}}
        ]
    """
    url = generate_url(f"/api/v1/implants/{implant_uuid}/tasks/history")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data
