import os

import requests as raw_requests


def test_get_all_builds(api_client):
    """GET /build/ returns 200 with a list."""
    resp = api_client.get_build()
    assert resp["status"] == "200"
    assert isinstance(resp["data"], list)


def test_submit_build(api_client):
    """POST /build/ returns 200 with a build_uuid. Does not wait for completion
    (the build toolchain may not be present on the test machine)."""
    payload = {
        "implant_name": "pytest_test_build",
        "listener_uuids": [],
    }
    resp = api_client.post_build(payload)
    assert resp["status"] == "200"
    build_uuid = resp["data"]["build_uuid"]
    assert build_uuid


def test_get_build_job_status(api_client):
    """GET /build/jobs/{build_uuid} for a just-submitted build returns 200
    with a recognizable status field."""
    payload = {
        "implant_name": "pytest_status_check_build",
        "listener_uuids": [],
    }
    submit_resp = api_client.post_build(payload)
    build_uuid = submit_resp["data"]["build_uuid"]

    resp = api_client.get_build_jobs(build_uuid)
    assert resp["status"] == "200"
    build_status = resp["data"].get("build_status")
    assert build_status in {"pending", "running", "complete", "failed"}


def test_delete_nonexistent_binary(api_client):
    """DELETE /build/<random-hash> always returns 200 (stub endpoint, no existence check)."""
    resp = api_client.delete_binary_actions("00000000000000000000000000000000")
    assert resp["status"] == "200"


def test_build_unauthed():
    """GET /build/ without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/build")
    assert resp.status_code == 401
