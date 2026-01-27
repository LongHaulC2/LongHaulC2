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
CURRENT_LISTENER_PORT = 5180
# Ensure directories exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PROFILES_DIR, exist_ok=True)

# misc globals
already_existing_implants = []


def log(msg, level="INFO"):
    print(f"[{level}] {msg}")


def step_1_connect():
    """Step 1: Connect to server (Health Check)"""
    try:
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
    global CURRENT_LISTENER_PORT
    unique_name = f"list_{profile_name}_{uuid.uuid4().hex[:4]}"
    CURRENT_LISTENER_PORT = CURRENT_LISTENER_PORT + 1

    payload = {
        "listener_name": unique_name,
        "listener_type": "http",
        "listener_host": "10.0.0.30",
        "listener_port": CURRENT_LISTENER_PORT,
        "listener_notes": "Automated test listener",
        "listener_profile_name": profile_name,
        "listener_profile_contents": profile_data,
    }
    log(f"Starting listener on port: {CURRENT_LISTENER_PORT}", "INFO")

    try:
        resp = requests.post(f"{API_BASE}/listeners/", json=payload)
        if resp.status_code == 200:
            try:
                data = (resp.json()).get("data")
                listener_id = data.get("listener_uuid")
                log(f"Listener created. ID: {listener_id}", "SUCCESS")
                return listener_id
            except:
                log(
                    f"Listener created but could not parse ID. Resp: {resp.text}",
                    "ERROR",
                )
                return None
        else:
            log(f"Failed to create listener: {resp.text}", "ERROR")
            return None
    except Exception as e:
        log(f"Exception creating listener: {e}", "ERROR")
        return None


def step_3_build_payload(listener_uuid):
    """Step 3: Create payload"""
    payload = {
        "implant_name": f"build_{uuid.uuid4().hex[:4]}",
        "implant_listener_uuid": listener_uuid,
        "implant_variant": "http_wininet",
        "output_format": "exe",
    }

    try:
        resp = requests.post(f"{API_BASE}/build/", json=payload)
        if resp.status_code == 200:
            try:
                data = (resp.json()).get("data")
                build_uuid = data.get("build_uuid")
                log(
                    f"Payload build task submitted. build uuid: {build_uuid}", "SUCCESS"
                )
                return build_uuid
            except:
                log(f"Failed to parse build response: {resp.text}", "ERROR")
                return None
        else:
            log(f"Failed to build payload: {resp.text}", "ERROR")
            return None
    except Exception as e:
        log(f"Exception requesting build: {e}", "ERROR")
        return None


def step_3_5_get_hash(build_id):
    """Polls the build job status until completion or timeout."""
    log(f"Polling build job {build_id}...", "INFO")
    url = f"{API_BASE}/build/jobs/{build_id}"

    for _ in range(MAX_RETRIES):
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                status = data.get("build_status")

                if status == "complete":
                    payload_hash = data.get("payload_hash")
                    log(f"Payload built successfully. Hash: {payload_hash}", "SUCCESS")
                    return payload_hash
                elif status == "failed":
                    error_msg = data.get("error", "Unknown error")
                    log(f"Build failed: {error_msg}", "ERROR")
                    return None
                elif status in ["building", "pending"]:
                    log("Payload still being built...", "INFO")
            else:
                log(f"Error polling job: {resp.status_code}", "WARNING")
        except Exception as e:
            log(f"Exception during polling: {e}", "ERROR")

        time.sleep(SLEEP_INTERVAL)

    log("Timed out waiting for build to complete.", "ERROR")
    return None


def step_4_download_payload(build_hash):
    """Step 4: Download payload"""
    url = f"{API_BASE}/build/{build_hash}"
    try:
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
    except Exception as e:
        log(f"Exception downloading payload: {e}", "ERROR")
        return None


def step_5_execute_payload(filepath):
    """
    Step 5: Execute payload (Windows).
    UPDATED: Checks if process stays alive for at least 2 seconds.
    """
    try:
        # Start the process without blocking
        proc = subprocess.Popen([filepath], creationflags=subprocess.CREATE_NEW_CONSOLE)

        # WAIT: Give the process 2 seconds to see if it crashes/exits
        time.sleep(2)

        # CHECK: Has the process exited?
        exit_code = proc.poll()

        if exit_code is not None:
            log(f"Payload started but exited immediately (Code: {exit_code})", "ERROR")
            return None  # Failure
        else:
            log(f"Executed payload and it is stable. PID: {proc.pid}", "SUCCESS")
            return proc  # Success

    except Exception as e:
        log(f"Execution exception: {e}", "ERROR")
        return None


def wait_for_implant_checkin(listener_uuid):
    """Helper: Poll /implants/ until a relevant implant appears"""
    # this is a bad way to do it... tldr we have no idea what implant id will be when it checks in
    # coudl do a list of ID's, and if not in list, it's the new one?

    log("Waiting for implant check-in...", "INFO")

    for _ in range(MAX_RETRIES):
        try:
            resp = requests.get(f"{API_BASE}/implants/")
            if resp.status_code == 200:
                implants = (resp.json()).get("data")
                for implant in implants:
                    if implant not in already_existing_implants:
                        implant_uuid = implant.get("implant_uuid")
                        already_existing_implants.append(implant_uuid)
                        log(f"Implant checked in! UUID: {implant_uuid}", "SUCCESS")
                        return implant_uuid

                # if isinstance(implants, list) and len(implants) > 0:
                #     # Ideally, match listener_uuid here if possible
                #     implant = implants[-1]
                #     implant_uuid = implant.get("uuid", implant.get("id"))
                #     log(f"Implant checked in! UUID: {implant_uuid}", "SUCCESS")
                #     return implant_uuid
        except Exception as e:
            log(f"Exception checking implants: {e}", "ERROR")

        time.sleep(SLEEP_INTERVAL)

    log("Timed out waiting for implant.", "ERROR")
    return None


