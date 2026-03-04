import time
import base64
import pytest

# pull in all our tasks from the task defs, easier to maintain, and cleaner in the long run
from client.src.client.modules.task_definitions import *

def verify_task_success(task_response_data: dict):
    result = task_response_data.get("result", {})
    error_code = result.get("windows_error_code")
    assert error_code == 0, f"Task failed. Expected windows_error_code 0, got {error_code}"

def dispatch_and_wait(api_client, implant_uuid: str, task_object, timeout: int = 60) -> dict:
    task_payload = task_object.to_task()
    
    response = api_client.post_implant_task(implant_uuid, task_payload)
    task_uuid = response.get("data", {}).get("task_uuid")
    assert task_uuid, "Failed to retrieve task_uuid from server response"

    start_time = time.time()
    while time.time() - start_time < timeout:
        history_response = api_client.get_implant_history(implant_uuid)
        tasks = history_response.get("data", [])
        
        for task in tasks:
            if task.get("task_uuid") == task_uuid:
                status = task.get("status")
                if status == "complete" or status == "completed":
                    verify_task_success(task)
                    return task
                elif status == "failed":
                    pytest.fail(f"Task {task_uuid} reported a failed status on the server.")
                    
        time.sleep(2)
        
    pytest.fail(f"Task {task_uuid} timed out after {timeout} seconds")

@pytest.fixture(scope="module")
def target_implant(api_client):
    response = api_client.get_implants()
    implants = response.get("data", [])
    assert implants, "No active implants available for testing"
    return implants[0].get("implant_uuid")


# ==========================================
# Strategy Tests
# ==========================================

def test_01_strat_list(api_client, target_implant):
    cmd = StratList(implant_uuid=target_implant)
    dispatch_and_wait(api_client, target_implant, cmd)

def test_02_strat_active(api_client, target_implant):
    cmd = StratActive(implant_uuid=target_implant)
    dispatch_and_wait(api_client, target_implant, cmd)

def test_03_strat_post(api_client, target_implant):
    cmd = StratPost(implant_uuid=target_implant, strategy_name="default_post")
    dispatch_and_wait(api_client, target_implant, cmd)

def test_04_strat_get(api_client, target_implant):
    cmd = StratGet(implant_uuid=target_implant, strategy_name="default_get")
    dispatch_and_wait(api_client, target_implant, cmd)

# ==========================================
# Memory Store Tests
# ==========================================

def test_05_memstore_clear(api_client, target_implant):
    cmd = MemStoreClear(implant_uuid=target_implant)
    dispatch_and_wait(api_client, target_implant, cmd)

def test_06_memstore_upload(api_client, target_implant):
    b64_data = base64.b64encode(b"pytest_memstore_data").decode("utf-8")
    cmd = MemStoreUpload(implant_uuid=target_implant, file_name="test_mem_file", file_contents=b64_data)
    dispatch_and_wait(api_client, target_implant, cmd)

def test_07_memstore_list(api_client, target_implant):
    cmd = MemStoreList(implant_uuid=target_implant)
    dispatch_and_wait(api_client, target_implant, cmd)

def test_08_memstore_download(api_client, target_implant):
    cmd = MemStoreDownload(implant_uuid=target_implant, file_name="test_mem_file")
    dispatch_and_wait(api_client, target_implant, cmd)

def test_09_memstore_delete(api_client, target_implant):
    cmd = MemStoreDelete(implant_uuid=target_implant, file_name="test_mem_file")
    dispatch_and_wait(api_client, target_implant, cmd)

# ==========================================
# File System Tests
# ==========================================

def test_10_ls_default(api_client, target_implant):
    cmd = Ls(implant_uuid=target_implant, directory="")
    dispatch_and_wait(api_client, target_implant, cmd)

def test_11_ls_path(api_client, target_implant):
    cmd = Ls(implant_uuid=target_implant, directory="C:\\")
    dispatch_and_wait(api_client, target_implant, cmd)

def test_12_cd_default(api_client, target_implant):
    cmd = Cd(implant_uuid=target_implant, directory=".")
    dispatch_and_wait(api_client, target_implant, cmd)

def test_13_cd_path(api_client, target_implant):
    cmd = Cd(implant_uuid=target_implant, directory="C:\\Windows")
    dispatch_and_wait(api_client, target_implant, cmd)
    
    # Revert back
    revert = Cd(implant_uuid=target_implant, directory="C:\\")
    dispatch_and_wait(api_client, target_implant, revert)

def test_14_file_upload_b64(api_client, target_implant):
    b64_data = base64.b64encode(b"pytest_upload_data").decode("utf-8")
    cmd = FileUpload(implant_uuid=target_implant, file_path="C:\\Windows\\Temp\\pytest_up.txt", file_contents=b64_data)
    dispatch_and_wait(api_client, target_implant, cmd)

def test_15_file_upload_memstore(api_client, target_implant):
    b64_data = base64.b64encode(b"memstore_stage_data").decode("utf-8")
    setup_cmd = MemStoreUpload(implant_uuid=target_implant, file_name="staged_file", file_contents=b64_data)
    dispatch_and_wait(api_client, target_implant, setup_cmd)
    
    cmd = FileUpload(implant_uuid=target_implant, file_path="C:\\Windows\\Temp\\pytest_mem_up.txt", file_contents="*staged_file")
    dispatch_and_wait(api_client, target_implant, cmd)

def test_16_file_download(api_client, target_implant):
    cmd = FileDownload(implant_uuid=target_implant, file_path="C:\\Windows\\Temp\\pytest_up.txt")
    dispatch_and_wait(api_client, target_implant, cmd)

