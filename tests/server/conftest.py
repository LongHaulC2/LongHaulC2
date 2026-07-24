import base64
import os
import sys
from pathlib import Path
from typing import Dict, Any

import pytest
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))

from tests.integration_test.conftest import C2APIClient


class FullC2APIClient(C2APIClient):
    """
    Extends C2APIClient with the methods missing from the integration-test version:
    authentication, listener patch, filestore, health check, and graph endpoints.
    """

    def post_authentication(self, username: str, password: str) -> Dict[str, Any]:
        url = str(self.base_url / "authentication")
        response = self.session.post(url, json={"username": username, "password": password})
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_authentication_register(self, username: str, password: str) -> Dict[str, Any]:
        url = str(self.base_url / "authentication" / "register")
        response = self.session.post(url, json={"username": username, "password": password})
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_authentication_refresh(self, refresh_token: str) -> Dict[str, Any]:
        url = str(self.base_url / "authentication" / "refresh")
        # Pass the refresh token directly — overrides the access token in the session header
        response = self.session.post(url, headers={"Authorization": f"Bearer {refresh_token}"})
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def patch_listener(self, uuid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = str(self.base_url / "listeners" / uuid)
        response = self.session.patch(url, json=payload)
        if not response.ok:
            self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    def get_health(self) -> Dict[str, Any]:
        url = str(self.base_url / "health")
        response = self.session.get(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_filestore(self, file_name: str, b64_content: str) -> Dict[str, Any]:
        url = str(self.base_url / "filestore")
        payload = {"file_name": file_name, "file_contents": b64_content}
        response = self.session.post(url, json=payload)
        if not response.ok:
            self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    def get_filestore(self) -> Dict[str, Any]:
        url = str(self.base_url / "filestore")
        response = self.session.get(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_file(self, file_uuid: str) -> bytes:
        url = str(self.base_url / "filestore" / file_uuid)
        response = self.session.get(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.content

    def delete_file(self, file_uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "filestore" / file_uuid)
        response = self.session.delete(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_graph(self) -> Dict[str, Any]:
        url = str(self.base_url / "graph")
        response = self.session.get(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_graph_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = str(self.base_url / "graph" / "search")
        response = self.session.post(url, json=payload)
        if not response.ok:
            self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    # -- Profile CRUD helpers --

    def get_profiles(self) -> Dict[str, Any]:
        url = str(self.base_url / "profiles")
        response = self.session.get(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_profile(self, name: str, contents: str) -> Dict[str, Any]:
        url = str(self.base_url / "profiles")
        payload = {"profile_name": name, "profile_contents": contents}
        response = self.session.post(url, json=payload)
        if not response.ok:
            self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    def get_profile(self, name: str) -> Dict[str, Any]:
        url = str(self.base_url / "profiles" / name)
        response = self.session.get(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def delete_profile(self, name: str) -> Dict[str, Any]:
        url = str(self.base_url / "profiles" / name)
        response = self.session.delete(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_profile_seed(self, profiles: list) -> Dict[str, Any]:
        url = str(self.base_url / "profiles" / "seed")
        payload = {"profiles": profiles}
        response = self.session.post(url, json=payload)
        if not response.ok:
            self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    # -- Audit helpers --

    def get_audit(self, **params) -> Dict[str, Any]:
        url = str(self.base_url / "audit")
        response = self.session.get(url, params=params)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_audit_export(self, **params) -> requests.Response:
        url = str(self.base_url / "audit" / "export")
        response = self.session.get(url, params=params)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response

    # -- Chat helpers --

    def get_chat(self, since_id: int = 0) -> Dict[str, Any]:
        url = str(self.base_url / "chat")
        response = self.session.get(url, params={"since_id": since_id})
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_chat(self, message: str) -> Dict[str, Any]:
        url = str(self.base_url / "chat")
        response = self.session.post(url, json={"message": message})
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    # -- User management helpers --

    def get_users(self) -> Dict[str, Any]:
        url = str(self.base_url / "users")
        response = self.session.get(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_user_me(self) -> Dict[str, Any]:
        url = str(self.base_url / "users" / "me")
        response = self.session.get(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def put_user_password(self, old_password: str, new_password: str) -> Dict[str, Any]:
        url = str(self.base_url / "users" / "password")
        response = self.session.put(url, json={"old_password": old_password, "new_password": new_password})
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def delete_user(self, username: str) -> Dict[str, Any]:
        url = str(self.base_url / "users" / username)
        response = self.session.delete(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_totp_setup(self) -> Dict[str, Any]:
        url = str(self.base_url / "users" / "totp")
        response = self.session.post(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def delete_totp(self) -> Dict[str, Any]:
        url = str(self.base_url / "users" / "totp")
        response = self.session.delete(url)
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_totp_verify(self, code: str) -> Dict[str, Any]:
        url = str(self.base_url / "users" / "totp" / "verify")
        response = self.session.post(url, json={"code": code})
        if not response.ok:
            self._log_error(response)
        response.raise_for_status()
        return response.json()


_RAW_PROFILE_TOML = """
[profile]
name = "pytest raw"

[raw.get]
proto = "tcp"
body = "<METADATA>"

[raw.get.client.metadata]
transforms = [{ op = "base64" }]

[raw.get.server.output]
transforms = []

[raw.post]
proto = "tcp"
body = "<OUTPUT>"

[raw.post.client.output]
transforms = [{ op = "base64" }]

[raw.post.server]
body = ""
"""

LISTENER_PAYLOAD = {
    "listener_host": "127.0.0.1",
    "listener_port": 19099,
    "listener_type": "raw",
    "listener_name": "pytest_listener",
    "listener_notes": "Created by pytest — safe to delete",
    "listener_profile_name": "pytest_raw.toml",
    "listener_profile_contents": _RAW_PROFILE_TOML,
}


@pytest.fixture(scope="session")
def api_client():
    """
    Session-scoped authenticated API client.
    Reads SERVER_URL, TEST_API_USER, TEST_API_PASS from environment;
    falls back to the Makefile dev defaults.
    """
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    username = os.getenv("TEST_API_USER", "longhaul")
    password = os.getenv("TEST_API_PASS", "P@ssw0rd1!")

    client = FullC2APIClient(base_url)
    print(f"\n[SETUP] Authenticating to {base_url} as '{username}'...")
    auth_resp = client.post_authentication(username, password)
    access_token = auth_resp["data"]["access_token"]
    client.session.headers.update({"Authorization": f"Bearer {access_token}"})
    print("[SETUP] Authenticated. Starting tests.")

    yield client

    client.session.close()


@pytest.fixture
def listener_uuid(api_client):
    """Creates a raw listener on 127.0.0.1:19099, yields its UUID, then deletes it."""
    resp = api_client.post_listeners(LISTENER_PAYLOAD)
    uuid = resp["data"]["listener_uuid"]
    yield uuid
    try:
        api_client.delete_listener(uuid)
    except Exception:
        pass


@pytest.fixture
def raw_listener_uuid(api_client):
    """Creates a raw TCP listener on 127.0.0.1:19100, yields its UUID, then deletes it."""
    payload = {
        "listener_host": "127.0.0.1",
        "listener_port": 19100,
        "listener_type": "raw",
        "listener_name": "pytest_raw_listener",
        "listener_notes": "Created by pytest — safe to delete",
        "listener_profile_name": "pytest_raw.toml",
        "listener_profile_contents": _RAW_PROFILE_TOML,
    }
    resp = api_client.post_listeners(payload)
    uuid = resp["data"]["listener_uuid"]
    yield uuid
    try:
        api_client.delete_listener(uuid)
    except Exception:
        pass


@pytest.fixture
def implant_uuid(api_client):
    """Creates a blank implant entry, yields its UUID, then deletes it."""
    resp = api_client.post_implants()
    uuid = resp["data"]["uuid"]
    yield uuid
    try:
        api_client.delete_implant(uuid)
    except Exception:
        pass


@pytest.fixture
def file_uuid(api_client):
    """Uploads a small test file, yields its UUID, then deletes it."""
    b64 = base64.b64encode(b"hello pytest").decode()
    resp = api_client.post_filestore("pytest_test.txt", b64)
    uuid = resp["data"]["file_uuid"]
    yield uuid
    try:
        api_client.delete_file(uuid)
    except Exception:
        pass
