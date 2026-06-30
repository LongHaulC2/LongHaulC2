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


# ---------------------------------------------------------------------------
# Profile CRUD tests
# ---------------------------------------------------------------------------

_TEST_PROFILE_NAME = "pytest_test_profile.toml"
_TEST_PROFILE_CONTENTS = """
[profile]
name = "pytest profile"

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


def test_profile_upload(api_client):
    """POST /profiles/ with name and contents returns 200 with artifact metadata."""
    resp = api_client.post_profile(_TEST_PROFILE_NAME, _TEST_PROFILE_CONTENTS)
    assert resp["status"] == "200"
    assert resp["data"]["artifact_name"] == _TEST_PROFILE_NAME
    assert resp["data"]["content_hash"]
    assert resp["data"]["artifact_uuid"]
    # cleanup
    api_client.delete_profile(_TEST_PROFILE_NAME)


def test_profile_list(api_client):
    """GET /profiles/ includes an uploaded profile in the list."""
    api_client.post_profile(_TEST_PROFILE_NAME, _TEST_PROFILE_CONTENTS)
    resp = api_client.get_profiles()
    assert resp["status"] == "200"
    names = [p["artifact_name"] for p in resp["data"]]
    assert _TEST_PROFILE_NAME in names
    # list should not include contents
    for p in resp["data"]:
        assert "artifact_contents" not in p
    api_client.delete_profile(_TEST_PROFILE_NAME)


def test_profile_get_by_name(api_client):
    """GET /profiles/<name> returns full contents."""
    api_client.post_profile(_TEST_PROFILE_NAME, _TEST_PROFILE_CONTENTS)
    resp = api_client.get_profile(_TEST_PROFILE_NAME)
    assert resp["status"] == "200"
    assert resp["data"]["artifact_contents"] == _TEST_PROFILE_CONTENTS
    assert resp["data"]["artifact_name"] == _TEST_PROFILE_NAME
    api_client.delete_profile(_TEST_PROFILE_NAME)


def test_profile_upsert_same_hash(api_client):
    """POST same profile twice with identical content keeps the same hash."""
    resp1 = api_client.post_profile(_TEST_PROFILE_NAME, _TEST_PROFILE_CONTENTS)
    resp2 = api_client.post_profile(_TEST_PROFILE_NAME, _TEST_PROFILE_CONTENTS)
    assert resp1["data"]["content_hash"] == resp2["data"]["content_hash"]
    assert resp1["data"]["artifact_uuid"] == resp2["data"]["artifact_uuid"]
    api_client.delete_profile(_TEST_PROFILE_NAME)


def test_profile_upsert_different_content(api_client):
    """POST same name with different content updates the hash."""
    resp1 = api_client.post_profile(_TEST_PROFILE_NAME, _TEST_PROFILE_CONTENTS)
    modified = _TEST_PROFILE_CONTENTS.replace("pytest profile", "pytest profile v2")
    resp2 = api_client.post_profile(_TEST_PROFILE_NAME, modified)
    assert resp1["data"]["content_hash"] != resp2["data"]["content_hash"]
    # UUID is preserved (same row updated)
    assert resp1["data"]["artifact_uuid"] == resp2["data"]["artifact_uuid"]
    api_client.delete_profile(_TEST_PROFILE_NAME)


def test_profile_delete(api_client):
    """DELETE /profiles/<name> removes the profile."""
    api_client.post_profile(_TEST_PROFILE_NAME, _TEST_PROFILE_CONTENTS)
    resp = api_client.delete_profile(_TEST_PROFILE_NAME)
    assert resp["status"] == "200"
    # verify it's gone from the list
    list_resp = api_client.get_profiles()
    names = [p["artifact_name"] for p in list_resp["data"]]
    assert _TEST_PROFILE_NAME not in names


def test_profile_seed(api_client):
    """POST /profiles/seed bulk-uploads profiles and reports counts."""
    profiles = [
        {"profile_name": "seed_a.toml", "profile_contents": '[profile]\nname = "A"'},
        {"profile_name": "seed_b.toml", "profile_contents": '[profile]\nname = "B"'},
    ]
    resp = api_client.post_profile_seed(profiles)
    assert resp["status"] == "200"
    assert resp["data"]["created"] == 2
    assert resp["data"]["unchanged"] == 0

    # seed again — should be unchanged
    resp2 = api_client.post_profile_seed(profiles)
    assert resp2["data"]["created"] == 0
    assert resp2["data"]["unchanged"] == 2

    # cleanup
    api_client.delete_profile("seed_a.toml")
    api_client.delete_profile("seed_b.toml")


def test_profile_unauthed():
    """GET /profiles/ without auth returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/profiles/")
    assert resp.status_code == 401
