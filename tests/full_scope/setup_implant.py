import time

def start_listener(api_client):
    with open("client/src/client/user/profiles/amazon.profile")as profile:
        profile_contents = profile.read()

    listener_data = {
        "listener_host": "10.0.1.171",
        "listener_port": 9090,
        "listener_type": "http",
        "listener_name": "pytest_listener",
        "listener_notes": "None",
        "listener_profile_name": "amazon.profile",
        "listener_profile_contents": profile_contents
    }

    start_listener_response = api_client.post_listeners(
        payload = listener_data
    )

    # make sure listener actually started
    assert start_listener_response["data"]["listener_active"] == True
    # and make sure it has a UUID
    assert "data" in start_listener_response and "listener_uuid" in start_listener_response["data"]

    return start_listener_response

def build_payload(api_client, listener_uuid):
	

    build_data = {
        "implant_name": "pytest_implant",
        "output_format": "exe",
        "listener_uuids": [
            listener_uuid
        ],
        "initial_get_profile_listener_uuid": listener_uuid,
        "initial_post_profile_listener_uuid": listener_uuid
    }

    build_data_response = api_client.post_listeners(
        payload = build_data
    )

    # make sure build has UUID
    assert "data" in build_data_response and "build_uuid" in build_data_response["data"]
    return build_data_response

def test_setup_implant(api_client):
    print("Running tests")
    listener_data = start_listener(api_client=api_client)

    listener_uuid = listener_data.get("data").get("listener_uuid")

    build_data = build_payload(api_client=api_client, listener_uuid=listener_uuid)
    build_uuid = build_data.get("data").get("build_uuid")
    # wait for payload to build
    # could poll with build status endpoint in future iters
    print("Waiting for build to complete")

    time.sleep(30)

    # get client hash
    post_build_data = api_client.get_build_jobs(build_uuid=build_uuid)
    assert post_build_data["data"]["build_status"] == "complete"
    assert "data" in post_build_data and "payload_hash" in post_build_data["data"]

    payload_hash = post_build_data.get("data").get("payload_hash")

    # pull bin
    payload_bytes = api_client.get_binary_actions(hash=payload_hash)
    # temp dir

    # write to temp cuz it'll be there on all systems
    with open("/tmp/pytest_implant.exe", "wb") as payload:
        payload.write(payload_bytes)

    # # serve for one GET
    # server = HTTPServer(("0.0.0.0", 8000), OneShotHandler)
    # server.serve_forever()

    # if everyhting else works
    assert True



from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

class OneShotHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        super().do_GET()
        # shutdown in a separate thread to avoid deadlock
        threading.Thread(target=self.server.shutdown, daemon=True).start()
