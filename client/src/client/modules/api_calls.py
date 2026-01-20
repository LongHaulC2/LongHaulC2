import logging

import httpx
import structlog

from client.src.client.utils.url import generate_url

from ..utils.checks import check_type

server_log = logging.getLogger("server")

api_log = logging.getLogger("api")


async def queue_task(implant_uuid: str, task: dict):
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
    Start a listener with the given configuration.

    Returns:
        dict: status/result payload
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


async def build_implant(
    implant_name, implant_listener_uuid, implant_variant, output_format
) -> dict:
    """
    Start a listener with the given configuration.

    Returns:
        dict: status/result payload
    """

    # --- validate inputs ---
    check_type(implant_name, str, "implant_name")
    check_type(implant_listener_uuid, str, "implant_listener_uuid")
    check_type(implant_variant, str, "implant_variant")
    check_type(output_format, str, "output_format")

    build_request_data = {
        # "implant_name": implant_name,
        "implant_variant": implant_variant,
        "implant_listener_uuid": implant_listener_uuid,
        "implant_name": implant_name,
        "output_format": output_format,
    }

    url = generate_url(f"/api/v1/build/")

    # --- core logic placeholder ---
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="POST", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=build_request_data)
        data = response.json()
        return data


async def get_payload_data() -> dict:
    """Gets list of payloads
    Returns:
        dict: _description_

    """
    url = generate_url(f"/api/v1/build/")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data


async def get_payload_bytes(payload_hash: str) -> dict:
    """Gets the bytes of a payload
    Returns:
        dict: _description_

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


async def get_implant_task_history_since_uuid(
    implant_uuid: str, since_task_uuid: str
) -> dict:
    """Gets list of tasks sinec a specific UUID. This is enabled by UUID7

    Returns:
        dict: _description_

    Ex: /api/v1/implants/019baff9-37fd-759d-8203-a8a5bd505028/tasks/history?since=019baffa-c8c7-76ff-a40d-d2ec6c99306e

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
    """Gets list of all tasks for an implant
    Returns:
        dict: _description_

    Ex: /api/v1/implants/019baff9-37fd-759d-8203-a8a5bd505028/tasks/history

    """
    url = generate_url(f"/api/v1/implants/{implant_uuid}/tasks/history")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(method="GET", url=url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data
