import os

import pyotp
import requests as raw_requests


def test_list_users(api_client):
    """GET /users/ returns 200 with a list of users."""
    resp = api_client.get_users()
    assert resp["status"] == "200"
    assert isinstance(resp["data"], list)
    assert len(resp["data"]) >= 1
    usernames = [u["username"] for u in resp["data"]]
    assert "longhaul" in usernames


def test_get_me(api_client):
    """GET /users/me returns 200 with the current user's profile."""
    resp = api_client.get_user_me()
    assert resp["status"] == "200"
    assert resp["data"]["username"] == "longhaul"
    assert "has_totp" in resp["data"]


def test_change_password_wrong_old(api_client):
    """PUT /users/password with wrong old_password returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = api_client.session.put(
        f"{base_url}/api/v1/users/password",
        json={"old_password": "definitely_wrong", "new_password": "NewPass123!"},
    )
    assert resp.status_code == 401


def test_change_password_missing_fields(api_client):
    """PUT /users/password with missing fields returns 400."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = api_client.session.put(
        f"{base_url}/api/v1/users/password",
        json={"old_password": "something"},
    )
    assert resp.status_code == 400


def test_totp_setup_and_verify(api_client):
    """POST /users/totp generates a secret, and verify accepts a valid code."""
    setup_resp = api_client.post_totp_setup()
    assert setup_resp["status"] == "200"
    secret = setup_resp["data"]["secret"]
    assert secret
    assert "provisioning_uri" in setup_resp["data"]

    totp = pyotp.TOTP(secret)
    code = totp.now()
    verify_resp = api_client.post_totp_verify(code)
    assert verify_resp["status"] == "200"

    # Clean up: disable TOTP so it doesn't break other tests' login
    disable_resp = api_client.delete_totp()
    assert disable_resp["status"] == "200"


def test_totp_verify_bad_code(api_client):
    """POST /users/totp/verify with a bad code returns 401."""
    api_client.post_totp_setup()

    try:
        base_url = os.getenv("SERVER_URL", "http://localhost:45045")
        resp = api_client.session.post(
            f"{base_url}/api/v1/users/totp/verify",
            json={"code": "000000"},
        )
        assert resp.status_code == 401
    finally:
        api_client.delete_totp()


def test_delete_nonexistent_user(api_client):
    """DELETE /users/<username> for a nonexistent user returns 404."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = api_client.session.delete(f"{base_url}/api/v1/users/no_such_user_xyz")
    assert resp.status_code == 404


def test_delete_created_user(api_client):
    """Register a throwaway user, then delete them via the admin endpoint."""
    api_client.post_authentication_register("pytest_throwaway", "Thr0w@way!")
    resp = api_client.delete_user("pytest_throwaway")
    assert resp["status"] == "200"


def test_users_unauthed():
    """GET /users/ without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/users/")
    assert resp.status_code == 401
