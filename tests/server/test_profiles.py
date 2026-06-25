import os
from pathlib import Path

import requests as raw_requests

_PROFILE_PATH = Path(__file__).resolve().parents[2] / "client" / "user" / "profiles" / "profile_def.toml"


def test_profile_preview_valid_toml(api_client):
    """POST a valid profile returns parse_ok=true with http_get populated and transform steps."""
    url = str(api_client.base_url / "profiles" / "preview")
    resp = api_client.session.post(url, json={"profile_contents": _PROFILE_PATH.read_text()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["validation"]["parse_ok"] is True
    assert body["data"]["http_get"] is not None
    assert body["data"]["http_get"]["client"]["metadata_token_location"] == "header:Cookie"
    assert len(body["data"]["http_get"]["client"]["metadata_transforms"]) > 0
    assert body["data"]["http_post"] is not None


def test_profile_preview_malformed_toml(api_client):
    """POST malformed TOML returns HTTP 200 with parse_ok=false and a parse_error string."""
    url = str(api_client.base_url / "profiles" / "preview")
    resp = api_client.session.post(url, json={"profile_contents": "[bad toml"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["validation"]["parse_ok"] is False
    assert body["data"]["validation"]["parse_error"]
    assert body["data"].get("http_get") is None


def test_profile_preview_missing_field(api_client):
    """POST with empty body returns 400 — profile_contents is required."""
    url = str(api_client.base_url / "profiles" / "preview")
    resp = api_client.session.post(url, json={})
    assert resp.status_code == 400


def test_profile_preview_unauthed():
    """POST without auth token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.post(
        f"{base_url}/api/v1/profiles/preview",
        json={"profile_contents": "name = 'test'"},
    )
    assert resp.status_code == 401
