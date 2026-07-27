import os

import requests as raw_requests


def test_send_message(api_client):
    """POST /chat/ with a message returns 200."""
    resp = api_client.post_chat("hello from pytest")
    assert resp["status"] == "200"


def test_get_messages(api_client):
    """GET /chat/ returns 200 with a list containing previously sent messages."""
    api_client.post_chat("pytest fetch test")
    resp = api_client.get_chat()
    assert resp["status"] == "200"
    assert isinstance(resp["data"], list)
    assert len(resp["data"]) >= 1
    messages = [m["message"] for m in resp["data"]]
    assert "pytest fetch test" in messages


def test_get_messages_since_id(api_client):
    """GET /chat/?since_id=N only returns messages after that ID."""
    all_before = api_client.get_chat()
    assert len(all_before["data"]) >= 1
    marker_id = all_before["data"][-1]["id"]

    api_client.post_chat("msg after marker")

    resp = api_client.get_chat(since_id=marker_id)
    assert resp["status"] == "200"
    assert len(resp["data"]) >= 1
    for msg in resp["data"]:
        assert msg["id"] > marker_id


def test_send_empty_message(api_client):
    """POST /chat/ with an empty message returns 400."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = api_client.session.post(
        f"{base_url}/api/v1/chat/",
        json={"message": "   "},
    )
    assert resp.status_code == 400


def test_chat_unauthed():
    """GET /chat/ without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/chat/")
    assert resp.status_code == 401
