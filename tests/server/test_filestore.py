import base64
import os

import requests as raw_requests

_TEST_FILE_CONTENT = base64.b64encode(b"hello pytest filestore").decode()


def test_get_all_files(api_client):
    """GET /filestore/ returns 200 with a list."""
    resp = api_client.get_filestore()
    assert resp["status"] == "200"
    assert isinstance(resp["data"], list)


def test_upload_file(api_client):
    """POST /filestore/ with file_name and base64 content returns 200 with file_uuid."""
    resp = api_client.post_filestore("pytest_upload.txt", _TEST_FILE_CONTENT)
    assert resp["status"] == "200"
    file_uuid = resp["data"]["file_uuid"]
    assert file_uuid
    # clean up
    api_client.delete_file(file_uuid)


def test_download_file(api_client, file_uuid):
    """GET /filestore/{uuid} returns binary content."""
    content = api_client.get_file(file_uuid)
    assert isinstance(content, bytes)
    assert len(content) > 0


def test_delete_file(api_client, file_uuid):
    """DELETE /filestore/{uuid} returns 200. Fixture teardown will attempt a second delete — fine."""
    resp = api_client.delete_file(file_uuid)
    assert resp["status"] == "200"


def test_download_nonexistent_file(api_client):
    """GET /filestore/<random-uuid> returns an error response (no server 500)."""
    import uuid as uuid_mod

    fake_uuid = str(uuid_mod.uuid4())
    url = str(api_client.base_url / "filestore" / fake_uuid)
    resp = api_client.session.get(url)
    # Server returns APIResponse with status 404 but HTTP 200 — just ensure no 500
    assert resp.status_code != 500


def test_upload_missing_fields(api_client):
    """POST /filestore/ with an empty body returns 400."""
    url = str(api_client.base_url / "filestore")
    resp = api_client.session.post(url, json={})
    assert resp.status_code == 400


def test_filestore_unauthed():
    """GET /filestore/ without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/filestore")
    assert resp.status_code == 401
