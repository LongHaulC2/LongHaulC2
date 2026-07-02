"""
Integration tests for implant command responses.

Requires a live implant beaconing against a running server.
Validates response structure and content for every command,
not just error_code == 0.

Usage:
    PYTHONPATH=. python -m pytest -v -s tests/integration_test/test_implant_responses.py
"""

import base64
import os
import sys
import time
from pathlib import Path

import msgpack
import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from client.modules.task_definitions import (
    BofRunner,
    Cd,
    FileDownload,
    FileUpload,
    Ls,
    MemStoreClear,
    MemStoreDelete,
    MemStoreDownload,
    MemStoreList,
    MemStoreUpload,
    Sleep,
    StratActive,
    StratList,
)
from tests.integration_test.conftest import C2APIClient


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLL_INTERVAL = 5
MAX_POLLS = 12

MEMSTORE_TEST_NAME = "pytest_roundtrip"
MEMSTORE_TEST_DATA = b"LongHaul_integration_roundtrip_42"

FILE_UPLOAD_PATH = r"C:\Windows\Temp\pytest_response_test.txt"
FILE_UPLOAD_DATA = b"LongHaul file upload integration test"

# x64 ARP table BOF — no args required, always produces output on Windows
X64_ARP_BOF_BYTES = (
    b"\x64\x86\x07\x00\x00\x00\x00\x00\x34\x0c\x00\x00\x29\x00\x00\x00"
    b"\x00\x00\x04\x00\x2e\x74\x65\x78\x74\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x50\x05\x00\x00\x2c\x01\x00\x00\xec\x08\x00\x00"
    b"\x00\x00\x00\x00\x36\x00\x00\x00\x20\x00\x50\x60\x2e\x64\x61\x74"
    b"\x61\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20\x00\x00\x00"
    b"\x7c\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x40\x00\x50\xc0\x2e\x62\x73\x73\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x50\xc0\x2e\x78\x64\x61"
    b"\x74\x61\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x78\x00\x00\x00"
    b"\x9c\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x40\x00\x30\x40\x2e\x70\x64\x61\x74\x61\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x78\x00\x00\x00\x14\x07\x00\x00\x08\x0b\x00\x00"
    b"\x00\x00\x00\x00\x1e\x00\x00\x00\x40\x00\x30\x40\x2e\x72\x64\x61"
    b"\x74\x61\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20\x01\x00\x00"
    b"\x8c\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x40\x00\x50\x40\x2f\x34\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x40\x00\x00\x00\xac\x08\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x50\x40\x48\x83\xec\x28"
    b"\xba\x01\x00\x00\x00\xb9\x00\x20\x00\x00\xff\x15\x00\x00\x00\x00"
    b"\x66\xc7\x05\x06\x00\x00\x00\x00\x00\x48\x89\x05\x10\x00\x00\x00"
    b"\xb8\x01\x00\x00\x00\x48\x83\xc4\x28\xc3\x57\x53\x48\x83\xec\x28"
    b"\x48\x8b\x15\x10\x00\x00\x00\x44\x0f\xb7\x05\x08\x00\x00\x00\x89"
    b"\xcb\x31\xc9\xff\x15\x00\x00\x00\x00\x48\x8b\x15\x10\x00\x00\x00"
    b"\xb9\x00\x08\x00\x00\x31\xc0\x66\xc7\x05\x06\x00\x00\x00\x00\x00"
    b"\x48\x89\xd7\xf3\xab\x85\xdb\x74\x12\x48\x89\xd1\xff\x15\x00\x00"
    b"\x00\x00\x31\xc0\x48\x89\x05\x10\x00\x00\x00\x48\x83\xc4\x28\x5b"
    b"\x5f\xc3\x41\x57\x41\x56\x41\x55\x41\x54\x55\x57\x56\x53\x48\x83"
    b"\xec\x48\x48\x8b\x3d\x00\x00\x00\x00\x4c\x8d\xbc\x24\x98\x00\x00"
    b"\x00\x48\x89\x94\x24\x98\x00\x00\x00\x48\x89\xce\x31\xd2\x4c\x89"
    b"\x84\x24\xa0\x00\x00\x00\x49\x89\xc8\x31\xc9\x4c\x89\x8c\x24\xa8"
    b"\x00\x00\x00\x4d\x89\xf9\x4c\x89\x7c\x24\x38\xff\xd7\x89\xc3\x83"
    b"\xf8\xff\x0f\x84\x07\x01\x00\x00\x4c\x8b\x35\x00\x00\x00\x00\x4c"
    b"\x63\xe3\x41\xff\xd6\x48\x8b\x2d\x00\x00\x00\x00\x41\xb8\x00\x20"
    b"\x00\x00\xba\x08\x00\x00\x00\x48\x89\xc1\xff\xd5\x49\x89\xc5\x41"
    b"\xff\xd6\x4d\x89\xe0\xba\x08\x00\x00\x00\x48\x89\xc1\xff\xd5\x49"
    b"\x89\xf0\x4c\x89\xe2\x4c\x89\x7c\x24\x38\x48\x89\xc5\x4d\x89\xf9"
    b"\x48\x89\xc1\xff\xd7\x0f\xb7\x15\x08\x00\x00\x00\x48\x89\xee\x48"
    b"\x89\xd0\x01\xda\x81\xfa\xff\x1f\x00\x00\x7e\x0a\x41\xbf\x00\x20"
    b"\x00\x00\x31\xc0\xeb\x73\x48\x03\x05\x10\x00\x00\x00\x4c\x89\xe1"
    b"\x48\x89\xc7\xf3\xa4\x66\x01\x1d\x08\x00\x00\x00\xeb\x5f\x0f\xb7"
    b"\x0d\x08\x00\x00\x00\x45\x89\xf8\x41\x29\xc8\x48\x89\xca\x41\x39"
    b"\xd8\x44\x0f\x4f\xc3\x48\x03\x15\x10\x00\x00\x00\x49\x63\xf8\x49"
    b"\x89\xfc\x48\x89\x7c\x24\x28\x48\x89\xd7\x49\x63\xcc\xf3\xa4\x66"
    b"\x8b\x15\x08\x00\x00\x00\x44\x01\xe2\x66\x89\x15\x08\x00\x00\x00"
    b"\x66\x81\xfa\x00\x20\x75\x07\xe8\x7e\xfe\xff\xff\x31\xc0\x4c\x89"
    b"\xef\x49\x63\xcc\x44\x29\xe3\xf3\xaa\x85\xdb\x7f\xa1\x41\xff\xd6"
    b"\x49\x89\xe8\x31\xd2\x48\x8b\x1d\x00\x00\x00\x00\x48\x89\xc1\xff"
    b"\xd3\x41\xff\xd6\x4d\x89\xe8\x31\xd2\x48\x89\xc1\xff\xd3\x90\x48"
    b"\x83\xc4\x48\x5b\x5e\x5f\x5d\x41\x5c\x41\x5d\x41\x5e\x41\x5f\xc3"
    b"\x41\x54\x55\x57\x56\x53\x48\x83\xec\x40\x31\xc0\x31\xd2\x41\x83"
    b"\xc9\xff\x4c\x8b\x25\x00\x00\x00\x00\x48\x89\xce\x31\xc9\x89\x54"
    b"\x24\x28\x31\xd2\x49\x89\xf0\x48\x89\x4c\x24\x20\xb9\xe9\xfd\x00"
    b"\x00\x48\x89\x44\x24\x38\x48\x89\x44\x24\x30\x41\xff\xd4\x48\x8b"
    b"\x2d\x00\x00\x00\x00\x89\xc7\xff\xd5\x4c\x63\xc7\xba\x08\x00\x00"
    b"\x00\x48\x89\xc1\xff\x15\x00\x00\x00\x00\x45\x31\xc0\x41\x83\xc9"
    b"\xff\x31\xd2\x4c\x89\x44\x24\x38\x48\x89\xc3\xb9\xe9\xfd\x00\x00"
    b"\x4c\x89\x44\x24\x30\x49\x89\xf0\x89\x7c\x24\x28\x48\x89\x44\x24"
    b"\x20\x41\xff\xd4\x85\xc0\x75\x17\x48\x85\xdb\x74\x10\xff\xd5\x49"
    b"\x89\xd8\x31\xd2\x48\x89\xc1\xff\x15\x00\x00\x00\x00\x31\xdb\x48"
    b"\x89\xd8\x48\x83\xc4\x40\x5b\x5e\x5f\x5d\x41\x5c\xc3\xc3\x53\x48"
    b"\x83\xec\x50\x31\xc0\x31\xd2\x48\x89\x44\x24\x3c\x48\x8d\x5c\x24"
    b"\x3c\x44\x0f\xb6\xc1\x48\x89\x44\x24\x44\x0f\xb6\xc5\x41\x89\xc1"
    b"\x89\xc8\x89\x54\x24\x4c\x48\x8d\x15\x00\x00\x00\x00\xc1\xe8\x18"
    b"\x89\x44\x24\x28\x89\xc8\x48\x89\xd9\xc1\xe8\x10\x0f\xb6\xc0\x89"
    b"\x44\x24\x20\xff\x15\x00\x00\x00\x00\x48\x89\xda\x48\x8d\x0d\x0c"
    b"\x00\x00\x00\xe8\x8a\xfd\xff\xff\x90\x48\x83\xc4\x50\x5b\xc3\x56"
    b"\x53\x48\x83\xec\x68\x31\xc0\x48\x8d\x1d\x0c\x00\x00\x00\x83\xf9"
    b"\x06\x48\x89\x44\x24\x48\x48\x89\x44\x24\x50\x48\x89\x44\x24\x58"
    b"\x74\x09\x48\x8d\x15\x12\x00\x00\x00\xeb\x41\x0f\xb6\x42\x05\x48"
    b"\x8d\x74\x24\x48\x48\x89\xf1\x89\x44\x24\x38\x0f\xb6\x42\x04\x89"
    b"\x44\x24\x30\x0f\xb6\x42\x03\x89\x44\x24\x28\x0f\xb6\x42\x02\x89"
    b"\x44\x24\x20\x44\x0f\xb6\x4a\x01\x44\x0f\xb6\x02\x48\x8d\x15\x25"
    b"\x00\x00\x00\xff\x15\x00\x00\x00\x00\x48\x89\xf2\x48\x89\xd9\xe8"
    b"\x0e\xfd\xff\xff\x90\x48\x83\xc4\x68\x5b\x5e\xc3\x48\x8d\x05\x43"
    b"\x00\x00\x00\x83\xf9\x01\x74\x2b\x48\x8d\x05\x49\x00\x00\x00\x83"
    b"\xf9\x02\x74\x1f\x48\x8d\x05\x58\x00\x00\x00\x83\xf9\x03\x74\x13"
    b"\x48\x8d\x05\x60\x00\x00\x00\x83\xf9\x04\x75\x07\x48\x8d\x05\x51"
    b"\x00\x00\x00\xc3\x41\x57\x41\x56\x41\x55\x41\x54\x55\x57\x56\x53"
    b"\x48\x83\xec\x48\x31\xc0\x31\xc9\x41\xb8\x01\x00\x00\x00\x48\x8b"
    b"\x35\x00\x00\x00\x00\x48\x8d\x7c\x24\x3c\x89\x44\x24\x3c\x48\x89"
    b"\xfa\xff\xd6\x44\x8b\x44\x24\x3c\x4c\x8b\x25\x00\x00\x00\x00\x4c"
    b"\x89\x44\x24\x28\x41\xff\xd4\x4c\x8b\x44\x24\x28\xba\x08\x00\x00"
    b"\x00\x48\x89\xc1\xff\x15\x00\x00\x00\x00\x48\x89\xc3\x48\x85\xc0"
    b"\x75\x17\x48\x8d\x15\x68\x00\x00\x00\xb9\x0d\x00\x00\x00\xff\x15"
    b"\x00\x00\x00\x00\xe9\xee\x00\x00\x00\x41\xb8\x01\x00\x00\x00\x48"
    b"\x89\xfa\x48\x89\xc1\xff\xd6\x41\x89\xc0\x85\xc0\x74\x2f\x3d\xe8"
    b"\x00\x00\x00\x74\x28\x48\x8b\x35\x00\x00\x00\x00\x48\x8d\x15\x92"
    b"\x00\x00\x00\xb9\x0d\x00\x00\x00\xff\xd6\x48\x8d\x15\xa1\x00\x00"
    b"\x00\xb9\x0d\x00\x00\x00\xff\xd6\xe9\x98\x00\x00\x00\x48\x8d\x73"
    b"\x0c\x31\xc0\x4c\x8d\x2d\xc0\x00\x00\x00\x31\xff\x4c\x8d\x35\xeb"
    b"\x00\x00\x00\x4c\x8d\x3d\xfc\x00\x00\x00\x3b\x3b\x73\x77\x8b\x6e"
    b"\xf8\x39\xc5\x74\x23\x89\xea\x4c\x89\xe9\xe8\xe3\xfb\xff\xff\x4c"
    b"\x8d\x0d\xd5\x00\x00\x00\x4c\x89\xf2\x4c\x89\xf9\x4c\x8d\x05\xda"
    b"\x00\x00\x00\xe8\xca\xfb\xff\xff\x8b\x4e\x08\xe8\xde\xfd\xff\xff"
    b"\x8b\x4e\xfc\x85\xc9\x74\x0a\x48\x89\xf2\xe8\x30\xfe\xff\xff\xeb"
    b"\x13\x48\x8d\x15\x0d\x01\x00\x00\x48\x8d\x0d\x0c\x00\x00\x00\xe8"
    b"\x9e\xfb\xff\xff\x8b\x4e\x0c\xff\xc7\x48\x83\xc6\x18\xe8\x8a\xfe"
    b"\xff\xff\x48\x8d\x0d\x0e\x01\x00\x00\x48\x89\xc2\xe8\x81\xfb\xff"
    b"\xff\x89\xe8\xeb\x85\x41\xff\xd4\x49\x89\xd8\x31\xd2\x48\x89\xc1"
    b"\xff\x15\x00\x00\x00\x00\x90\x48\x83\xc4\x48\x5b\x5e\x5f\x5d\x41"
    b"\x5c\x41\x5d\x41\x5e\x41\x5f\xc3\x48\x83\xec\x28\xe8\xcb\xfa\xff"
    b"\xff\xe8\x7e\xfe\xff\xff\xb9\x01\x00\x00\x00\x48\x83\xc4\x28\xe9"
    b"\xe6\xfa\xff\xff\x90\x90\x90\x90\x90\x90\x90\x90"
)  # fmt: skip


