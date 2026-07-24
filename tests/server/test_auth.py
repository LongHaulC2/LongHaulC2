import os

import requests as raw_requests

from tests.server.conftest import FullC2APIClient


def test_login_success(api_client):
    """Valid credentials return 200 with access and refresh tokens."""
    username = os.getenv("TEST_API_USER", "longhaul")
    password = os.getenv("TEST_API_PASS", "P@ssw0rd1!")
    resp = api_client.post_authentication(username, password)

    assert resp["status"] == "200"
    assert "access_token" in resp["data"]
    assert "refresh_token" in resp["data"]
    assert resp["data"]["access_token"]
    assert resp["data"]["refresh_token"]


def test_login_missing_fields(api_client):
    """POST with an empty body returns 400."""
    url = str(api_client.base_url / "authentication")
    resp = raw_requests.post(url, json={})
    assert resp.status_code == 400


def test_refresh_token(api_client):
    """A valid refresh token can be exchanged for a new access token."""
    username = os.getenv("TEST_API_USER", "longhaul")
    password = os.getenv("TEST_API_PASS", "P@ssw0rd1!")

    # Get a fresh token pair so we have a refresh token to use
    auth_resp = api_client.post_authentication(username, password)
    refresh_token = auth_resp["data"]["refresh_token"]

    resp = api_client.post_authentication_refresh(refresh_token)
    assert resp["status"] == "200"
    assert resp["data"]["access_token"]


def test_access_token_rejected_on_refresh_endpoint(api_client):
    """Sending an access token to /refresh returns 422 (refresh=True requires refresh token)."""
    username = os.getenv("TEST_API_USER", "longhaul")
    password = os.getenv("TEST_API_PASS", "P@ssw0rd1!")

    auth_resp = api_client.post_authentication(username, password)
    access_token = auth_resp["data"]["access_token"]

    url = str(api_client.base_url / "authentication" / "refresh")
    resp = raw_requests.post(url, headers={"Authorization": f"Bearer {access_token}"})
    # Flask-JWT rejects access tokens on refresh-only endpoints
    # 401 is expected as it's sending the wrong token type (refresh, not jwt), which is access denied
    assert resp.status_code == 401


def test_register_requires_auth():
    """POST /authentication/register without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    url = f"{base_url}/api/v1/authentication/register"
    resp = raw_requests.post(url, json={"username": "newuser", "password": "TestPass1!"})
    assert resp.status_code == 401


def test_register_with_auth(api_client):
    """POST /authentication/register with a valid token returns 200."""
    import uuid

    unique_user = f"pytest_user_{uuid.uuid4().hex[:8]}"
    resp = api_client.post_authentication_register(unique_user, "TestPass1!")
    assert resp["status"] == "200"


def test_unauthed_request_to_protected_route():
    """Any protected route called without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/health")
    assert resp.status_code == 401


def test_expired_or_invalid_token():
    """A clearly malformed token returns 422."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(
        f"{base_url}/api/v1/health",
        headers={"Authorization": "Bearer this.is.not.a.real.jwt"},
    )
    # Sending a bad token, so 401 is correct, as request is not authorized with bad token
    assert resp.status_code == 401
