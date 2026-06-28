import os
from pathlib import Path

import requests as raw_requests

_PROFILE_PATH = Path(__file__).resolve().parents[2] / "client" / "user" / "profiles" / "raw_http_profile.toml"


def test_profile_preview_valid_toml(api_client):
    """POST a valid raw profile returns parse_ok=true with raw_profiles populated and transform steps."""
    url = str(api_client.base_url / "profiles" / "preview")
    resp = api_client.session.post(url, json={"profile_contents": _PROFILE_PATH.read_text()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["validation"]["parse_ok"] is True
    raw_profiles = body["data"]["raw_profiles"]
    assert len(raw_profiles) == 1
    assert raw_profiles[0]["name"] == "default"
    assert raw_profiles[0]["get"]["proto"] == "tcp"
    assert raw_profiles[0]["get"]["client"]["metadata_token_location"] == "body"
    assert len(raw_profiles[0]["get"]["client"]["metadata_transforms"]) > 0
    assert raw_profiles[0]["post"] is not None


def test_profile_preview_malformed_toml(api_client):
    """POST malformed TOML returns HTTP 200 with parse_ok=false and a parse_error string."""
    url = str(api_client.base_url / "profiles" / "preview")
    resp = api_client.session.post(url, json={"profile_contents": "[bad toml"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["validation"]["parse_ok"] is False
    assert body["data"]["validation"]["parse_error"]


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


_RAW_PROFILE_SIMPLE = """
[profile]
name = "Raw Test"

[raw.get]
proto = "tcp"
body = "<METADATA>"

[raw.get.client.metadata]
transforms = [
    { op = "base64" },
]

[raw.get.server.output]
transforms = []

[raw.post]
proto = "tcp"
body = "<OUTPUT>"

[raw.post.client.output]
transforms = [
    { op = "base64" },
]

[raw.post.server]
body = ""
"""



def test_profile_preview_raw_simple(api_client):
    """A profile with top-level [raw.get]/[raw.post] returns one 'default' raw entry."""
    url = str(api_client.base_url / "profiles" / "preview")
    resp = api_client.session.post(url, json={"profile_contents": _RAW_PROFILE_SIMPLE})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["validation"]["parse_ok"] is True
    raw_profiles = body["data"]["raw_profiles"]
    assert len(raw_profiles) == 1
    assert raw_profiles[0]["name"] == "default"
    assert raw_profiles[0]["get"]["proto"] == "tcp"
    assert raw_profiles[0]["get"]["client"]["metadata_token_location"] == "body"
    assert len(raw_profiles[0]["get"]["client"]["metadata_transforms"]) > 0
    assert raw_profiles[0]["post"] is not None


def test_profile_preview_no_raw_section_has_empty_raw_profiles(api_client):
    """A TOML with no [raw] section returns parse_ok=true with an empty raw_profiles list."""
    minimal_toml = '[profile]\nname = "minimal"\n'
    url = str(api_client.base_url / "profiles" / "preview")
    resp = api_client.session.post(url, json={"profile_contents": minimal_toml})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["validation"]["parse_ok"] is True
    assert body["data"]["raw_profiles"] == []