# ---------------------------------------------------------------------------
# Auth client — avoids touching the integration conftest
# ---------------------------------------------------------------------------


class _AuthClient(C2APIClient):
    def login(self, username: str, password: str):
        url = str(self.base_url / "authentication")
        resp = self.session.post(url, json={"username": username, "password": password})
        resp.raise_for_status()
        token = resp.json()["data"]["access_token"]
        self.session.headers["Authorization"] = f"Bearer {token}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api():
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    username = os.getenv("TEST_API_USER", "longhaul")
    password = os.getenv("TEST_API_PASS", "P@ssw0rd1!")

    client = _AuthClient(base_url)
    client.login(username, password)
    yield client
    client.session.close()


@pytest.fixture(scope="module")
def implant_uuid(api):
    resp = api.get_implants()
    implants = resp.get("data", [])
    assert implants, "No active implants available — is one beaconing?"
    uuid = implants[0]["implant_uuid"]
    print(f"\n[SETUP] Using implant: {uuid}")
    return uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_base_response(resp: dict):
    """Every implant response must have these three fields."""
    assert "windows_error_code" in resp, f"Missing windows_error_code in: {resp}"
    assert "message" in resp, f"Missing message in: {resp}"
    assert "data" in resp, f"Missing data in: {resp}"


def dispatch_and_wait(
    api: _AuthClient,
    implant_uuid: str,
    task_obj,
    *,
    expect_success: bool = True,
    send_as_msgpack: bool = False,
) -> dict:
    """
    Send a task, poll until the implant responds, return the task_response dict.

    If expect_success is True (default), asserts windows_error_code == 0.
    If False, just returns the response for the caller to inspect.
    """
    payload = task_obj.to_task()
    if send_as_msgpack:
        payload = msgpack.packb(payload)

    resp = api.post_implant_task(implant_uuid, payload)
    task_uuid = resp["data"]["task_uuid"]

    for _ in range(MAX_POLLS):
        task = api.get_implant_task(implant_uuid=implant_uuid, task_uuid=task_uuid)
        task_response = task.get("data", {}).get("task_response")

        if task_response is not None and "windows_error_code" in task_response:
            _assert_base_response(task_response)

            if expect_success:
                code = task_response["windows_error_code"]
                assert code == 0, (
                    f"Expected success (0), got error code {code}: "
                    f"{task_response.get('message', 'no message')}"
                )

            return task_response

        time.sleep(POLL_INTERVAL)

    pytest.fail(f"Task {task_uuid} timed out after {MAX_POLLS * POLL_INTERVAL}s")


