from client.src.client.utils.url import generate_url
import httpx
import logging

server_log = logging.getLogger("server")

api_log = logging.getLogger("api")


async def queue_task(implant_uuid: int, task: dict):
    api_log.debug(f"Queueing a task for implant {implant_uuid}: {task}")
    url = generate_url(f"/api/v1/implants/{implant_uuid}/task")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=task)
        return response


async def update_implant(implant_uuid: int, data: dict):
    api_log.debug(f"Updating data for implant {implant_uuid}: {data}")
    url = generate_url(f"/api/v1/implants/{implant_uuid}")

    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data)
        return response


async def get_implant_data(implant_uuid: int) -> dict:
    api_log.debug(f"Getting data for implant {implant_uuid}")
    url = generate_url(f"/api/v1/implants/{implant_uuid}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return data


async def get_all_implant_data() -> dict:
    api_log.debug(f"Getting all implant data")
    url = generate_url("/api/v1/implants/")

    # get implants
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()  # .get("data")
        return data
