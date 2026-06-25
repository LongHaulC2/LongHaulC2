import os

import requests as raw_requests


def test_get_all_implants(api_client):
    """GET /implants/ returns 200 with a list."""
    resp = api_client.get_implants()
    assert resp["status"] == "200"
    assert isinstance(resp["data"], list)


def test_create_implant(api_client):
    """POST /implants/ returns 200 with a uuid."""
    resp = api_client.post_implants()
    assert resp["status"] == "200"
    uuid = resp["data"]["uuid"]
    assert uuid
    # clean up
    api_client.delete_implant(uuid)


def test_get_single_implant(api_client, implant_uuid):
    """GET /implants/{uuid} returns 200."""
    resp = api_client.get_implant(implant_uuid)
    assert resp["status"] == "200"


def test_update_implant(api_client, implant_uuid):
    """PUT /implants/{uuid} with notes returns 200."""
    resp = api_client.put_implant(implant_uuid, {"notes": "set by pytest"})
    assert resp["status"] == "200"


def test_delete_implant(api_client, implant_uuid):
    """DELETE /implants/{uuid} returns 200. Fixture teardown will attempt a second delete — that's fine."""
    resp = api_client.delete_implant(implant_uuid)
    assert resp["status"] == "200"


def test_queue_task(api_client, implant_uuid):
    """POST a task to /implants/{uuid}/task returns 200 with a task_uuid."""
    task_payload = {
        "implant_uuid": implant_uuid,
        "task": {
            "task_name": "ls",
            "args": {},
        },
    }
    resp = api_client.post_implant_task(implant_uuid, task_payload)
    assert resp["status"] == "200"
    assert resp["data"]["task_uuid"]


def test_peek_task_queue(api_client, implant_uuid):
    """GET /implants/{uuid}/tasks returns 200 with a list after queuing a task."""
    task_payload = {
        "implant_uuid": implant_uuid,
        "task": {"task_name": "ls", "args": {}},
    }
    api_client.post_implant_task(implant_uuid, task_payload)

    resp = api_client.get_implant_tasks(implant_uuid)
    assert resp["status"] == "200"
    assert isinstance(resp["data"], list)
    assert len(resp["data"]) >= 1


def test_delete_task_queue(api_client, implant_uuid):
    """DELETE /implants/{uuid}/tasks clears the queue and returns 200."""
    task_payload = {
        "implant_uuid": implant_uuid,
        "task": {"task_name": "ls", "args": {}},
    }
    api_client.post_implant_task(implant_uuid, task_payload)

    resp = api_client.delete_implant_tasks(implant_uuid)
    assert resp["status"] == "200"

    # Queue should now be empty
    after = api_client.get_implant_tasks(implant_uuid)
    assert after["data"] == []


def test_task_history(api_client, implant_uuid):
    """GET /implants/{uuid}/tasks/history returns 200 with a list (may be empty)."""
    resp = api_client.get_implant_history(implant_uuid)
    assert resp["status"] == "200"
    assert isinstance(resp["data"], list)


def test_search_implants(api_client):
    """POST /implants/search with an empty term returns 200."""
    resp = api_client.post_implant_search({"search_term": ""})
    assert resp["status"] == "200"


def test_search_task_history(api_client):
    """POST /implants/history/search with an empty term returns 200."""
    resp = api_client.post_task_search({"search_term": ""})
    assert resp["status"] == "200"


def test_implants_unauthed():
    """GET /implants/ without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/implants")
    assert resp.status_code == 401