# ==========================================
# Execution Tests
# ==========================================

def test_17_bof_b64_no_args(api_client, target_implant):
    b64_bof = base64.b64encode(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00").decode("utf-8")
    cmd = BofRunner(implant_uuid=target_implant, bof_contents=b64_bof, bof_args="")
    dispatch_and_wait(api_client, target_implant, cmd)

def test_18_bof_b64_with_args(api_client, target_implant):
    b64_bof = base64.b64encode(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00").decode("utf-8")
    cmd = BofRunner(implant_uuid=target_implant, bof_contents=b64_bof, bof_args="--test-arg true")
    dispatch_and_wait(api_client, target_implant, cmd)

def test_19_bof_memstore(api_client, target_implant):
    b64_bof = base64.b64encode(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00").decode("utf-8")
    setup_cmd = MemStoreUpload(implant_uuid=target_implant, file_name="test_bof", file_contents=b64_bof)
    dispatch_and_wait(api_client, target_implant, setup_cmd)
    
    cmd = BofRunner(implant_uuid=target_implant, bof_contents="*test_bof", bof_args="")
    dispatch_and_wait(api_client, target_implant, cmd)

# ==========================================
# Discovery Tests
# ==========================================

def test_20_discover_neighbors_no_resolve(api_client, target_implant):
    cmd = DiscoverNeighbors(implant_uuid=target_implant, resolve=False)
    dispatch_and_wait(api_client, target_implant, cmd)

def test_21_discover_neighbors_with_resolve(api_client, target_implant):
    cmd = DiscoverNeighbors(implant_uuid=target_implant, resolve=True)
    dispatch_and_wait(api_client, target_implant, cmd, timeout=120)

# ==========================================
# System Tests (Exit must be last)
# ==========================================

def test_22_sleep(api_client, target_implant):
    cmd = Sleep(implant_uuid=target_implant, sleep_time="3")
    dispatch_and_wait(api_client, target_implant, cmd)
    # Wait out the new sleep cycle briefly before next commands
    time.sleep(4)

def test_99_exit(api_client, target_implant):
    cmd = Exit(implant_uuid=target_implant)
    cmd_payload = cmd.to_task()
    
    api_client.post_implant_task(target_implant, cmd_payload)
    # Exit kills the process, so polling for a success response isn't reliable
    # Ensure it successfully posted instead.
    time.sleep(2)

def implant_tasks_test(api_client):
    """Orchestrates the full suite of implant tasks in a logical sequence."""
    
    # 1. Setup & Discovery
    implants = api_client.get_implants().get("data", [])
    assert implants, "No active implants for testing"
    uuid = implants[0].get("implant_uuid")
    print(f"\n[!] Starting lifecycle test for: {uuid}")

    # 2. Strategy Tests
    print("[*] Testing Strategy configurations...")
    dispatch_and_wait(api_client, uuid, StratList(implant_uuid=uuid))
    dispatch_and_wait(api_client, uuid, StratActive(implant_uuid=uuid))
    dispatch_and_wait(api_client, uuid, StratPost(implant_uuid=uuid, strategy_name="default_post"))

    # 3. Memory Store Operations
    print("[*] Testing Memstore cycle...")
    dispatch_and_wait(api_client, uuid, MemStoreClear(implant_uuid=uuid))
    
    test_data = base64.b64encode(b"pytest_binary_blob").decode("utf-8")
    dispatch_and_wait(api_client, uuid, MemStoreUpload(implant_uuid=uuid, file_name="stage.bin", file_contents=test_data))
    dispatch_and_wait(api_client, uuid, MemStoreList(implant_uuid=uuid))
    dispatch_and_wait(api_client, uuid, MemStoreDownload(implant_uuid=uuid, file_name="stage.bin"))

    # 4. File System Operations
    print("[*] Testing File System commands...")
    dispatch_and_wait(api_client, uuid, Ls(implant_uuid=uuid, directory="C:\\"))
    dispatch_and_wait(api_client, uuid, Cd(implant_uuid=uuid, directory="C:\\Windows\\Temp"))
    
    # Test Upload (B64 and Dereference)
    dispatch_and_wait(api_client, uuid, FileUpload(uuid, "pytest_b64.txt", test_data))
    dispatch_and_wait(api_client, uuid, FileUpload(uuid, "pytest_mem.txt", "*stage.bin"))
    dispatch_and_wait(api_client, uuid, FileDownload(uuid, "pytest_b64.txt"))

    # 5. Execution (BOF)
    print("[*] Testing BOF execution...")
    # Minimal dummy BOF header for testing
    dummy_bof = base64.b64encode(b"MZ\x90\x00\x03\x00\x00\x00").decode("utf-8")
    dispatch_and_wait(api_client, uuid, BofRunner(uuid, bof_contents=dummy_bof, bof_args="--scan"))

    # 6. Network Discovery
    print("[*] Testing Neighbor discovery...")
    dispatch_and_wait(api_client, uuid, DiscoverNeighbors(implant_uuid=uuid), timeout=120)

    # 7. Cleanup & Termination
    print("[*] Testing Sleep and Exit...")
    dispatch_and_wait(api_client, uuid, Sleep(implant_uuid=uuid, sleep_time="5"))
    
    # Exit is post-only, we don't wait for a response as the process dies
    api_client.post_implant_task(uuid, Exit(implant_uuid=uuid).to_task())
    print("[+] Lifecycle test complete. Implant terminated.")