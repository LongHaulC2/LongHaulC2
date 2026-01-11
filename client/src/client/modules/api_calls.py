import logging

import httpx
import structlog

from client.src.client.utils.url import generate_url

server_log = logging.getLogger("server")

api_log = logging.getLogger("api")


async def queue_task(implant_uuid: int, task: dict):
    url = generate_url(f"/api/v1/implants/{implant_uuid}/task")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="POST", url=url, implant_uuid=implant_uuid, task=task
    )
    api_log.debug(f"Queueing a task for implant")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=task)
        return response


async def update_implant(implant_uuid: int, data: dict):
    url = generate_url(f"/api/v1/implants/{implant_uuid}")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method="GET", url=url, implant_uuid=implant_uuid
    )
    api_log.debug(f"Updating data for implant")

    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data)
        return response


async def get_implant_data(implant_uuid: int) -> dict:
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