# ===========================================================================
# 1. Strategy
# ===========================================================================


class TestStrategy:
    def test_strat_list_returns_strategies(self, api, implant_uuid):
        """strat list should return a non-empty list of strategy names."""
        resp = dispatch_and_wait(api, implant_uuid, StratList(implant_uuid=implant_uuid))

        data = resp["data"]
        assert data, "strat list returned empty data — implant has no strategies?"

    def test_strat_active_returns_both_channels(self, api, implant_uuid):
        """strat active should return both comms_get_strategy and comms_post_strategy."""
        resp = dispatch_and_wait(api, implant_uuid, StratActive(implant_uuid=implant_uuid))

        assert "comms_get_strategy" in resp, "Missing comms_get_strategy field"
        assert "comms_post_strategy" in resp, "Missing comms_post_strategy field"
        assert resp["comms_get_strategy"], "comms_get_strategy is empty"
        assert resp["comms_post_strategy"], "comms_post_strategy is empty"


# ===========================================================================
# 2. Memory Store — full lifecycle
# ===========================================================================


class TestMemStore:
    """Tests run in order: clear → upload → list → download → delete → verify gone."""

    def test_01_clear(self, api, implant_uuid):
        """Clear the memstore to start from a known state."""
        dispatch_and_wait(api, implant_uuid, MemStoreClear(implant_uuid=implant_uuid))

    def test_02_list_empty(self, api, implant_uuid):
        """After clear, memstore list should return empty data."""
        resp = dispatch_and_wait(api, implant_uuid, MemStoreList(implant_uuid=implant_uuid))
        data = resp["data"]
        assert data == "" or data == [] or data is None or (isinstance(data, str) and data.strip() == ""), (
            f"Expected empty memstore after clear, got: {repr(data)}"
        )

    def test_03_upload(self, api, implant_uuid):
        """Upload test data to the memstore."""
        b64 = base64.b64encode(MEMSTORE_TEST_DATA).decode()
        cmd = MemStoreUpload(
            implant_uuid=implant_uuid,
            file_name=MEMSTORE_TEST_NAME,
            file_contents=b64,
        )
        dispatch_and_wait(api, implant_uuid, cmd, send_as_msgpack=True)

    def test_04_list_contains_uploaded(self, api, implant_uuid):
        """After upload, memstore list should contain our file name."""
        resp = dispatch_and_wait(api, implant_uuid, MemStoreList(implant_uuid=implant_uuid))
        data = resp["data"]
        assert MEMSTORE_TEST_NAME in str(data), (
            f"Expected '{MEMSTORE_TEST_NAME}' in memstore listing, got: {repr(data)}"
        )

    def test_05_download_matches_upload(self, api, implant_uuid):
        """Download should return the exact bytes we uploaded."""
        cmd = MemStoreDownload(implant_uuid=implant_uuid, file_name=MEMSTORE_TEST_NAME)
        resp = dispatch_and_wait(api, implant_uuid, cmd)

        data = resp["data"]
        assert data, "memstore download returned empty data"

        if isinstance(data, str):
            downloaded = base64.b64decode(data)
        elif isinstance(data, dict) and "bin" in str(type(data)):
            downloaded = bytes(data)
        elif isinstance(data, (bytes, bytearray)):
            downloaded = bytes(data)
        elif isinstance(data, list):
            downloaded = bytes(data)
        else:
            downloaded = data

        assert downloaded == MEMSTORE_TEST_DATA, (
            f"Round-trip mismatch.\n"
            f"  Uploaded: {MEMSTORE_TEST_DATA!r}\n"
            f"  Got back: {downloaded!r}"
        )

    def test_06_delete(self, api, implant_uuid):
        """Delete the test file from memstore."""
        cmd = MemStoreDelete(implant_uuid=implant_uuid, file_name=MEMSTORE_TEST_NAME)
        dispatch_and_wait(api, implant_uuid, cmd)

    def test_07_list_after_delete(self, api, implant_uuid):
        """After delete, the file should no longer appear in the listing."""
        resp = dispatch_and_wait(api, implant_uuid, MemStoreList(implant_uuid=implant_uuid))
        data = str(resp["data"])
        assert MEMSTORE_TEST_NAME not in data, (
            f"'{MEMSTORE_TEST_NAME}' still present after delete: {data}"
        )


