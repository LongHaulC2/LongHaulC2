from typing import Any

import httpx
import msgpack
import orjson  # trying for speed
import structlog

from client.src.client.utils.url import generate_url

from ..utils.checks import check_type

server_log = structlog.getLogger("server")
api_log = structlog.getLogger("api")

# Global persistent client to maintain connection pooling for efficiency.
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """
    Lazy-load the httpx.AsyncClient to ensure it is created within the active event loop.

    Returns:
        httpx.AsyncClient: The global asynchronous HTTP client instance.
    """
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client


async def safe_api_request(
    method: str,
    endpoint: str,
    return_type: str = "json",
    log_context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Global helper to handle all API requests, standardize logging, and gracefully swallow network errors.

    Args:
        method (str): The HTTP method (e.g., "GET", "POST", "PATCH").
        endpoint (str): The API path relative to the base URL (e.g., "/api/v1/health/").
        return_type (str): The expected return format. Options: "json" (default), "content", "response".
        log_context (dict | None): Optional dictionary of context variables to bind to structlog.
        **kwargs: Additional arguments passed directly to httpx.request (e.g., json, content, headers, timeout).

    Returns:
        Any: Parsed JSON dict, raw bytes (content), httpx.Response, or None if the request fails.
    """
    url = generate_url(endpoint)

    structlog.contextvars.clear_contextvars()
    base_context = {"method": method, "url": url}
    if log_context:
        base_context.update(log_context)
    structlog.contextvars.bind_contextvars(**base_context)

    client = get_client()

    try:
        response = await client.request(method, url, **kwargs)

        # binary content
        if return_type == "content":
            if response.status_code != 200:
                server_log.error(f"Error downloading: {response.text}")
                return None
            # Use .content for binary, not .json()
            return response.content

        # direct network response object
        elif return_type == "response":
            return response

        return orjson.loads(response.content)  # response.json()

    except orjson.JSONDecodeError as e:
        api_log.error("Failed to decode JSON response", error=str(e))
        return None
    except httpx.RequestError as e:
        api_log.error("Network request failed", error=str(e))
        return None
    except Exception as e:
        api_log.error("An unexpected error occurred", error=str(e))
        return None


async def queue_task(implant_uuid: str, task: dict) -> httpx.Response | None:
    """
    Submit a new task to be executed by a specific implant.

    Note, this converts the task to msgpack, for sending binary data in the tasks. The server is setup to accept both
    json and msgpack, but msgpack is preferred for tasks to allow for more flexible data structures and binary data.

    Args:
        implant_uuid (str): The unique identifier (UUID) of the target implant.
        task (dict): The task definition. Expected to contain 'task_name' (str) and 'args' (dict).

    Returns:
        httpx.Response: The HTTP response object. A successful task queueing (200 OK) returns the task details.
        Example return data structure (response.json()):
        {
            "task_name": "shell",
            "args": {"cli": "whoami"},
            "status": "queued"
        }
    """
    check_type(implant_uuid, str, "implant_uuid")
    # switch task to dataclass
    check_type(task, dict, "task")

    api_log.debug("Queueing a task for implant")
    task_msgpack = msgpack.packb(task)

    return await safe_api_request(
        method="POST",
        endpoint=f"/api/v1/implants/{implant_uuid}/task",
        return_type="response",
        log_context={"implant_uuid": implant_uuid, "task": task},
        content=task_msgpack,
        headers={"Content-Type": "application/msgpack"},
    )


async def update_implant(implant_uuid: str, data: dict) -> httpx.Response | None:
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

    api_log.debug("Updating data for implant")

    return await safe_api_request(
        method="PUT",
        endpoint=f"/api/v1/implants/{implant_uuid}",
        return_type="response",
        log_context={"implant_uuid": implant_uuid},
        json=data,
    )


async def get_health_status() -> dict | None:
    """
    Gets health status of the server

    Returns:
        dict: A dictionary containing the implant's metadata and check-in history.
        Example structure:
        {
        "data": {
            "mysql_status": "running",
            "neo4j_status": "running",
            "redis_status": "running",
            "response_pipeline_status": "running"
        },
        "message": "Success",
        "status": "200"
        }
    """
    # structlog.contextvars.clear_contextvars()
    # structlog.contextvars.bind_contextvars(method="GET", url=url)
    # api_log.debug("Getting data for implant")

    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/health/",
    )


async def get_implant_data(implant_uuid: str) -> dict | None:
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

    api_log.debug("Getting data for implant")

    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/implants/{implant_uuid}",
        log_context={"implant_uuid": implant_uuid},
    )


async def get_all_implant_data() -> dict | None:
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
    api_log.debug("Getting all implant data")

    # get implants
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/implants/",
    )


async def get_all_listener_data() -> dict | None:
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
    api_log.debug("Getting all listener data")

    # get implants
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/listeners/",
    )


async def get_listener_data(listener_uuid: str) -> dict | None:
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

    api_log.debug("Getting data for listener")

    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/listeners/{listener_uuid}",
        log_context={"listener_uuid": listener_uuid},
    )


async def stop_listener(listener_uuid: str) -> dict | None:
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

    api_log.debug("Getting data for listener")

    state = {"active": False}
    return await safe_api_request(
        method="PATCH",
        endpoint=f"/api/v1/listeners/{listener_uuid}",
        log_context={"listener_uuid": listener_uuid},
        json=state,
    )


async def start_listener_from_existing(listener_uuid: str) -> dict | None:
    """
    Starts a listener, only if it already exists, in a stopped state.

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

    api_log.debug("Getting data for listener")

    state = {"active": True}
    return await safe_api_request(
        method="PATCH",
        endpoint=f"/api/v1/listeners/{listener_uuid}",
        log_context={"listener_uuid": listener_uuid},
        json=state,
    )


async def delete_listener(listener_uuid: str) -> dict | None:
    """
    Delete a running listener

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

    api_log.debug("Getting data for listener")

    return await safe_api_request(
        method="DELETE",
        endpoint=f"/api/v1/listeners/{listener_uuid}",
        log_context={"listener_uuid": listener_uuid},
    )


async def restart_listener(listener_uuid: str) -> dict | None:
    """
    Restart a running listener (Stop, then start)

    Args:
        listener_uuid (str): The unique identifier (UUID) of the listener to stop.

    Returns:
        dict: A status message indicating if the listener was successfully stopped.
        Example structure:
        {
            "status": "success",
            "message": "Listener restarted"
        }
    """
    check_type(listener_uuid, str, "listener_uuid")

    # api_log.debug(f"Getting data for listener")

    stop_data = {"active": False}
    await safe_api_request(
        method="PATCH",
        endpoint=f"/api/v1/listeners/{listener_uuid}",
        log_context={"listener_uuid": listener_uuid},
        json=stop_data,
    )

    # then call again to restart
    start_data = {"active": True}
    return await safe_api_request(
        method="PATCH",
        endpoint=f"/api/v1/listeners/{listener_uuid}",
        log_context={"listener_uuid": listener_uuid},
        json=start_data,
    )


async def start_listener(
    listener_host: str,
    listener_port: int,
    listener_type: str,
    listener_name: str,
    listener_notes: str,
    listener_profile_name: str,
    listener_profile_contents: str,
) -> dict | None:
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

    # --- normalize / preprocess ---
    listener_host = listener_host.strip()
    listener_name = listener_name.strip()

    listener_request_data = {
        "listener_host": listener_host,
        "listener_port": listener_port,
        "listener_type": listener_type,
        "listener_name": listener_name,
        "listener_notes": listener_notes,
        "listener_profile_name": listener_profile_name,
        "listener_profile_contents": listener_profile_contents,
    }

    # --- core logic placeholder ---
    api_log.debug("Getting data for listener")

    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/listeners/",
        json=listener_request_data,
    )


async def build_implant(
    implant_name: str,
    listener_uuids: list,
    output_format: str,
    initial_get_profile_listener_uuid: str,
    initial_post_profile_listener_uuid: str,
) -> dict | None:
    # print(initial_get_profile_listener_uuid)
    # print(initial_post_profile_listener_uuid)
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

        initial_get_profile_listener_uuid (str): The listener UUID to use for the initial GET profile.
        initial_post_profile_listener_uuid (str): The listener UUID to use for the initial POST profile

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
    check_type(listener_uuids, list, "listener_uuids")

    check_type(initial_get_profile_listener_uuid, str, "initial_get_profile_listener_uuid")
    check_type(initial_post_profile_listener_uuid, str, "initial_post_profile_listener_uuid")

    build_request_data = {
        # "implant_name": implant_name,
        "listener_uuids": listener_uuids,
        "implant_name": implant_name,
        "output_format": output_format,
        "initial_get_profile_listener_uuid": initial_get_profile_listener_uuid,
        "initial_post_profile_listener_uuid": initial_post_profile_listener_uuid,
    }

    # --- core logic placeholder ---
    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/build/",
        json=build_request_data,
        timeout=60.0,
    )


async def get_build_status(build_uuid: str) -> dict | None:
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
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/build/jobs/{build_uuid}",
    )


async def get_payload_data() -> dict | None:
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
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/build/",
    )


async def get_payload_bytes(payload_hash: str) -> bytes | None:
    """
    Retrieve the actual compiled binary/bytes of a specific payload.

    Args:
        payload_hash (str): The unique hash identifying the payload.

    Returns:
        bytes: The raw binary content of the payload, or None if download fails.
        Example structure:
        b'\x4d\x5a\x90...' (The actual executable bytes)
    """
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/build/{payload_hash}",
        return_type="content",
    )


async def get_payload_source_bytes(payload_hash: str) -> bytes | None:
    """
    Retrieve the source code (typically as a zip) for a specific built payload.

    Args:
        payload_hash (str): The unique hash identifying the payload.

    Returns:
        bytes: The raw bytes of the source code archive, or None if download fails.
        Example structure:
        b'PK\x03\x04...' (The bytes of a ZIP file)
    """
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/build/{payload_hash}/source",
        return_type="content",
    )


async def get_implant_task_history_since_uuid(implant_uuid: str, since_task_uuid: str) -> dict | None:
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

    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/implants/{implant_uuid}/tasks/history",
        params=url_params,
    )


async def get_implant_task_history(implant_uuid: str) -> dict | None:
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
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/implants/{implant_uuid}/tasks/history",
    )


async def get_all_graph_data() -> dict | None:
    """
    Gets allt eh graph data from the API

    Returns:

    """
    api_log.debug("Getting all graph data")

    # get implants
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/graph/",
    )
