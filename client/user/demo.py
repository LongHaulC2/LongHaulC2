import requests
from yarl import URL

"""
A demo script meant to populate the server with various data

The functions here also demo how to use the API, etc.
"""

profile = """
[profile]
name = "Demo HTTP Mimicry"
author = "demo"

[raw.get]
proto = "tcp"
body = "<METADATA>"

[raw.get.client.metadata]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = "GET /update?sid=" },
    { op = "append",  val = " HTTP/1.1\\r\\nHost: example.com\\r\\nAccept: */*\\r\\n\\r\\n" },
]

[raw.get.server]
body = "<OUTPUT>"

[raw.get.server.output]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = "HTTP/1.1 200 OK\\r\\nContent-Type: application/octet-stream\\r\\n\\r\\n" },
]

[raw.post]
proto = "tcp"
body = "<OUTPUT>"

[raw.post.client.output]
transforms = [
    { op = "base64url" },
    { op = "prepend", val = "POST /upload HTTP/1.1\\r\\nHost: example.com\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\n\\r\\ndata=" },
]

[raw.post.server]
body = "HTTP/1.1 200 OK\\r\\n\\r\\n"
"""


# setup server variables
api_url = URL("http://10.0.0.30:45045/api/v1")


def start_listener(host, port, type="raw", name="raw_listener"):
    """
    Start a listener
    """
    listener_spawn_url = api_url / "listeners"

    listener_data = {
        "listener_host": host,
        "listener_port": port,
        "listener_type": type,
        "listener_name": name,
        "listener_notes": "Generic Listener",
        "listener_profile_name": "profile",
        "listener_profile_contents": profile,
    }

    r = requests.post(str(listener_spawn_url), json=listener_data)
    print(r.status_code)
    print(r.text)


def generate_implants():
    """
    Generate implants for each listener listed
    """
    # get a list of listeners
    listener_list_url = api_url / "listeners"
    r = requests.get(str(listener_list_url))
    list_of_listeners = (r.json()).get("data")

    # loop over listeners, and then generate
    build_payload_url = api_url / "build"

    for listener in list_of_listeners:
        listener_uuid = listener.get("listener_uuid")

        req_data = {
            "implant_variant": "raw",
            "output_format": "exe",
            "implant_name": "my_implant",
            "implant_listener_uuid": listener_uuid,
        }

        r = requests.post(str(build_payload_url), json=req_data)
        print(r.status_code)
        print(r.text)


def main():
    print("========================================")
    print("Generating some data...")
    print("========================================")
    for i in range(0, 50):
        # Start some listeners
        start_listener("0.0.0.0", 9090 + int(i))

    # generate some implants for those listeners...
    # These will generate in the background, and might take a second to generate.
    for i in range(0, 1):
        generate_implants()


main()