# ===========================================================================
# 3. File System
# ===========================================================================


class TestFileSystem:
    def test_ls_cwd(self, api, implant_uuid):
        """ls with no path should list the current working directory."""
        resp = dispatch_and_wait(api, implant_uuid, Ls(implant_uuid=implant_uuid, directory=""))
        assert resp["data"], "ls returned empty data for CWD"

    def test_ls_root(self, api, implant_uuid):
        """ls C:\\ should list root directory entries."""
        resp = dispatch_and_wait(api, implant_uuid, Ls(implant_uuid=implant_uuid, directory="C:\\"))
        data = str(resp["data"])
        assert "Windows" in data or "Users" in data or "Program" in data, (
            f"Expected common Windows dirs in C:\\ listing, got: {data[:200]}"
        )

    def test_cd_to_windows(self, api, implant_uuid):
        """cd to C:\\Windows should succeed."""
        dispatch_and_wait(
            api, implant_uuid, Cd(implant_uuid=implant_uuid, directory="C:\\Windows")
        )

    def test_ls_after_cd(self, api, implant_uuid):
        """ls after cd to C:\\Windows should show System32."""
        resp = dispatch_and_wait(api, implant_uuid, Ls(implant_uuid=implant_uuid, directory=""))
        assert "System32" in str(resp["data"]) or "system32" in str(resp["data"]).lower(), (
            f"Expected System32 in Windows dir listing"
        )

    def test_cd_revert(self, api, implant_uuid):
        """Revert CWD back to C:\\ for other tests."""
        dispatch_and_wait(api, implant_uuid, Cd(implant_uuid=implant_uuid, directory="C:\\"))

    def test_file_upload(self, api, implant_uuid):
        """Upload a file to disk via base64."""
        b64 = base64.b64encode(FILE_UPLOAD_DATA).decode()
        cmd = FileUpload(
            implant_uuid=implant_uuid,
            file_path=FILE_UPLOAD_PATH,
            file_contents=b64,
        )
        dispatch_and_wait(api, implant_uuid, cmd, send_as_msgpack=True)

    def test_file_download_matches_upload(self, api, implant_uuid):
        """Download the file we just uploaded and verify contents match."""
        cmd = FileDownload(implant_uuid=implant_uuid, file_path=FILE_UPLOAD_PATH)
        resp = dispatch_and_wait(api, implant_uuid, cmd)

        data = resp["data"]
        assert data, "file download returned empty data"

        if isinstance(data, str):
            downloaded = base64.b64decode(data)
        elif isinstance(data, (bytes, bytearray)):
            downloaded = bytes(data)
        elif isinstance(data, list):
            downloaded = bytes(data)
        else:
            downloaded = data

        assert downloaded == FILE_UPLOAD_DATA, (
            f"File round-trip mismatch.\n"
            f"  Uploaded: {FILE_UPLOAD_DATA!r}\n"
            f"  Got back: {downloaded!r}"
        )

    def test_file_upload_from_memstore(self, api, implant_uuid):
        """Stage data in memstore, then write to disk via deref operator."""
        stage_data = b"memstore_to_disk_roundtrip"
        stage_name = "pytest_staged"
        stage_path = r"C:\Windows\Temp\pytest_deref_test.txt"

        b64 = base64.b64encode(stage_data).decode()
        upload_cmd = MemStoreUpload(
            implant_uuid=implant_uuid, file_name=stage_name, file_contents=b64
        )
        dispatch_and_wait(api, implant_uuid, upload_cmd, send_as_msgpack=True)

        write_cmd = FileUpload(
            implant_uuid=implant_uuid,
            file_path=stage_path,
            file_contents=f"*{stage_name}",
        )
        dispatch_and_wait(api, implant_uuid, write_cmd)

        dl_cmd = FileDownload(implant_uuid=implant_uuid, file_path=stage_path)
        resp = dispatch_and_wait(api, implant_uuid, dl_cmd)

        data = resp["data"]
        if isinstance(data, str):
            downloaded = base64.b64decode(data)
        elif isinstance(data, (bytes, bytearray, list)):
            downloaded = bytes(data)
        else:
            downloaded = data

        assert downloaded == stage_data, (
            f"Memstore→disk round-trip mismatch.\n"
            f"  Staged:  {stage_data!r}\n"
            f"  Got back: {downloaded!r}"
        )

        MemStoreDelete(implant_uuid=implant_uuid, file_name=stage_name)


