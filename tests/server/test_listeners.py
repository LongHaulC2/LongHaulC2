import os

import requests as raw_requests


def test_get_all_listeners(api_client):
    """GET /listeners/ returns 200 with a list."""
    resp = api_client.get_listeners()
    assert resp["status"] == "200"
    assert isinstance(resp["data"], list)


def test_create_listener(api_client, listener_uuid):
    """Creating a listener returns 200 with a uuid and active=True."""
    resp = api_client.get_listener(listener_uuid)
    assert resp["status"] == "200"
    data = resp["data"]
    assert data["listener_uuid"] == listener_uuid
    assert data["listener_active"] is True


def test_get_single_listener(api_client, listener_uuid):
    """GET /listeners/{uuid} returns 200 with listener data."""
    resp = api_client.get_listener(listener_uuid)
    assert resp["status"] == "200"
    assert resp["data"]["listener_uuid"] == listener_uuid


def test_get_nonexistent_listener(api_client):
    """GET /listeners/<random-uuid> returns 404."""
    import uuid as uuid_mod

    fake_uuid = str(uuid_mod.uuid4())
    url = str(api_client.base_url / "listeners" / fake_uuid)
    resp = api_client.session.get(url)
    assert resp.status_code == 404


def test_stop_listener(api_client, listener_uuid):
    """PATCH {active: false} on an active listener returns 200."""
    resp = api_client.patch_listener(listener_uuid, {"active": False})
    assert resp["status"] == "200"
    assert "stopped" in resp["message"].lower() or "offline" in resp["message"].lower()


def test_start_listener(api_client, listener_uuid):
    """PATCH {active: true} on a stopped listener returns 200."""
    api_client.patch_listener(listener_uuid, {"active": False})
    resp = api_client.patch_listener(listener_uuid, {"active": True})
    assert resp["status"] == "200"
    assert "started" in resp["message"].lower() or "online" in resp["message"].lower()


def test_already_active_message(api_client, listener_uuid):
    """PATCH {active: true} on an already-active listener returns the 'already online' message."""
    resp = api_client.patch_listener(listener_uuid, {"active": True})
    assert resp["status"] == "200"
    assert "already" in resp["message"].lower()


def test_patch_missing_active_field(api_client, listener_uuid):
    """PATCH with a payload missing the 'active' field returns 400."""
    url = str(api_client.base_url / "listeners" / listener_uuid)
    resp = api_client.session.patch(url, json={})
    assert resp.status_code == 400


def test_delete_listener(api_client, listener_uuid):
    """DELETE /listeners/{uuid} returns 200. Fixture teardown will attempt a second delete — fine."""
    resp = api_client.delete_listener(listener_uuid)
    assert resp["status"] == "200"


def test_listeners_unauthed():
    """GET /listeners/ without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/listeners")
    assert resp.status_code == 401


def test_create_raw_listener(api_client, raw_listener_uuid):
    """Creating a raw listener returns 200 with uuid, active=True, and type='raw'."""
    resp = api_client.get_listener(raw_listener_uuid)
    assert resp["status"] == "200"
    data = resp["data"]
    assert data["listener_uuid"] == raw_listener_uuid
    assert data["listener_type"] == "raw"
    assert data["listener_active"] is True


def test_raw_listener_stop_start(api_client, raw_listener_uuid):
    """Raw listener can be stopped and restarted via PATCH."""
    stop_resp = api_client.patch_listener(raw_listener_uuid, {"active": False})
    assert stop_resp["status"] == "200"

    start_resp = api_client.patch_listener(raw_listener_uuid, {"active": True})
    assert start_resp["status"] == "200"
    assert "started" in start_resp["message"].lower() or "online" in start_resp["message"].lower()
