import base64
import time
from typing import Any, Literal

import httpx
import msgpack
import orjson  # trying for speed
import structlog
from nicegui import app

from client.modules.latency_tracker import update_latency_metrics
from client.utils.url import generate_url

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
        # verify false for allowing of self signed certs
        _client = httpx.AsyncClient(verify=False)
    return _client


async def safe_api_request(
    method: str,
    endpoint: str,
    return_type: str = "json",
    log_context: dict[str, Any] | None = None,
    skip_auth: bool = False,
    _is_retry: bool = False,  # Prevents infinite refresh loops
    **kwargs: Any,
) -> Any:
    """
    Global helper to handle all API requests, standardize logging,
    inject auth headers, and auto-refresh expired tokens.
    """
    url = generate_url(endpoint)

    structlog.contextvars.clear_contextvars()
    base_context = {"method": method, "url": url}
    if log_context:
        base_context.update(log_context)
    structlog.contextvars.bind_contextvars(**base_context)

    client = get_client()

    # Safely get and copy headers so we don't lose custom ones (like Content-Type) on retries
    headers = kwargs.get("headers", {}).copy()

    if not skip_auth:
        access_token = app.storage.user.get("access_token")
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        else:
            api_log.warning("No access token found in session")
            # ui.navigate.to('/login')
            return None

    kwargs["headers"] = headers

    start_time = time.perf_counter()
    try:
        response = await client.request(method, url, **kwargs)

        end_time = time.perf_counter()
        update_latency_metrics((end_time - start_time) * 1000)

        # --- AUTO REFRESH TRIGGER ---
        if response.status_code == 401 and not skip_auth and not _is_retry:
            api_log.warning("Access token expired. Attempting silent refresh...")
            refresh_token = app.storage.user.get("refresh_token")

            if refresh_token:
                # Ask the server for a new access token
                refresh_response = await client.post(
                    generate_url("/api/v1/authentication/refresh"), headers={"Authorization": f"Bearer {refresh_token}"}
                )

                if refresh_response.status_code == 200:
                    api_log.info("Token refreshed successfully. Retrying request.")
                    new_data = orjson.loads(refresh_response.content)
                    new_access_token = new_data.get("data", {}).get("access_token")

                    # Update the browser cookie with the new access token
                    app.storage.user["access_token"] = new_access_token

                    # Retry the original request exactly once
                    return await safe_api_request(
                        method=method,
                        endpoint=endpoint,
                        return_type=return_type,
                        log_context=log_context,
                        skip_auth=skip_auth,
                        _is_retry=True,
                        **kwargs,
                    )

            # If we get here, either the refresh token is missing or it also expired
            api_log.error("Refresh failed or token expired. Kicking to login.")
            app.storage.user["access_token"] = None
            app.storage.user["refresh_token"] = None
            # ui.navigate.to("/login")
            return None

        # --- NORMAL RESPONSE HANDLING ---

        # binary content
        if return_type == "content":
            if response.status_code != 200:
                server_log.error(f"Error downloading: {response.text}")
                return None
            return response.content

        # direct network response object
        if return_type == "response":
            return response

        # default json parsing
        return orjson.loads(response.content)

    except orjson.JSONDecodeError as e:
        api_log.error("Failed to decode JSON response", error=str(e))
        return None
    except httpx.RequestError as e:
        api_log.error("Network request failed", error=str(e))
        return None
    except Exception as e:
        api_log.error("An unexpected error occurred", error=str(e))
        return None


async def authenticate_to_server(username: str, password: str, totp_code: str | None = None) -> dict | None:
    request_data = {
        "username": username,
        "password": password,
    }
    if totp_code:
        request_data["totp_code"] = totp_code

    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/authentication/",
        json=request_data,
        skip_auth=True,
    )


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

    api_log.info("task", task=task)
    api_log.info("implant_uuid", task=implant_uuid)

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


async def delete_implant(implant_uuid=str) -> None:
    check_type(implant_uuid, str, "implant_uuid")

    return await safe_api_request(
        method="DELETE",
        endpoint=f"/api/v1/implants/{implant_uuid}",
        return_type="response",
        log_context={"implant_uuid": implant_uuid},
    )


async def search_server(query: str, search_for: Literal["implant", "task", "graph"] | None) -> httpx.Response | None:
    """
    Search the server

    Args:
        query: The string to search for

    Returns:
        httpx.Response: The HTTP response object.
        Example return data structure (200 OK):
        {
            "status": "success",
            "message": "Implant updated"
        }
    """
    check_type(query, str, "query")

    # api set up to have 2 search endpoints, relevant to each item.
    if search_for == "implant":
        url = "/api/v1/implants/search"

    elif search_for == "task":
        url = "/api/v1/implants/history/search"

    elif search_for == "graph":
        url = "/api/v1/graph/search"

    else:
        api_log.warning("Invalid search type for search_server")
        return None

    request_body = {"search_term": str(query)}

    return await safe_api_request(
        method="POST",
        endpoint=url,
        return_type="response",
        json=request_body,
    )