# ===========================================================================
# 4. BOF Execution
# ===========================================================================


class TestBofExecution:
    def test_bof_b64_no_args(self, api, implant_uuid):
        """Run the ARP BOF (no args) from base64 — should produce output."""
        b64 = base64.b64encode(X64_ARP_BOF_BYTES).decode()
        cmd = BofRunner(implant_uuid=implant_uuid, bof_contents=b64, bof_args="")
        resp = dispatch_and_wait(api, implant_uuid, cmd, send_as_msgpack=True)

        assert resp["data"], "BOF produced no output — expected ARP table data"

    def test_bof_from_memstore(self, api, implant_uuid):
        """Upload BOF to memstore, then run via deref operator."""
        bof_name = "pytest_arp_bof"
        b64 = base64.b64encode(X64_ARP_BOF_BYTES).decode()

        upload_cmd = MemStoreUpload(
            implant_uuid=implant_uuid, file_name=bof_name, file_contents=b64
        )
        dispatch_and_wait(api, implant_uuid, upload_cmd, send_as_msgpack=True)

        run_cmd = BofRunner(
            implant_uuid=implant_uuid, bof_contents=f"*{bof_name}", bof_args=""
        )
        resp = dispatch_and_wait(api, implant_uuid, run_cmd)
        assert resp["data"], "Memstore BOF produced no output"

        cleanup = MemStoreDelete(implant_uuid=implant_uuid, file_name=bof_name)
        dispatch_and_wait(api, implant_uuid, cleanup)


# ===========================================================================
# 5. System Commands
# ===========================================================================


class TestSystem:
    def test_sleep(self, api, implant_uuid):
        """Set sleep to 3 seconds — response should echo the new interval."""
        cmd = Sleep(implant_uuid=implant_uuid, sleep_time="3")
        resp = dispatch_and_wait(api, implant_uuid, cmd)

        data = resp["data"]
        assert str(data) == "3" or data == 3, (
            f"Expected sleep data to be '3', got: {repr(data)}"
        )

    def test_sleep_restore(self, api, implant_uuid):
        """Restore sleep to 1 second so subsequent tests aren't slow."""
        cmd = Sleep(implant_uuid=implant_uuid, sleep_time="1")
        dispatch_and_wait(api, implant_uuid, cmd)
