import time
import sys

'''
Step 2 of integration test

A test meant for linux github runners, that after the server is spun up,
connects to server, starts a listeenr, builds and implant, and puts it in /tmp/...
for the runner to host to the file, and the windows runner to execute

'''

def start_listener(api_client):
    print(f"[*] Initializing listener...")
    with open("client/src/client/user/profiles/amazon.profile") as profile:
        profile_contents = profile.read()

    listener_data = {
        "listener_host": "10.0.1.170",
        "listener_port": 9090,
        "listener_type": "http",
        "listener_name": "pytest_listener",
        "listener_notes": "None",
        "listener_profile_name": "amazon.profile",
        "listener_profile_contents": profile_contents
    }

    start_listener_response = api_client.post_listeners(payload=listener_data)

    active = start_listener_response.get("data", {}).get("listener_active")
    uuid = start_listener_response.get("data", {}).get("listener_uuid")

    # make sure listener actually started
    assert active == True
    # and make sure it has a UUID
    assert "data" in start_listener_response and "listener_uuid" in start_listener_response["data"]

    print(f"[+] Listener '{listener_data['listener_name']}' active. UUID: {uuid}")
    return start_listener_response

def build_payload(api_client, listener_uuid):    
    build_data = {
        "implant_name": "pytest_implant",
        "listener_uuids": [listener_uuid],
        "initial_get_profile_listener_uuid": listener_uuid,
        "initial_post_profile_listener_uuid": listener_uuid
    }

    print(f"[*] Requesting '{build_data['implant_name']}' build")

    build_data_response = api_client.post_build(payload=build_data)

    # make sure build has UUID
    assert "data" in build_data_response and "build_uuid" in build_data_response["data"]
    
    build_uuid = build_data_response["data"]["build_uuid"]
    print(f"[+] Build job submitted successfully. UUID: {build_uuid}")
    return build_data_response

def test_setup_implant(api_client):
    print("\n[!] Starting Automated Implant Setup")
    print("-" * 40)
    
    listener_data = start_listener(api_client=api_client)
    listener_uuid = listener_data.get("data").get("listener_uuid")

    build_data = build_payload(api_client=api_client, listener_uuid=listener_uuid)
    build_uuid = build_data.get("data").get("build_uuid")

    # wait for payload to build
    timeout = 60
    start_poll = time.time()
    print(f"[*] Polling build status for {build_uuid}...")

    while True:
        post_build_data = api_client.get_build_jobs(build_uuid=build_uuid)
        status = post_build_data.get("data", {}).get("build_status")
        
        if status == "complete":
            print(f"\n[+] Build complete in {round(time.time() - start_poll, 2)}s")
            break
        elif status == "failed":
            print(f"\n[!] Build failed for UUID: {build_uuid}")
            sys.exit(1)
            
        if time.time() - start_poll > timeout:
            print(f"\n[!] Timeout reached waiting for build {build_uuid}")
            sys.exit(1)
            
        print(".", end="", flush=True)
        time.sleep(2)

    # get client hash
    assert post_build_data["data"]["build_status"] == "complete"
    assert "data" in post_build_data and "payload_hash" in post_build_data["data"]

    payload_hash = post_build_data.get("data").get("payload_hash")
    print(f"[*] Fetching binary with hash: {payload_hash}")

    # pull bin
    payload_bytes = api_client.get_binary_actions(hash=payload_hash)
    
    output_path = "/tmp/pytest_implant.exe"
    # write to temp cuz it'll be there on all systems
    # GH job will grab it from here, and handle the hosting
    with open(output_path, "wb") as payload:
        payload.write(payload_bytes)
    
    print(f"[+] Success: Binary written to {output_path} ({len(payload_bytes)} bytes)")
    # if everyhting else works
    assert True
