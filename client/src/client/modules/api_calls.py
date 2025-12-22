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