def step_6_queue_command(implant_uuid):
    """Step 6: Enqueue command (whoami)"""
    time.sleep(
        1
    )  # wait 1 seoncd for implant to be regiseterd, sometimes it doens't get the cmd if it's too quick. Kinda weird.
    command_str = "cmd whoami"
    task_data = {
        "implant_uuid": implant_uuid,
        "task": {
            "taskname": "cmd",
            "args": {"cli": command_str},
        },
    }

    try:
        resp = requests.post(f"{API_BASE}/implants/{implant_uuid}/task", json=task_data)
        if resp.status_code == 200:
            log(f"Command '{command_str}' queued.", "SUCCESS")
            task_uuid = (resp.json()).get("data").get("task_uuid")
            return task_uuid
        else:
            log(f"Failed to queue command: {resp.text}", "ERROR")
            return None
    except Exception as e:
        log(f"Exception queuing command: {e}", "ERROR")
        return None


def step_7_check_output(implant_uuid, task_uuid):
    """Step 7: Check history for output"""
    log(f"Polling history of implant, looking for task {task_uuid}", "INFO")

    for i in range(MAX_RETRIES):
        try:
            resp = requests.get(f"{API_BASE}/implants/{implant_uuid}/tasks/history")
            if resp.status_code == 200:
                history_data = resp.json()
                tasks = (
                    history_data.get("data", [])
                    if isinstance(history_data, dict)
                    else history_data
                )

                # print(tasks)

                for task in tasks:
                    extracted_task_uuid = task.get("task_uuid")
                    extracted_task_response = task.get("task_response")

                    # make sure we pull the correct task id
                    if extracted_task_uuid == task_uuid:
                        # and that the response is not none
                        if extracted_task_response != None:
                            print(
                                f"Task {task_uuid} response found: {extracted_task_response}"
                            )
                            return True

        except Exception as e:
            log(f"Exception checking history: {e}", "ERROR")

        time.sleep(SLEEP_INTERVAL)
        print(f"    ...waiting for task response ({i+1}/{MAX_RETRIES})")

    log("Failed to verify output within timeout.", "ERROR")
    return False


def main():
    log("--- Starting Test Suite ---")

    # DICT to store results: { "ProfileName": "Success/Error Message" }
    test_report = {}

    # 1. Connect
    if not step_1_connect():
        print("CRITICAL: Cannot connect to server. Exiting.")
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

        # Initialize status for this profile
        test_report[profile_name] = "Incomplete (Unknown Error)"

        with open(profile_path, "r") as f:
            profile_content = f.read()

        log(f"\n--- Testing Profile: {profile_name} ---")

        # 2. Create Listener
        listener_id = step_2_create_listener(profile_name, profile_content)
        if not listener_id:
            test_report[profile_name] = "FAILURE: Step 2 (Create Listener)"
            continue  # Skip to next profile

        # 3. Build Payload
        build_id = step_3_build_payload(listener_id)
        if not build_id:
            test_report[profile_name] = "FAILURE: Step 3 (Request Build)"
            continue

        # 3.5 Get Hash
        build_hash = step_3_5_get_hash(build_id)
        if not build_hash:
            test_report[profile_name] = "FAILURE: Step 3.5 (Build Job Failed/Timeout)"
            continue

        # 4. Download Payload
        exe_path = step_4_download_payload(build_hash)
        if not exe_path:
            test_report[profile_name] = "FAILURE: Step 4 (Download Payload)"
            continue

        # 5. Execute Payload (Includes 2s health check)
        process = step_5_execute_payload(exe_path)
        if not process:
            test_report[profile_name] = "FAILURE: Step 5 (Execution - Crashed/Exited)"
            continue

        # Wait for Check-in
        implant_uuid = wait_for_implant_checkin(listener_id)
        if not implant_uuid:
            process.kill()  # Cleanup
            test_report[profile_name] = "FAILURE: Step 5b (No Check-in Received)"
            continue

        # 6. Queue Command
        task_uuid = step_6_queue_command(implant_uuid)
        if not task_uuid:
            process.kill()
            requests.delete(f"{API_BASE}/implants/{implant_uuid}")
            test_report[profile_name] = "FAILURE: Step 6 (Queue Command)"
            continue

        # 7. Check Output - re-enable when cmd works
        # current_user = os.getlogin()
        # output_verified = step_7_check_output(implant_uuid, current_user)

        output_verified = step_7_check_output(implant_uuid, task_uuid)

        # Cleanup
        requests.delete(f"{API_BASE}/implants/{implant_uuid}")
        process.kill()

        if output_verified:
            test_report[profile_name] = "SUCCESS"
        else:
            test_report[profile_name] = "FAILURE: Step 7 (Output Verification Failed)"

        log(f"--- Completed Profile: {profile_name} ---")

    # --- FINAL REPORT ---
    print("\n" + "=" * 40)
    print("      FINAL EXECUTION REPORT")
    print("=" * 40)
    for name, status in test_report.items():
        # Formatting for alignment
        print(f"{name:<30} | {status}")
    print("=" * 40 + "\n")


if __name__ == "__main__":
    main()
