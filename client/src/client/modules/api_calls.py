from client.src.client.utils.url import generate_url
import httpx
import logging

server_log = logging.getLogger("server")

api_log = logging.getLogger("api")


async def queue_task(implant_id: int, task: dict):
    api_log.debug(f"Queueing a task for implant {implant_id}: {task}")
    url = generate_url(f"/api/v1/implants/{implant_id}/task")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=task)
        return response


async def update_implant(implant_id: int, data: dict):
    api_log.debug(f"Updating data for implant {implant_id}: {data}")
    url = generate_url(f"/api/v1/implants/{implant_id}")

    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data)
        return response


async def get_implant_data(implant_id: int) -> dict:
    api_log.debug(f"Getting data for implant {implant_id}")
    url = generate_url(f"/api/v1/implants/{implant_id}")

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
