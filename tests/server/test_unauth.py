import os

import pytest
import requests

BASE_URL = os.getenv("SERVER_URL", "http://localhost:45045") + "/api/v1"

FAKE_UUID = "00000000-0000-0000-0000-000000000000"

ENDPOINTS = [
    # (method, path, json_body_or_None)

    # Health
    ("GET", "/health", None),

    # Implants
    ("GET", "/implants", None),
    ("POST", "/implants", None),
    ("GET", f"/implants/{FAKE_UUID}", None),
    ("DELETE", f"/implants/{FAKE_UUID}", None),
    ("POST", f"/implants/{FAKE_UUID}/task", {
        "implant_uuid": FAKE_UUID,
        "task": {"command": "ls", "args": ""},
    }),
    ("GET", f"/implants/{FAKE_UUID}/tasks", None),
    ("GET", f"/implants/{FAKE_UUID}/task/{FAKE_UUID}", None),
    ("GET", f"/implants/{FAKE_UUID}/tasks/history", None),
    ("POST", "/implants/search", {"search_term": "test"}),
    ("POST", "/implants/history/search", {"search_term": "test"}),

    # Listeners
    ("GET", "/listeners", None),
    ("POST", "/listeners", {
        "listener_host": "127.0.0.1",
        "listener_port": 9999,
        "listener_type": "raw",
        "listener_name": "unauth_test",
        "listener_profile_name": "test.toml",
        "listener_profile_contents": "[profile]\nname = \"test\"",
    }),
    ("GET", f"/listeners/{FAKE_UUID}", None),
    ("DELETE", f"/listeners/{FAKE_UUID}", None),
    ("PATCH", f"/listeners/{FAKE_UUID}", {"active": True}),

    # Filestore
    ("GET", "/filestore", None),
    ("POST", "/filestore", {"file_name": "test.txt", "file_contents": "dGVzdA=="}),
    ("GET", f"/filestore/{FAKE_UUID}", None),
    ("DELETE", f"/filestore/{FAKE_UUID}", None),

    # Build
    ("GET", "/build", None),
    ("POST", "/build", {
        "implant_name": "test",
        "listener_uuids": [FAKE_UUID],
        "initial_get_profile_listener_uuid": FAKE_UUID,
        "initial_post_profile_listener_uuid": FAKE_UUID,
    }),
    ("GET", f"/build/jobs/{FAKE_UUID}", None),
    ("GET", f"/build/jobs/{FAKE_UUID}/package", None),
    ("GET", f"/build/{FAKE_UUID}", None),
    ("DELETE", f"/build/{FAKE_UUID}", None),
    ("GET", f"/build/{FAKE_UUID}/source", None),

    # Profiles
    ("GET", "/profiles", None),
    ("POST", "/profiles", {"profile_name": "test.toml", "profile_contents": "[profile]\nname=\"t\""}),
    ("GET", "/profiles/test_profile", None),
    ("DELETE", "/profiles/test_profile", None),
    ("POST", "/profiles/preview", {"profile_contents": "[profile]\nname=\"t\""}),
    ("POST", "/profiles/seed", {"profiles": []}),

    # Graph
    ("GET", "/graph", None),
    ("POST", "/graph/search", {"search_term": "test"}),
    ("GET", "/graph/node/Implant/", None),
    ("GET", f"/graph/node/Implant/{FAKE_UUID}", None),

    # Users
    ("GET", "/users", None),
    ("GET", "/users/me", None),
    ("DELETE", "/users/me", None),
    ("DELETE", f"/users/{FAKE_UUID}", None),
    ("PUT", "/users/password", {"old_password": "x", "new_password": "y"}),
    ("POST", "/users/totp", None),
    ("DELETE", "/users/totp", None),
    ("POST", "/users/totp/verify", {"code": "000000"}),

    # Chat
    ("GET", "/chat", None),
    ("POST", "/chat", {"message": "test"}),

    # Audit
    ("GET", "/audit", None),
    ("GET", "/audit/export", None),

    # Auth — register requires auth, refresh requires a refresh token
    ("POST", "/authentication/register", {"username": "x", "password": "y"}),
]


def _test_id(endpoint):
    method, path, _ = endpoint
    return f"{method} {path}"


@pytest.mark.parametrize("method,path,body", ENDPOINTS, ids=[_test_id(e) for e in ENDPOINTS])
def test_endpoint_returns_401_without_auth(method, path, body):
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    resp = requests.request(method, f"{BASE_URL}{path}", **kwargs)
    assert resp.status_code == 401, (
        f"{method} {path} returned {resp.status_code}, expected 401"
    )