async def create_implant_entry(implant_uuid: str) -> dict | None:
    """
    Creates a blank implant entry, and registers it to the datamodel

    Args:
        implant_uuid (str): The unique identifier (UUID) of the implant to update.
        data (dict): The update data, such as notes or status changes.

    Returns:
        dict, with uuid in it
    """
    check_type(implant_uuid, str, "implant_uuid")

    api_log.debug("Creating new implant entry")

    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/implants/",
        log_context={"implant_uuid": implant_uuid},
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
            "listener_type": "raw",
            "listener_profile_name": "raw_http_profile.toml",
            "listener_profile_contents": "[raw.get]\nproto = \"tcp\"\nbody = \"<METADATA>\"\n..."
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
        listener_type (str): Type of listener ('raw', 'pivot_smb').
        listener_name (str): Friendly name for the listener.
        listener_notes (str): Additional notes.
        listener_profile_name (str): Network profile filename.
        listener_profile_contents (str): The raw TOML content of the network profile.

    Returns:
        dict: The created listener's details, including its new UUID.
    """
    # validate inputs
    check_type(listener_host, str, "listener_host")
    check_type(listener_port, int, "listener_port")
    check_type(listener_type, str, "listener_type")
    check_type(listener_name, str, "listener_name")
    check_type(listener_notes, str, "listener_notes")
    check_type(listener_profile_name, str, "listener_profile_name")
    check_type(listener_profile_contents, str, "listener_profile_contents")

    # normalize / preprocess
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

    # core logic placeholder
    api_log.debug("Getting data for listener")

    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/listeners/",
        json=listener_request_data,
    )


async def build_implant(
    implant_name: str,
    listener_uuids: list,
    initial_get_profile_listener_uuid: str,
    initial_post_profile_listener_uuid: str,
    callback_host: str,
    options: dict,
) -> dict | None:
    """
    Submit a task to build a new implant payload tailored to a specific listener.

    Args:
        implant_name (str): The name to give the built implant.
        listener_uuids (list): List of listener UUIDs to compile into the implant.
        initial_get_profile_listener_uuid (str): The listener UUID to use for the initial GET profile.
        initial_post_profile_listener_uuid (str): The listener UUID to use for the initial POST profile.
        callback_host (str): IP or hostname for the implant to call back to.
        options (dict): Build options (debug, clear_cache, etc.).

    Returns:
        dict: Details of the build job, including a 'build_uuid' to track status.
    """
    check_type(implant_name, str, "implant_name")
    check_type(listener_uuids, list, "listener_uuids")
    check_type(initial_get_profile_listener_uuid, str, "initial_get_profile_listener_uuid")
    check_type(initial_post_profile_listener_uuid, str, "initial_post_profile_listener_uuid")

    build_request_data = {
        "listener_uuids": listener_uuids,
        "implant_name": implant_name,
        "initial_get_profile_listener_uuid": initial_get_profile_listener_uuid,
        "initial_post_profile_listener_uuid": initial_post_profile_listener_uuid,
        "callback_host": callback_host,
        "options": options,
    }

    # core logic placeholder
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


async def get_build_package(build_uuid: str) -> bytes | None:
    """Download all binary artifacts for a build as a zip package."""
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/build/jobs/{build_uuid}/package",
        return_type="content",
    )


async def get_all_files():
    """Gets all files stored in DB"""
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/filestore/",
    )


async def get_file_bytes(file_uuid: str) -> bytes | None:
    """
    Retrieve the bytes of a stored file

    Args:
        file_uuid (str): The UUID of the file to download

    Returns:
        bytes: The raw binary content of the payload, or None if download fails.
        Example structure:
        b'\x4d\x5a\x90...' (The actual executable bytes)
    """
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/filestore/{file_uuid}",
        return_type="content",
    )


async def post_new_file_to_server_filestore(file_name, file_bytes: bytes):
    """
    Posts a new file to the filestore

    """

    # b64 is ascii, so we decode to that
    file_contents = base64.b64encode(file_bytes).decode("ascii")

    request_data = {"file_name": file_name, "file_contents": file_contents}

    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/filestore/",
        json=request_data,
    )


async def delete_file_from_server_filestore(file_uuid: str):
    """
    Deletes a file from the server filestore

    """

    return await safe_api_request(
        method="DELETE",
        endpoint=f"/api/v1/filestore/{file_uuid}",
    )


# uplaod file


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


async def get_single_node_data(node_type: str, node_uuid: str) -> dict | None:
    """Get data about ONE node

    Args:
        node_type (str): The node type
        node_uuid (str): The UUID of the node

    Returns:
        dict | None: Dict of data
    """
    api_log.debug("Getting a node", node_type=node_type, node_uuid=node_uuid)

    # get implants
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/graph/node/{node_type}/{node_uuid}",
    )


async def get_all_node_data(node_type: str) -> dict | None:
    """Gets data from ALL of a node type

    Args:
        node_type (str): The node type

    Returns:
        dict | None: Dict of data
    """
    api_log.debug("Getting nodes", node_type=node_type)

    # get implants
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/graph/node/{node_type}/",
    )


async def update_node_data(node_type: str, node_uuid: str, node_data: dict):
    """Update the data of one node

    Args:
        node_type (str): The node type
        node_uuid (str): The UUID of the node
        node_data (dict): Dict data to update the node with

    """
    api_log.debug("Deleting a node", node_type=node_type, node_uuid=node_uuid, node_data=node_data)

    return await safe_api_request(
        method="PATCH",
        endpoint=f"/api/v1/graph/node/{node_type}/{node_uuid}",
        json=node_data,
    )


async def delete_single_node(node_type: str, node_uuid: str) -> dict | None:
    """Delete data from ONE node

    Args:
        node_type (str): The node type
        node_uuid (str): The UUID of the node

    Returns:
        dict | None: Dict of data
    """
    api_log.debug("Deleting a node", node_type=node_type, node_uuid=node_uuid)

    # get implants
    return await safe_api_request(
        method="DELETE",
        endpoint=f"/api/v1/graph/node/{node_type}/{node_uuid}",
    )


async def preview_profile(profile_contents: str) -> dict | None:
    """Submit raw TOML profile contents to the server for preview rendering.

    Returns a structured breakdown of request/response templates, header lists,
    and step-by-step transform chain output for each protocol section.

    Args:
        profile_contents (str): Raw TOML string of the network profile.

    Returns:
        dict | None: Structured preview data including transform chains and validation info.
    """
    check_type(profile_contents, str, "profile_contents")
    api_log.debug("Requesting profile preview")
    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/profiles/preview",
        json={"profile_contents": profile_contents},
    )


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------


async def get_all_profiles() -> dict | None:
    """Fetch list of all profiles from the server (metadata only, no contents)."""
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/profiles/",
    )


async def get_profile_by_name(profile_name: str) -> dict | None:
    """Fetch full profile contents by name."""
    check_type(profile_name, str, "profile_name")
    return await safe_api_request(
        method="GET",
        endpoint=f"/api/v1/profiles/{profile_name}",
    )


async def upload_profile(profile_name: str, profile_contents: str) -> dict | None:
    """Upload or update a profile on the server."""
    check_type(profile_name, str, "profile_name")
    check_type(profile_contents, str, "profile_contents")
    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/profiles/",
        json={"profile_name": profile_name, "profile_contents": profile_contents},
    )


async def delete_profile(profile_name: str) -> dict | None:
    """Delete a profile from the server."""
    check_type(profile_name, str, "profile_name")
    return await safe_api_request(
        method="DELETE",
        endpoint=f"/api/v1/profiles/{profile_name}",
    )


async def seed_profiles(profiles: list[dict]) -> dict | None:
    """Bulk-upload seed profiles to the server."""
    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/profiles/seed",
        json={"profiles": profiles},
    )


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------


async def get_all_users() -> dict | None:
    return await safe_api_request(method="GET", endpoint="/api/v1/users/")


async def get_current_user() -> dict | None:
    return await safe_api_request(method="GET", endpoint="/api/v1/users/me")


async def delete_user(username: str) -> dict | None:
    check_type(username, str, "username")
    return await safe_api_request(method="DELETE", endpoint=f"/api/v1/users/{username}")


async def delete_own_account() -> dict | None:
    return await safe_api_request(method="DELETE", endpoint="/api/v1/users/me")


async def change_password(old_password: str, new_password: str) -> dict | None:
    return await safe_api_request(
        method="PUT",
        endpoint="/api/v1/users/password",
        json={"old_password": old_password, "new_password": new_password},
    )


async def register_user(username: str, password: str) -> dict | None:
    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/authentication/register",
        json={"username": username, "password": password},
    )


async def setup_totp() -> dict | None:
    return await safe_api_request(method="POST", endpoint="/api/v1/users/totp")


async def verify_totp(code: str) -> dict | None:
    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/users/totp/verify",
        json={"code": code},
    )


async def disable_totp() -> dict | None:
    return await safe_api_request(method="DELETE", endpoint="/api/v1/users/totp")


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


async def get_chat_messages(since_id: int = 0) -> dict | None:
    params = {}
    if since_id > 0:
        params["since_id"] = since_id
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/chat/",
        params=params,
    )


async def send_chat_message(message: str) -> dict | None:
    check_type(message, str, "message")
    return await safe_api_request(
        method="POST",
        endpoint="/api/v1/chat/",
        json={"message": message},
    )


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


async def get_audit_log(
    actor: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    since: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict | None:
    params: dict = {}
    if actor:
        params["actor"] = actor
    if action:
        params["action"] = action
    if target_type:
        params["target_type"] = target_type
    if since:
        params["since"] = since
    if limit != 50:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/audit/",
        params=params,
    )


async def get_audit_export(
    actor: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    since: int | None = None,
) -> bytes | None:
    params: dict = {}
    if actor:
        params["actor"] = actor
    if action:
        params["action"] = action
    if target_type:
        params["target_type"] = target_type
    if since:
        params["since"] = since
    return await safe_api_request(
        method="GET",
        endpoint="/api/v1/audit/export",
        params=params,
        return_type="content",
    )
