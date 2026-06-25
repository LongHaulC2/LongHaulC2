import os

import requests as raw_requests


def test_health_check_success(api_client):
    """GET /health/ with a valid token returns 200 and a data payload."""
    resp = api_client.get_health()
    assert resp["status"] == "200"
    assert resp["data"] is not None


def test_health_check_unauthed():
    """GET /health/ without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/health")
    assert resp.status_code == 401
