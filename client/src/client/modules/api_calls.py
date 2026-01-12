import logging

import httpx
import structlog

from client.src.client.utils.url import generate_url

from ..utils.checks import check_type

server_log = logging.getLogger("server")

api_log = logging.getLogger("api")


async def queue_task(implant_uuid: str, task: dict):
    check_type(implant_uuid, str, "implant_uuid")
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

    url = generate_url(f"/api/v1/implants/{listener_uuid}")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="GET", url=url, listener_uuid=listener_uuid
    )
    api_log.debug(f"Getting data for listener")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return data


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
